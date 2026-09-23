# fetch_youtube_data.py
# ---------------------------------------------
# YouTube Data API v3 を使用して動画やチャンネル情報を取得し、
# ローカルのSQLiteデータベースに保存・キャッシュするクラスを定義。
#
# 主な機能：
# - 動画やチャンネルの情報をAPIから取得
# - 一度取得した情報はSQLiteに保存し、再利用（キャッシュ機構）
# - チャンネルの動画一覧を日付指定で取得・保存
# - 動画の再生時間（duration）をISO 8601から秒に変換して保存
#
# 使用ライブラリ：
# - googleapiclient.discovery: YouTube APIクライアント
# - isodate: ISO 8601 形式の duration を秒数へ変換
# - dotenv: .envファイルからAPIキーとDBパスを取得
#
# 依存ファイル：
# - youtube_db.py: SQLiteデータベースの操作クラス
# - .env: 環境変数（YOUTUBE_API_KEY, YOUTUBE_DB_PATH）を定義
#
# 注意事項：
# - APIキーは.envにてYOUTUBE_API_KEYとして設定しておく必要あり
# - DBのパスを明示的に指定したい場合は、YouTubeDBインスタンスに引数で渡す
# ---------------------------------------------


import os
from datetime import datetime

import isodate
from dotenv import load_dotenv
from googleapiclient.discovery import build

from .youtube_db import YouTubeDB

load_dotenv()
API_KEY = os.getenv('YOUTUBE_API_KEY')


class YouTubeAPI:
    def __init__(self, youtube=None, db=None):
        self.youtube = (
            youtube
            if youtube is not None
            else build(
                "youtube",
                "v3",
                developerKey=API_KEY,
            )
        )
        self.db = db if db is not None else YouTubeDB()

    def call_api(self, resource, method, **params):
        """汎用 API 呼び出し関数"""
        func = getattr(getattr(self.youtube, resource)(), method)
        return func(**params).execute()

    def get_video_with_cache(self, video_id):
        """動画をDBから取得、なければAPIから取得・保存して返す"""
        result = self.db.get_video_by_id(video_id)

        if result:
            return result

        response = self.call_api(
            "videos",
            "list",
            part="snippet,contentDetails",
            id=video_id,
        )
        items = response.get("items", [])
        if not items:
            return None

        item = items[0]
        snippet = item["snippet"]
        content = item["contentDetails"]

        try:
            duration = int(isodate.parse_duration(
                content["duration"]).total_seconds())
        except Exception:
            duration = None

        video = {
            "video_id": video_id,
            "title": snippet["title"],
            "channel_id": snippet["channelId"],
            "published_at": snippet.get("publishedAt"),
            "duration": duration,
            "thumbnail_default": snippet["thumbnails"].get("default", {}).get("url"),
            "thumbnail_medium": snippet["thumbnails"].get("medium", {}).get("url"),
            "thumbnail_high": snippet["thumbnails"].get("high", {}).get("url"),
        }

        self.get_channel_with_cache(video["channel_id"])  # チャンネルも挿入
        self.db.insert_video(video)
        return video

    def get_channel_with_cache(self, channel_id):
        """チャンネルをDBから取得、なければAPIから取得して保存して返す"""
        result = self.db.get_channel_by_id(channel_id)

        if result:
            return result

        response = self.call_api(
            "channels",
            "list",
            part="snippet",
            id=channel_id,
        )
        items = response.get("items", [])
        if not items:
            return None

        snippet = items[0]["snippet"]
        title = snippet["title"]

        self.db.insert_channel(channel_id, title)

        return (channel_id, title)

    def fetch_and_save_videos_from_channel(self, channel_id, published_after=None, published_before=None, max_results=50, get_duration=False):
        channel_info = self.get_channel_with_cache(channel_id)
        if not channel_info:
            print(f"Channel {channel_id} not found")
            return

        def to_utc_z(dt):
            if isinstance(dt, datetime):
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            return dt  # 文字列ならそのまま（責任は呼び出し元）

        next_page_token = None

        while True:
            request = self.youtube.search().list(
                part="id,snippet",
                channelId=channel_id,
                maxResults=max_results,
                order="date",
                publishedAfter=to_utc_z(published_after),
                publishedBefore=to_utc_z(published_before),
                pageToken=next_page_token,
                type="video"
            )
            response = request.execute()

            video_ids = []
            videos_to_insert = []

            for item in response.get("items", []):
                vid = item["id"]["videoId"]
                video_ids.append(vid)

                snippet = item["snippet"]
                videos_to_insert.append({
                    "video_id": vid,
                    "title": snippet["title"],
                    "channel_id": channel_id,
                    "published_at": snippet.get("publishedAt"),
                    "duration": None,
                    "thumbnail_default": snippet["thumbnails"].get("default", {}).get("url"),
                    "thumbnail_medium": snippet["thumbnails"].get("medium", {}).get("url"),
                    "thumbnail_high": snippet["thumbnails"].get("high", {}).get("url"),
                })

            for video in videos_to_insert:
                self.db.insert_video(video)

            if get_duration:
                self.fetch_and_update_video_details(video_ids)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

    def get_channel_videos_with_cache(self, channel_id, start_date, end_date):
        def to_utc_z(dt):
            if isinstance(dt, datetime):
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            elif isinstance(dt, str) and not dt.endswith("Z"):
                return dt + "Z"
            return dt

        start = to_utc_z(start_date)
        end = to_utc_z(end_date)

        results = self.db.get_videos_by_channel_and_date(
            channel_id,
            start,
            end,
        )

        if results:
            print('from DB')
            return results

        # なければAPIから取得
        self.fetch_and_save_videos_from_channel(
            channel_id,
            published_after=start,
            published_before=end
        )

        print('from api')

        # 再検索して返す
        with self.db._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM videos
                WHERE channel_id = ? AND published_at BETWEEN ? AND ?
                ORDER BY published_at DESC
            """, (channel_id, start, end))
            return cursor.fetchall()

    def fetch_and_update_video_details(self, video_ids):
        """動画のduration情報を取得してDBを更新"""
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]

            response = self.youtube.videos().list(
                part="contentDetails",
                id=",".join(batch_ids)
            ).execute()

            for item in response.get("items", []):
                vid = item["id"]
                duration_iso = item["contentDetails"]["duration"]

                try:
                    duration_sec = int(isodate.parse_duration(
                        duration_iso).total_seconds())
                except Exception:
                    duration_sec = None

                self.db.update_video_duration(vid, duration_sec)

    def search_videos(
        self,
        query=None,
        channel_id=None,
        published_after=None,
        published_before=None,
        event_type=None,
        max_results=50,
        order="date",
        page_token=None,
    ):
        """YouTube動画を検索する"""
        def to_utc_z(dt):
            if isinstance(dt, datetime):
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            return dt

        params = {
            "part": "snippet",
            "type": "video",
            "maxResults": max_results,
            "order": order,
        }

        if query is not None:
            params["q"] = query

        if channel_id is not None:
            params["channelId"] = channel_id

        if published_after is not None:
            params["publishedAfter"] = to_utc_z(published_after)

        if published_before is not None:
            params["publishedBefore"] = to_utc_z(published_before)

        if event_type is not None:
            params["eventType"] = event_type

        if page_token is not None:
            params["pageToken"] = page_token

        return self.call_api("search", "list", **params)

    def get_video_details(self, video_id, part="snippet,contentDetails"):
        """指定した動画の詳細情報を取得する"""
        response = self.call_api(
            "videos",
            "list",
            part=part,
            id=video_id,
        )

        items = response.get("items", [])

        if not items:
            return None

        return items[0]

    def get_playlist_items(
        self,
        playlist_id,
        max_results=50,
        page_token=None,
    ):
        """プレイリスト内の動画を取得する"""
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": max_results,
        }

        if page_token is not None:
            params["pageToken"] = page_token

        return self.call_api(
            "playlistItems",
            "list",
            **params,
        )

    def get_live_streaming_video_ids(self, video_ids):
        """
        liveStreamingDetailsを持つvideo_idを取得する。

        liveStreamingDetailsはyoutube.dbには保存せず、
        YouTube APIから処理時に確認する。
        """
        live_video_ids = set()

        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i + 50]
            if not batch_ids:
                continue

            response = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=",".join(batch_ids),
            ).execute()

            for item in response.get("items", []):
                if "liveStreamingDetails" in item:
                    live_video_ids.add(item["id"])

        return live_video_ids

    def get_video_details_with_cache(
        self,
        video_id,
        part="snippet,contentDetails",
    ):
        """
        YouTube APIから動画詳細を取得し、youtube_cache.dbに保存する。

        既にDBに存在する動画についても、APIから取得した最新情報で
        動画情報を更新する。

        Returns:
            dict | None:
                YouTube APIから取得した動画情報。
                指定されたvideo_idが存在しない場合はNone。
        """
        item = self.get_video_details(
            video_id,
            part=part,
        )

        if item is None:
            return None

        snippet = item.get("snippet", {})

        channel_id = snippet.get("channelId")
        channel_title = snippet.get("channelTitle")

        if not channel_id or not channel_title:
            return item

        # チャンネルを保存
        self.db.insert_channel(
            channel_id,
            channel_title,
        )

        video = {
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel_id": channel_id,
            "published_at": snippet.get("publishedAt"),
            "duration": None,
            "thumbnail_default": (
                snippet.get("thumbnails", {})
                .get("default", {})
                .get("url")
            ),
            "thumbnail_medium": (
                snippet.get("thumbnails", {})
                .get("medium", {})
                .get("url")
            ),
            "thumbnail_high": (
                snippet.get("thumbnails", {})
                .get("high", {})
                .get("url")
            ),
        }

        # contentDetailsが取得されている場合はdurationを保存
        if "contentDetails" in item:
            duration = item["contentDetails"].get("duration")

            if duration:
                import isodate

                video["duration"] = int(
                    isodate.parse_duration(duration).total_seconds()
                )

        self.db.upsert_video(video)

        return item

def _to_utc_z(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    if isinstance(value, str) and not value.endswith("Z"):
        return value + "Z"

    return value
