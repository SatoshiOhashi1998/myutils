# fetch_youtube_data.py
# ---------------------------------------------
# YouTube Data API

import os
from datetime import datetime

import isodate
from dotenv import load_dotenv
from googleapiclient.discovery import build

from .youtube_db import YouTubeDB
from .converters import (
    channel_from_api_item,
    parse_duration,
    video_from_api_item,
    video_from_search_item,
)


load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")


# =============================================
# Utility / Conversion
# =============================================

def _to_utc_z(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")

    if isinstance(value, str) and not value.endswith("Z"):
        return value + "Z"

    return value

def _chunks(values, size):
    for i in range(0, len(values), size):
        yield values[i:i + size]


# =============================================
# API Response Converters
# =============================================
def _video_data(
    video_id,
    snippet,
    channel_id=None,
    duration=None,
):
    thumbnails = snippet.get("thumbnails", {})

    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "channel_id": channel_id,
        "published_at": snippet.get("publishedAt"),
        "duration": duration,
        "thumbnail_default": thumbnails.get("default", {}).get("url"),
        "thumbnail_medium": thumbnails.get("medium", {}).get("url"),
        "thumbnail_high": thumbnails.get("high", {}).get("url"),
    }


# =============================================
# YouTube API
# =============================================

class YouTubeAPI:

    # -----------------------------------------
    # Initialization
    # -----------------------------------------

    def __init__(self, youtube=None, db=None):
        self.youtube = (
            youtube
            if youtube is not None
            else build("youtube", "v3", developerKey=API_KEY)
        )
        self.db = db if db is not None else YouTubeDB()

    def call_api(self, resource, method, **params):
        func = getattr(getattr(self.youtube, resource)(), method)
        return func(**params).execute()

    # -----------------------------------------
    # Cache
    # -----------------------------------------

    def get_video_with_cache(self, video_id):
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
        video = video_from_api_item(item)

        self.get_channel_with_cache(video["channel_id"])
        self.db.insert_video(video)

        return video

    def get_channel_with_cache(self, channel_id):
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

        channel = channel_from_api_item(items[0])

        self.db.insert_channel(
            channel["channel_id"],
            channel["channel_title"],
        )

        return (
            channel["channel_id"],
            channel["channel_title"],
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
            response = self.call_api(
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

    # -----------------------------------------
    # Update Video Details
    # -----------------------------------------

    def fetch_and_update_video_details(self, video_ids):
        for batch_ids in _chunks(video_ids, 50):

            response = self.call_api(
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

        return self.call_api(
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

        return self.call_api(
            "playlistItems",
            "list",
            **params,
        )

    # -----------------------------------------
    # Live Streaming
    # -----------------------------------------

    def get_live_streaming_video_ids(self, video_ids):
        live_video_ids = set()

        for batch_ids in _chunks(video_ids, 50):

            if not batch_ids:
                continue

            response = self.call_api(
                "videos",
                "list",
                part="liveStreamingDetails",
                id=",".join(batch_ids),
            )

            for item in response.get("items", []):
                if "liveStreamingDetails" in item:
                    live_video_ids.add(item["id"])

        return live_video_ids
