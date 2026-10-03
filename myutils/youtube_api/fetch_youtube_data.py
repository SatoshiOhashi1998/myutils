# fetch_youtube_data.py
# ---------------------------------------------
# YouTube Data API

from datetime import datetime, timezone, timedelta

from .converters import (
    channel_from_api_item,
    parse_duration,
    video_from_api_item,
    video_from_playlist_item,
    video_from_search_item,
)
    
# =============================================
# Utility / Conversion
# =============================================

LIVE_STATE_TTL = timedelta(hours=3)

def _to_utc_z(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    if isinstance(value, str):
        if value.endswith("Z"):
            return value

        if len(value) == 10:
            return value + "T00:00:00Z"

        return value + "Z"

    return value

def _chunks(values, size):
    for i in range(0, len(values), size):
        yield values[i:i + size]


# =============================================
# YouTube API
# =============================================

class YouTubeAPI:
    def __init__(self, client, db):
        self.client = client
        self.db = db

    # -----------------------------------------
    # Cache
    # -----------------------------------------

    def get_video_with_cache(self, video_id):
        result = self.db.get_video_by_id(video_id)

        if result:
            return result

        response = self.client.call(
            "videos",
            "list",
            part="snippet,contentDetails",
            id=video_id,
        )

        items = response.get("items", [])
        if not items:
            return None

        item = items[0]
        video = video_from_api_item(item)

        self.get_channel_with_cache(video["channel_id"])
        self.db.insert_video(video)

        return video

    def get_channel_uploads_playlist_id(self, channel_id):
        state = self.db.get_channel_sync_state(channel_id)

        if state and state[1]:
            return state[1]

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

        content_details = item.get("contentDetails", {})
        related_playlists = content_details.get(
            "relatedPlaylists",
            {},
        )

        uploads_playlist_id = related_playlists.get("uploads")

        if not uploads_playlist_id:
            return None

        snippet = item.get("snippet", {})
        channel_title = snippet.get("title")

        if channel_title:
            self.db.insert_channel(
                channel_id,
                channel_title,
            )

        self.db.set_channel_sync_state(
            channel_id,
            uploads_playlist_id=uploads_playlist_id,
        )

        return uploads_playlist_id

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

    def get_channel_with_cache(self, channel_id):
        result = self.db.get_channel_by_id(channel_id)

        if result:
            return result

        response = self.client.call(
            "channels",
            "list",
            part="snippet",
            id=channel_id,
        )

        items = response.get("items", [])
        if not items:
            return None

        channel = channel_from_api_item(items[0])

        self.db.insert_channel(
            channel["channel_id"],
            channel["channel_title"],
        )

        return (
            channel["channel_id"],
            channel["channel_title"],
        )

    def is_channel_sync_complete(
        self,
        channel_id,
        start_date,
        end_date,
    ):
        state = self.db.get_channel_sync_state(channel_id)

        if not state:
            return False

        oldest_synced_at = state[2]
        newest_synced_at = state[3]

        if not oldest_synced_at or not newest_synced_at:
            return False

        start = _to_utc_z(start_date)
        end = _to_utc_z(end_date)

        return (
            oldest_synced_at <= start
            and newest_synced_at >= end
        )

    # -----------------------------------------
    # Fetch / Save Videos
    # -----------------------------------------

    def fetch_and_save_videos_from_channel(
        self,
        channel_id,
        published_after=None,
        published_before=None,
        max_results=50,
        get_duration=False,
    ):
        channel_info = self.get_channel_with_cache(channel_id)

        if not channel_info:
            print(f"Channel {channel_id} not found")
            return

        next_page_token = None

        while True:
            response = self.client.call(
                "search",
                "list",
                part="id,snippet",
                channelId=channel_id,
                maxResults=max_results,
                order="date",
                publishedAfter=_to_utc_z(published_after),
                publishedBefore=_to_utc_z(published_before),
                pageToken=next_page_token,
                type="video",
            )

            video_ids = []

            for item in response.get("items", []):
                video = video_from_search_item(item, channel_id)

                self.db.insert_video(video)
                video_ids.append(video["video_id"])

            if get_duration and video_ids:
                self.fetch_and_update_video_details(video_ids)

            next_page_token = response.get("nextPageToken")

            if not next_page_token:
                break

    def get_channel_videos_with_cache(
        self,
        channel_id,
        start_date,
        end_date,
    ):
        start = _to_utc_z(start_date)
        end = _to_utc_z(end_date)

        results = self.db.get_videos_by_channel_and_date(
            channel_id,
            start,
            end,
        )

        if results:
            return results

        self.fetch_and_save_videos_from_channel(
            channel_id,
            published_after=start,
            published_before=end,
        )

        return self.db.get_videos_by_channel_and_date(
            channel_id,
            start,
            end,
        )

    def fetch_and_save_videos_from_playlist(
        self,
        playlist_id,
        channel_id,
        max_results=50,
    ):
        next_page_token = None

        while True:
            response = self.get_playlist_videos(
                playlist_id,
                max_results=max_results,
                page_token=next_page_token,
            )

            for item in response.get("items", []):
                video = video_from_playlist_item(item)

                if not video["video_id"]:
                    continue

                if not video["channel_id"]:
                    video["channel_id"] = channel_id

                self.db.insert_video(video)

            next_page_token = response.get("nextPageToken")

            if not next_page_token:
                break

    def sync_channel_videos(
        self,
        channel_id,
        start_date,
        end_date,
        max_results=50,
    ):
        start = _to_utc_z(start_date)
        end = _to_utc_z(end_date)

        if self.is_channel_sync_complete(
            channel_id,
            start,
            end,
        ):
            return True

        playlist_id = self.get_channel_uploads_playlist_id(
            channel_id
        )

        if not playlist_id:
            return False

        next_page_token = None
        oldest_published_at = None

        while True:
            response = self.get_playlist_videos(
                playlist_id,
                max_results=max_results,
                page_token=next_page_token,
            )

            items = response.get("items", [])

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

                oldest_published_at = published_at

            if not items:
                break

            if oldest_published_at and oldest_published_at < start:
                break

            next_page_token = response.get("nextPageToken")

            if not next_page_token:
                break

        self.db.set_channel_sync_state(
            channel_id,
            uploads_playlist_id=playlist_id,
            oldest_synced_at=start,
            newest_synced_at=end,
        )

        return True

    # -----------------------------------------
    # Update Video Details
    # -----------------------------------------

    def fetch_and_update_video_details(self, video_ids):
        for batch_ids in _chunks(video_ids, 50):

            response = self.client.call(
                "videos",
                "list",
                part="contentDetails",
                id=",".join(batch_ids),
            )

            for item in response.get("items", []):
                vid = item["id"]
                duration_iso = item["contentDetails"]["duration"]
                duration_sec = parse_duration(duration_iso)

                self.db.update_video_duration(
                    vid,
                    duration_sec,
                )

    # -----------------------------------------
    # Search
    # -----------------------------------------

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
            params["publishedAfter"] = _to_utc_z(published_after)

        if published_before is not None:
            params["publishedBefore"] = _to_utc_z(published_before)

        if event_type is not None:
            params["eventType"] = event_type

        if page_token is not None:
            params["pageToken"] = page_token

        return self.client.call(
            "search",
            "list",
            **params,
        )

    # -----------------------------------------
    # Video Details
    # -----------------------------------------

    def get_video_details(
        self,
        video_id,
        part="snippet,contentDetails",
    ):
        response = self.client.call(
            "videos",
            "list",
            part=part,
            id=video_id,
        )

        items = response.get("items", [])

        if not items:
            return None

        return items[0]

    def get_video_details_with_cache(
        self,
        video_id,
        part="snippet,contentDetails",
    ):
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

        self.db.insert_channel(
            channel_id,
            channel_title,
        )

        video = video_from_api_item(item)
        self.db.upsert_video(video)

        return item

    # -----------------------------------------
    # Playlist
    # -----------------------------------------

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

    # -----------------------------------------
    # Live Streaming
    # -----------------------------------------

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
            state["checked_at"].replace("Z", "+00:00")
        )

        return now - checked_at < LIVE_STATE_TTL


    def get_live_streaming_video_ids(self, video_ids, now=None):
        live_video_ids = set()
        uncached_video_ids = []

        if now is None:
            now = datetime.now(timezone.utc)


        for video_id in video_ids:
            state = self.db.get_video_live_state(video_id)

            if not self.is_live_state_cache_valid(state, now=now):
                uncached_video_ids.append(video_id)
                continue

            if state["is_live"]:
                live_video_ids.add(video_id)

        for batch_ids in _chunks(uncached_video_ids, 50):

            if not batch_ids:
                continue

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

                is_live = "liveStreamingDetails" in item

                self.db.set_video_live_state(
                    video_id,
                    is_live,
                    checked_at,
                )

                if is_live:
                    live_video_ids.add(video_id)

            for video_id in batch_ids:
                if video_id not in returned_video_ids:
                    self.db.set_video_live_state(
                        video_id,
                        False,
                        checked_at,
                    )

        return live_video_ids
