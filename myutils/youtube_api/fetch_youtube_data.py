# fetch_youtube_data.py
# ---------------------------------------------
# YouTube Data API

import re
from datetime import date, datetime, time, timedelta, timezone

from .converters import (
    channel_from_api_item,
    parse_duration,
    video_from_api_item,
    video_from_playlist_item,
    video_from_search_item,
)


# ============================================================
# Constants / Utility
# ============================================================

LIVE_STATE_TTL = timedelta(hours=3)
UTC = timezone.utc


def to_utc_z(
    value: str | date | datetime | None,
    *,
    end_date: bool = False,
) -> str | None:
    """日付/日時をYouTube API・youtube.db用のUTC ISO文字列へ変換する。"""
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        dt = dt.astimezone(UTC)

        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    if isinstance(value, date):
        dt = datetime.combine(
            value,
            time.min,
            tzinfo=UTC,
        )

        if end_date:
            dt += timedelta(days=1)

        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    text = str(value).strip()

    if not text:
        raise ValueError("date is required")

    # YYYY-M-D / YYYY-MM-DD の両方を許可する
    match = re.fullmatch(
        r"(\d{4})-(\d{1,2})-(\d{1,2})",
        text,
    )

    if match:
        year, month, day = map(int, match.groups())

        parsed_date = date(
            year,
            month,
            day,
        )

        return to_utc_z(
            parsed_date,
            end_date=end_date,
        )

    # 日付以外の日時文字列
    normalized = text.replace("Z", "+00:00")

    dt = datetime.fromisoformat(normalized)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    dt = dt.astimezone(UTC)

    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _chunks(values, size):
    for i in range(0, len(values), size):
        yield values[i:i + size]


def _video_row_to_dict(row):
    if row is None:
        return None

    return {
        "video_id": row[0],
        "title": row[1],
        "channel_id": row[2],
        "published_at": row[3],
        "duration": row[4],
        "thumbnail_default": row[5],
        "thumbnail_medium": row[6],
        "thumbnail_high": row[7],
    }


# ============================================================
# YouTube API
# ============================================================

class YouTubeAPI:

    # ========================================================
    # Initialization
    # ========================================================

    def __init__(self, client, db):
        self.client = client
        self.db = db

    # ========================================================
    # Channel
    # ========================================================

    def get_channel_with_cache(self, channel_id):
        print(f"[YouTubeAPI] get_channel_with_cache: channel_id={channel_id}")

        result = self.db.get_channel_by_id(channel_id)

        if result:
            print("[Cache] channel -> HIT")
            print("[Result] source=DB")
            return result

        print("[Cache] channel -> MISS")
        print(f"[API] channels.list: channel_id={channel_id}")
        response = self.client.call(
            "channels",
            "list",
            part="snippet",
            id=channel_id,
        )

        items = response.get("items", [])

        if not items:
            print("[Result] channel -> NOT_FOUND")
            return None

        channel = channel_from_api_item(items[0])

        self.db.insert_channel(
            channel["channel_id"],
            channel["channel_title"],
        )
        print(f"[DB] channel -> INSERT: channel_id={channel['channel_id']}")
        print("[Result] source=API")

        return (
            channel["channel_id"],
            channel["channel_title"],
        )


    def get_channel_uploads_playlist_id(self, channel_id):
        print(
            f"[YouTubeAPI] get_channel_uploads_playlist_id: "
            f"channel_id={channel_id}"
        )

        state = self.db.get_channel_sync_state(channel_id)

        if state and state[1]:
            print("[Cache] uploads_playlist_id -> HIT")
            print(f"[Result] playlist_id={state[1]}")
            return state[1]

        print("[Cache] uploads_playlist_id -> MISS")
        print(f"[API] channels.list: channel_id={channel_id}")
        response = self.client.call(
            "channels",
            "list",
            part="contentDetails,snippet",
            id=channel_id,
        )

        items = response.get("items", [])

        if not items:
            print("[Result] channel -> NOT_FOUND")
            return None

        item = items[0]

        content_details = item.get(
            "contentDetails",
            {},
        )

        related_playlists = content_details.get(
            "relatedPlaylists",
            {},
        )

        uploads_playlist_id = related_playlists.get(
            "uploads"
        )

        if not uploads_playlist_id:
            print("[Result] uploads_playlist_id -> NOT_FOUND")
            return None

        snippet = item.get("snippet", {})
        channel_title = snippet.get("title")

        if channel_title:
            self.db.insert_channel(
                channel_id,
                channel_title,
            )
            print(f"[DB] channel -> INSERT/IGNORE: channel_id={channel_id}")

        self.db.set_channel_sync_state(
            channel_id,
            uploads_playlist_id=uploads_playlist_id,
        )
        print(
            "[DB] sync_state -> UPDATE: "
            f"channel_id={channel_id} uploads_playlist_id={uploads_playlist_id}"
        )
        print(f"[Result] playlist_id={uploads_playlist_id}")

        return uploads_playlist_id


    def _fetch_channel_uploads_playlist_id(self, channel_id):
        response = self.client.call(
            "channels",
            "list",
            part="contentDetails,snippet",
            id=channel_id,
        )

        items = response.get("items", [])

        if not items:
            return None

        item = items[0]

        content_details = item.get(
            "contentDetails",
            {},
        )

        related_playlists = content_details.get(
            "relatedPlaylists",
            {},
        )

        uploads_playlist_id = related_playlists.get(
            "uploads"
        )

        if not uploads_playlist_id:
            return None

        snippet = item.get("snippet", {})
        channel_title = snippet.get("title")

        if channel_title:
            self.db.insert_channel(
                channel_id,
                channel_title,
            )

        return uploads_playlist_id

    # ========================================================
    # Video cache
    # ========================================================

    def get_video_with_cache(self, video_id):
        print(f"[YouTubeAPI] get_video_with_cache: video_id={video_id}")

        result = self.db.get_video_by_id(video_id)

        if result:
            print("[Cache] video -> HIT")
            print("[Result] source=DB")
            return _video_row_to_dict(result)

        print("[Cache] video -> MISS")
        print(f"[API] videos.list: video_id={video_id}")
        response = self.client.call(
            "videos",
            "list",
            part="snippet,contentDetails",
            id=video_id,
        )

        items = response.get("items", [])

        if not items:
            print("[Result] video -> NOT_FOUND")
            return None

        item = items[0]
        video = video_from_api_item(item)

        self.get_channel_with_cache(
            video["channel_id"]
        )

        self.db.insert_video(video)
        print(f"[DB] video -> INSERT/UPSERT: video_id={video_id}")
        print("[Result] source=API")

        return video


    # ========================================================
    # Channel video sync
    # ========================================================

    def is_channel_sync_complete(
        self,
        channel_id,
        start_date,
        end_date,
    ):
        state = self.db.get_channel_sync_state(channel_id)

        if not state:
            print(
                f"[Cache] sync -> NOT_FOUND: channel_id={channel_id}"
            )
            return False

        oldest_synced_at = state[2]
        newest_synced_at = state[3]

        if not oldest_synced_at or not newest_synced_at:
            print(
                f"[Cache] sync -> INCOMPLETE: channel_id={channel_id} "
                f"cached={oldest_synced_at}..{newest_synced_at}"
            )
            return False

        start = to_utc_z(start_date)
        end = to_utc_z(end_date)

        complete = (
            oldest_synced_at <= start
            and newest_synced_at >= end
        )

        status = "COMPLETE" if complete else "INCOMPLETE"
        print(
            f"[Cache] sync -> {status}: channel_id={channel_id} "
            f"cached={oldest_synced_at}..{newest_synced_at} "
            f"requested={start}..{end}"
        )
        return complete


    def refresh_channel_videos(
        self,
        channel_id,
        start_date,
        end_date,
        max_results=50,
    ):
        print(
            f"[YouTubeAPI] refresh_channel_videos: channel_id={channel_id} "
            f"start={start_date} end={end_date}"
        )

        start = to_utc_z(start_date)
        end = to_utc_z(end_date)

        playlist_id = self._fetch_channel_uploads_playlist_id(
            channel_id
        )

        if not playlist_id:
            print("[Result] refresh -> FAILED: uploads_playlist_id not found")
            return False

        next_page_token = None
        page = 0
        api_items = 0
        saved_items = 0

        while True:
            page += 1
            response = self.get_playlist_videos(
                playlist_id,
                max_results=max_results,
                page_token=next_page_token,
            )

            items = response.get("items", [])
            api_items += len(items)
            print(
                f"[API] playlistItems.list: page={page} items={len(items)}"
            )

            if not items:
                break

            reached_start = False

            for item in items:
                video = video_from_playlist_item(item)

                video_id = video["video_id"]
                published_at = video["published_at"]

                if not video_id or not published_at:
                    continue

                if video["channel_id"] is None:
                    video["channel_id"] = channel_id

                if published_at >= start:
                    if published_at < end:
                        self.db.insert_video(video)
                        saved_items += 1

                if published_at < start:
                    reached_start = True

            if reached_start:
                break

            next_page_token = response.get(
                "nextPageToken"
            )

            if not next_page_token:
                break

        self.db.set_channel_sync_state(
            channel_id,
            uploads_playlist_id=playlist_id,
            oldest_synced_at=start,
            newest_synced_at=end,
        )
        print(
            f"[DB] sync_state -> UPDATE: channel_id={channel_id} "
            f"range={start}..{end}"
        )
        print(
            f"[Result] refresh -> COMPLETE: pages={page} "
            f"api_items={api_items} saved={saved_items}"
        )

        return True


    def sync_channel_videos(
        self,
        channel_id,
        start_date,
        end_date,
        max_results=50,
    ):
        print(
            f"[YouTubeAPI] sync_channel_videos: channel_id={channel_id} "
            f"start={start_date} end={end_date}"
        )

        start = to_utc_z(start_date)
        end = to_utc_z(end_date)

        if self.is_channel_sync_complete(
            channel_id,
            start,
            end,
        ):
            print("[Sync] not required: cache is complete")
            print("[Result] sync -> CACHE")
            return True

        print("[Sync] required")

        playlist_id = self.get_channel_uploads_playlist_id(
            channel_id
        )

        if not playlist_id:
            print("[Result] sync -> FAILED: uploads_playlist_id not found")
            return False

        next_page_token = None
        oldest_published_at = None
        page = 0
        api_items = 0
        saved_items = 0

        while True:
            page += 1
            response = self.get_playlist_videos(
                playlist_id,
                max_results=max_results,
                page_token=next_page_token,
            )

            items = response.get("items", [])
            api_items += len(items)
            print(
                f"[API] playlistItems.list: page={page} items={len(items)}"
            )

            for item in items:
                video = video_from_playlist_item(item)

                video_id = video["video_id"]
                published_at = video["published_at"]

                if not video_id or not published_at:
                    continue

                if video["channel_id"] is None:
                    video["channel_id"] = channel_id

                if published_at >= start:
                    if published_at < end:
                        self.db.insert_video(video)
                        saved_items += 1

                oldest_published_at = published_at

            if not items:
                break

            if (
                oldest_published_at
                and oldest_published_at < start
            ):
                break

            next_page_token = response.get(
                "nextPageToken"
            )

            if not next_page_token:
                break

        self.db.set_channel_sync_state(
            channel_id,
            uploads_playlist_id=playlist_id,
            newest_synced_at=end,
        )
        print(
            f"[DB] sync_state -> UPDATE: channel_id={channel_id} "
            f"newest_synced_at={end}"
        )
        print(
            f"[Result] sync -> COMPLETE: pages={page} "
            f"api_items={api_items} saved={saved_items}"
        )

        return True


    def get_channel_videos_with_cache(
        self,
        channel_id,
        start_date,
        end_date,
    ):
        print(
            f"[YouTubeAPI] get_channel_videos_with_cache: "
            f"channel_id={channel_id} start={start_date} end={end_date}"
        )

        start = to_utc_z(start_date)
        end = to_utc_z(end_date)

        sync_complete = self.is_channel_sync_complete(
            channel_id,
            start,
            end,
        )

        if not sync_complete:
            print("[Sync] required")
            sync_success = self.sync_channel_videos(
                channel_id,
                start,
                end,
            )
            if not sync_success:
                print("[Sync] failed")
        else:
            print("[Sync] not required: cache is complete")

        videos = self.db.get_videos_by_channel_and_date(
            channel_id,
            start,
            end,
        )

        print(
            f"[Result] source=DB videos={len(videos)}"
        )
        return videos


    # ========================================================
    # Playlist
    # ========================================================

    def get_playlist_videos(
        self,
        playlist_id,
        max_results=50,
        page_token=None,
    ):
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": max_results,
        }

        if page_token is not None:
            params["pageToken"] = page_token

        return self.client.call(
            "playlistItems",
            "list",
            **params,
        )


    def get_playlist_items(
        self,
        playlist_id,
        max_results=50,
        page_token=None,
    ):
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": max_results,
        }

        if page_token is not None:
            params["pageToken"] = page_token

        return self.client.call(
            "playlistItems",
            "list",
            **params,
        )


    def fetch_and_save_videos_from_playlist(
        self,
        playlist_id,
        channel_id,
        max_results=50,
    ):
        print(
            f"[YouTubeAPI] fetch_and_save_videos_from_playlist: "
            f"playlist_id={playlist_id} channel_id={channel_id}"
        )

        next_page_token = None
        page = 0
        api_items = 0
        saved_items = 0

        while True:
            page += 1
            response = self.get_playlist_videos(
                playlist_id,
                max_results=max_results,
                page_token=next_page_token,
            )

            items = response.get("items", [])
            api_items += len(items)
            print(
                f"[API] playlistItems.list: page={page} items={len(items)}"
            )

            for item in items:
                video = video_from_playlist_item(item)

                if not video["video_id"]:
                    continue

                if not video["channel_id"]:
                    video["channel_id"] = channel_id

                self.db.insert_video(video)
                saved_items += 1

            next_page_token = response.get(
                "nextPageToken"
            )

            if not next_page_token:
                break

        print(
            f"[Result] videos saved={saved_items} api_items={api_items} "
            f"pages={page}"
        )


    # ========================================================
    # Search
    # ========================================================

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
            params["publishedAfter"] = to_utc_z(
                published_after
            )

        if published_before is not None:
            params["publishedBefore"] = to_utc_z(
                published_before
            )

        if event_type is not None:
            params["eventType"] = event_type

        if page_token is not None:
            params["pageToken"] = page_token

        print(
            "[YouTubeAPI] search_videos: "
            f"query={query} channel_id={channel_id} "
            f"published_after={params.get('publishedAfter')} "
            f"published_before={params.get('publishedBefore')} "
            f"event_type={event_type}"
        )
        print(
            f"[API] search.list: max_results={max_results} order={order}"
        )
        response = self.client.call(
            "search",
            "list",
            **params,
        )
        print(
            f"[Result] search items={len(response.get('items', []))}"
        )
        return response


    def fetch_and_save_videos_from_channel(
        self,
        channel_id,
        published_after=None,
        published_before=None,
        max_results=50,
        get_duration=False,
    ):
        print(
            f"[YouTubeAPI] fetch_and_save_videos_from_channel: "
            f"channel_id={channel_id} get_duration={get_duration}"
        )

        channel_info = self.get_channel_with_cache(
            channel_id
        )

        if not channel_info:
            print(f"[Result] channel -> NOT_FOUND: channel_id={channel_id}")
            return

        next_page_token = None
        page = 0
        api_items = 0
        saved_items = 0

        while True:
            page += 1
            print(
                f"[API] search.list: page={page} channel_id={channel_id}"
            )
            response = self.client.call(
                "search",
                "list",
                part="id,snippet",
                channelId=channel_id,
                maxResults=max_results,
                order="date",
                publishedAfter=to_utc_z(published_after),
                publishedBefore=to_utc_z(published_before),
                pageToken=next_page_token,
                type="video",
            )

            items = response.get("items", [])
            api_items += len(items)
            video_ids = []

            for item in items:
                video = video_from_search_item(
                    item,
                    channel_id,
                )

                self.db.insert_video(video)
                saved_items += 1
                video_ids.append(video["video_id"])

            print(
                f"[DB] videos -> INSERT/UPSERT: count={len(video_ids)}"
            )

            if get_duration and video_ids:
                self.fetch_and_update_video_details(
                    video_ids
                )

            next_page_token = response.get(
                "nextPageToken"
            )

            if not next_page_token:
                break

        print(
            f"[Result] videos saved={saved_items} api_items={api_items} "
            f"pages={page}"
        )


    # ========================================================
    # Video details
    # ========================================================

    def get_video_details(
        self,
        video_id,
        part="snippet,contentDetails",
    ):
        print(
            f"[API] videos.list: video_id={video_id} part={part}"
        )
        response = self.client.call(
            "videos",
            "list",
            part=part,
            id=video_id,
        )

        items = response.get("items", [])

        if not items:
            print("[Result] video_details -> NOT_FOUND")
            return None

        print("[Result] video_details -> FOUND")
        return items[0]


    def get_video_details_with_cache(
        self,
        video_id,
        part="snippet,contentDetails",
    ):
        print(
            f"[YouTubeAPI] get_video_details_with_cache: video_id={video_id}"
        )
        print(
            "[Cache] video_details -> NOT_CHECKED "
            "(current implementation fetches from API)"
        )

        item = self.get_video_details(
            video_id,
            part=part,
        )

        if item is None:
            print("[Result] source=API result=NOT_FOUND")
            return None

        snippet = item.get("snippet", {})
        channel_id = snippet.get("channelId")
        channel_title = snippet.get("channelTitle")

        if not channel_id or not channel_title:
            print("[Result] source=API db_update=SKIPPED")
            return item

        self.db.insert_channel(
            channel_id,
            channel_title,
        )
        print(f"[DB] channel -> INSERT/IGNORE: channel_id={channel_id}")

        video = video_from_api_item(item)
        self.db.upsert_video(video)
        print(f"[DB] video -> UPSERT: video_id={video_id}")

        print("[Result] source=API db_update=COMPLETE")
        return item


    def fetch_and_update_video_details(self, video_ids):
        print(
            f"[YouTubeAPI] fetch_and_update_video_details: videos={len(video_ids)}"
        )

        updated = 0

        for batch_no, batch_ids in enumerate(
            _chunks(video_ids, 50),
            start=1,
        ):
            print(
                f"[API] videos.list: batch={batch_no} count={len(batch_ids)}"
            )
            response = self.client.call(
                "videos",
                "list",
                part="contentDetails",
                id=",".join(batch_ids),
            )

            batch_updated = 0

            for item in response.get("items", []):
                vid = item["id"]
                duration_iso = item["contentDetails"]["duration"]
                duration_sec = parse_duration(
                    duration_iso
                )

                self.db.update_video_duration(
                    vid,
                    duration_sec,
                )
                batch_updated += 1
                updated += 1

            print(
                f"[DB] video duration -> UPDATE: count={batch_updated}"
            )

        print(f"[Result] duration updated={updated}")


    # ========================================================
    # Live streaming
    # ========================================================

    def is_live_state_cache_valid(
        self,
        state,
        now=None,
    ):
        if state is None:
            return False

        if now is None:
            now = datetime.now(timezone.utc)

        checked_at = datetime.fromisoformat(
            state["checked_at"].replace(
                "Z",
                "+00:00",
            )
        )

        return now - checked_at < LIVE_STATE_TTL

    def get_live_streaming_video_ids(
        self,
        video_ids,
        now=None,
    ):
        print(
            f"[YouTubeAPI] get_live_streaming_video_ids: videos={len(video_ids)}"
        )

        live_video_ids = set()
        uncached_video_ids = []
        cache_hit = 0
        cache_expired = 0
        cache_missing = 0

        if now is None:
            now = datetime.now(timezone.utc)

        for video_id in video_ids:
            state = self.db.get_video_live_state(
                video_id
            )

            if state is None:
                cache_missing += 1
                uncached_video_ids.append(video_id)
                continue

            if not self.is_live_state_cache_valid(
                state,
                now=now,
            ):
                cache_expired += 1
                uncached_video_ids.append(video_id)
                continue

            cache_hit += 1

            if state["is_live"]:
                live_video_ids.add(video_id)

        print(
            f"[Cache] live_state: HIT={cache_hit} "
            f"EXPIRED={cache_expired} NOT_FOUND={cache_missing}"
        )

        api_batches = 0
        api_items = 0
        db_updated = 0

        for batch_no, batch_ids in enumerate(
            _chunks(uncached_video_ids, 50),
            start=1,
        ):
            if not batch_ids:
                continue

            api_batches += 1
            print(
                f"[API] videos.list: batch={batch_no} "
                f"count={len(batch_ids)} part=liveStreamingDetails"
            )
            response = self.client.call(
                "videos",
                "list",
                part="liveStreamingDetails",
                id=",".join(batch_ids),
            )

            checked_at = now.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            returned_video_ids = set()

            for item in response.get("items", []):
                video_id = item["id"]
                returned_video_ids.add(video_id)
                api_items += 1

                is_live = "liveStreamingDetails" in item

                self.db.set_video_live_state(
                    video_id,
                    is_live,
                    checked_at,
                )
                db_updated += 1

                if is_live:
                    live_video_ids.add(video_id)

            for video_id in batch_ids:
                if video_id not in returned_video_ids:
                    self.db.set_video_live_state(
                        video_id,
                        False,
                        checked_at,
                    )
                    db_updated += 1

        print(
            f"[DB] live_state -> UPDATE: count={db_updated}"
        )
        print(
            f"[Result] live={len(live_video_ids)} "
            f"cache_hits={cache_hit} api_batches={api_batches} api_items={api_items}"
        )

        return live_video_ids
