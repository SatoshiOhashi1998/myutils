from datetime import datetime
from unittest.mock import MagicMock

from myutils.youtube_api.fetch_youtube_data import (
    YouTubeAPI,
    _channel_from_api_item,
    _parse_duration,
    _to_utc_z,
    _video_from_api_item,
    _video_from_search_item,
    _chunks,
)
from myutils.youtube_api.youtube_db import YouTubeDB


def create_api(tmp_path):
    return YouTubeAPI(
        youtube=MagicMock(),
        db=YouTubeDB(tmp_path / "youtube.db"),
    )


# ============================================================
# call_api
# ============================================================


def test_call_api_delegates_to_youtube_resource():
    youtube = MagicMock()
    api = YouTubeAPI(youtube=youtube, db=MagicMock())

    expected = {"items": [{"id": "video1"}]}

    youtube.videos.return_value.list.return_value.execute.return_value = expected

    result = api.call_api(
        "videos",
        "list",
        part="snippet",
        id="video1",
    )

    assert result == expected
    youtube.videos.return_value.list.assert_called_once_with(
        part="snippet",
        id="video1",
    )
    youtube.videos.return_value.list.return_value.execute.assert_called_once()


# ============================================================
# get_video_with_cache
# ============================================================


def test_get_video_with_cache_returns_cached_video(tmp_path):
    api = create_api(tmp_path)

    api.db.insert_channel("channel1", "Channel 1")
    api.db.insert_video(
        {
            "video_id": "video1",
            "title": "Cached Video",
            "channel_id": "channel1",
            "published_at": "2026-01-01T00:00:00Z",
            "duration": 120,
        }
    )

    api.call_api = MagicMock()

    result = api.get_video_with_cache("video1")

    assert result[0] == "video1"
    assert result[1] == "Cached Video"
    api.call_api.assert_not_called()


def test_get_video_with_cache_fetches_from_api(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        side_effect=[
            {
                "items": [
                    {
                        "id": "video1",
                        "snippet": {
                            "title": "Test Video",
                            "channelId": "channel1",
                            "publishedAt": "2026-01-01T00:00:00Z",
                            "thumbnails": {},
                        },
                        "contentDetails": {
                            "duration": "PT2M",
                        },
                    }
                ]
            },
            {
                "items": [
                    {
                        "id": "channel1",
                        "snippet": {
                            "title": "Test Channel",
                        },
                    }
                ]
            },
        ]
    )

    result = api.get_video_with_cache("video1")

    assert result["video_id"] == "video1"
    assert result["title"] == "Test Video"
    assert result["channel_id"] == "channel1"
    assert result["duration"] == 120

    saved = api.db.get_video_by_id("video1")

    assert saved is not None
    assert saved[0] == "video1"
    assert saved[1] == "Test Video"
    assert saved[4] == 120

    assert api.call_api.call_count == 2
    api.call_api.assert_any_call(
        "videos",
        "list",
        part="snippet,contentDetails",
        id="video1",
    )
    api.call_api.assert_any_call(
        "channels",
        "list",
        part="snippet",
        id="channel1",
    )


def test_get_video_with_cache_returns_none_when_api_has_no_items(tmp_path):
    api = create_api(tmp_path)
    api.call_api = MagicMock(return_value={"items": []})

    result = api.get_video_with_cache("video1")

    assert result is None
    api.call_api.assert_called_once_with(
        "videos",
        "list",
        part="snippet,contentDetails",
        id="video1",
    )


def test_get_video_with_cache_converts_duration(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        side_effect=[
            {
                "items": [
                    {
                        "id": "video1",
                        "snippet": {
                            "title": "Test Video",
                            "channelId": "channel1",
                            "publishedAt": "2026-01-01T00:00:00Z",
                            "thumbnails": {},
                        },
                        "contentDetails": {
                            "duration": "PT1H2M3S",
                        },
                    }
                ]
            },
            {
                "items": [
                    {
                        "id": "channel1",
                        "snippet": {
                            "title": "Test Channel",
                        },
                    }
                ]
            },
        ]
    )

    result = api.get_video_with_cache("video1")

    assert result["duration"] == 3723


def test_get_video_with_cache_handles_invalid_duration(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        side_effect=[
            {
                "items": [
                    {
                        "id": "video1",
                        "snippet": {
                            "title": "Test Video",
                            "channelId": "channel1",
                            "publishedAt": "2026-01-01T00:00:00Z",
                            "thumbnails": {},
                        },
                        "contentDetails": {
                            "duration": "invalid",
                        },
                    }
                ]
            },
            {
                "items": [
                    {
                        "id": "channel1",
                        "snippet": {
                            "title": "Test Channel",
                        },
                    }
                ]
            },
        ]
    )

    result = api.get_video_with_cache("video1")

    assert result["duration"] is None


# ============================================================
# get_channel_with_cache
# ============================================================


def test_get_channel_with_cache_returns_cached_channel(tmp_path):
    api = create_api(tmp_path)

    api.db.insert_channel("channel1", "Cached Channel")
    api.call_api = MagicMock()

    result = api.get_channel_with_cache("channel1")

    assert result == ("channel1", "Cached Channel")
    api.call_api.assert_not_called()


def test_get_channel_with_cache_fetches_from_api(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [
                {
                    "id": "channel1",
                    "snippet": {
                        "title": "Test Channel",
                    },
                }
            ]
        }
    )

    result = api.get_channel_with_cache("channel1")

    assert result == ("channel1", "Test Channel")

    saved = api.db.get_channel_by_id("channel1")
    assert saved == ("channel1", "Test Channel")

    api.call_api.assert_called_once_with(
        "channels",
        "list",
        part="snippet",
        id="channel1",
    )


def test_get_channel_with_cache_returns_none_when_api_has_no_items(tmp_path):
    api = create_api(tmp_path)
    api.call_api = MagicMock(return_value={"items": []})

    result = api.get_channel_with_cache("channel1")

    assert result is None


# ============================================================
# fetch_and_save_videos_from_channel
# ============================================================


def test_fetch_and_save_videos_from_channel(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        side_effect=[
            {
                "items": [
                    {
                        "id": "channel1",
                        "snippet": {
                            "title": "Test Channel",
                        },
                    }
                ]
            },
            {
                "items": [
                    {
                        "id": {
                            "videoId": "video1",
                        },
                        "snippet": {
                            "title": "Video 1",
                            "publishedAt": "2026-01-01T00:00:00Z",
                            "thumbnails": {},
                        },
                    }
                ]
            },
        ]
    )

    api.fetch_and_save_videos_from_channel("channel1")

    result = api.db.get_video_by_id("video1")

    assert result is not None
    assert result[0] == "video1"
    assert result[1] == "Video 1"
    assert result[2] == "channel1"
    assert result[4] is None

    api.call_api.assert_any_call(
        "channels",
        "list",
        part="snippet",
        id="channel1",
    )
    api.call_api.assert_any_call(
        "search",
        "list",
        part="id,snippet",
        channelId="channel1",
        maxResults=50,
        order="date",
        publishedAfter=None,
        publishedBefore=None,
        pageToken=None,
        type="video",
    )


def test_fetch_and_save_videos_from_channel_returns_when_channel_not_found(
    tmp_path,
):
    api = create_api(tmp_path)

    api.call_api = MagicMock(return_value={"items": []})

    api.fetch_and_save_videos_from_channel("channel1")

    api.call_api.assert_called_once_with(
        "channels",
        "list",
        part="snippet",
        id="channel1",
    )


def test_fetch_and_save_videos_from_channel_converts_datetime_to_utc_z(tmp_path):
    api = create_api(tmp_path)

    published_after = datetime(2026, 1, 1, 12, 30, 0)
    published_before = datetime(2026, 1, 2, 12, 30, 0)

    api.call_api = MagicMock(
        side_effect=[
            {
                "items": [
                    {
                        "id": "channel1",
                        "snippet": {
                            "title": "Test Channel",
                        },
                    }
                ]
            },
            {
                "items": [],
            },
        ]
    )

    api.fetch_and_save_videos_from_channel(
        "channel1",
        published_after=published_after,
        published_before=published_before,
    )

    api.call_api.assert_any_call(
        "search",
        "list",
        part="id,snippet",
        channelId="channel1",
        maxResults=50,
        order="date",
        publishedAfter="2026-01-01T12:30:00Z",
        publishedBefore="2026-01-02T12:30:00Z",
        pageToken=None,
        type="video",
    )


def test_fetch_and_save_videos_from_channel_handles_pagination(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        side_effect=[
            {
                "items": [
                    {
                        "id": "channel1",
                        "snippet": {
                            "title": "Test Channel",
                        },
                    }
                ]
            },
            {
                "items": [
                    {
                        "id": {
                            "videoId": "video1",
                        },
                        "snippet": {
                            "title": "Video 1",
                            "publishedAt": "2026-01-01T00:00:00Z",
                            "thumbnails": {},
                        },
                    }
                ],
                "nextPageToken": "next-token",
            },
            {
                "items": [
                    {
                        "id": {
                            "videoId": "video2",
                        },
                        "snippet": {
                            "title": "Video 2",
                            "publishedAt": "2025-12-31T00:00:00Z",
                            "thumbnails": {},
                        },
                    }
                ],
            },
        ]
    )

    api.fetch_and_save_videos_from_channel("channel1")

    assert api.db.get_video_by_id("video1") is not None
    assert api.db.get_video_by_id("video2") is not None

    search_calls = [
        call
        for call in api.call_api.call_args_list
        if call.args[:2] == ("search", "list")
    ]

    assert len(search_calls) == 2
    assert search_calls[0].kwargs["pageToken"] is None
    assert search_calls[1].kwargs["pageToken"] == "next-token"


def test_fetch_and_save_videos_from_channel_get_duration(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        side_effect=[
            {
                "items": [
                    {
                        "id": "channel1",
                        "snippet": {
                            "title": "Test Channel",
                        },
                    }
                ]
            },
            {
                "items": [
                    {
                        "id": {
                            "videoId": "video1",
                        },
                        "snippet": {
                            "title": "Video 1",
                            "publishedAt": "2026-01-01T00:00:00Z",
                            "thumbnails": {},
                        },
                    }
                ],
            },
            {
                "items": [
                    {
                        "id": "video1",
                        "contentDetails": {
                            "duration": "PT3M",
                        },
                    }
                ],
            },
        ]
    )

    api.fetch_and_save_videos_from_channel(
        "channel1",
        get_duration=True,
    )

    result = api.db.get_video_by_id("video1")

    assert result[4] == 180

    api.call_api.assert_any_call(
        "videos",
        "list",
        part="contentDetails",
        id="video1",
    )


# ============================================================
# fetch_and_update_video_details
# ============================================================


def test_fetch_and_update_video_details_updates_duration(tmp_path):
    api = create_api(tmp_path)

    api.db.insert_channel("channel1", "Test Channel")
    api.db.insert_video(
        {
            "video_id": "video1",
            "title": "Video 1",
            "channel_id": "channel1",
            "published_at": "2026-01-01T00:00:00Z",
            "duration": None,
        }
    )

    api.call_api = MagicMock(
        return_value={
            "items": [
                {
                    "id": "video1",
                    "contentDetails": {
                        "duration": "PT2M30S",
                    },
                }
            ]
        }
    )

    api.fetch_and_update_video_details(["video1"])

    result = api.db.get_video_by_id("video1")

    assert result[4] == 150

    api.call_api.assert_called_once_with(
        "videos",
        "list",
        part="contentDetails",
        id="video1",
    )


def test_fetch_and_update_video_details_batches_50_ids(tmp_path):
    api = create_api(tmp_path)

    video_ids = [f"video{i}" for i in range(51)]

    api.call_api = MagicMock(
        return_value={
            "items": [],
        }
    )

    api.fetch_and_update_video_details(video_ids)

    calls = [
        call
        for call in api.call_api.call_args_list
        if call.args[:2] == ("videos", "list")
    ]

    assert len(calls) == 2
    assert len(calls[0].kwargs["id"].split(",")) == 50
    assert len(calls[1].kwargs["id"].split(",")) == 1


# ============================================================
# get_channel_videos_with_cache
# ============================================================


def test_get_channel_videos_with_cache_fetches_when_cache_is_empty(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        side_effect=[
            {
                "items": [
                    {
                        "id": "channel1",
                        "snippet": {
                            "title": "Test Channel",
                        },
                    }
                ]
            },
            {
                "items": [
                    {
                        "id": {
                            "videoId": "video1",
                        },
                        "snippet": {
                            "title": "Video 1",
                            "publishedAt": "2026-01-01T00:00:00Z",
                            "thumbnails": {},
                        },
                    }
                ],
            },
        ]
    )

    result = api.get_channel_videos_with_cache(
        "channel1",
        "2026-01-01T00:00:00",
        "2026-01-02T00:00:00",
    )

    assert len(result) == 1
    assert result[0][0] == "video1"


def test_get_channel_videos_with_cache_adds_z_to_string_dates(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        side_effect=[
            {
                "items": [
                    {
                        "id": "channel1",
                        "snippet": {
                            "title": "Test Channel",
                        },
                    }
                ]
            },
            {
                "items": [],
            },
        ]
    )

    api.get_channel_videos_with_cache(
        "channel1",
        "2026-01-01T00:00:00",
        "2026-01-02T00:00:00",
    )

    api.call_api.assert_any_call(
        "search",
        "list",
        part="id,snippet",
        channelId="channel1",
        maxResults=50,
        order="date",
        publishedAfter="2026-01-01T00:00:00Z",
        publishedBefore="2026-01-02T00:00:00Z",
        pageToken=None,
        type="video",
    )


def test_get_channel_videos_with_cache_returns_cached_videos(tmp_path):
    api = create_api(tmp_path)

    api.db.insert_channel("channel1", "Test Channel")
    api.db.insert_video(
        {
            "video_id": "video1",
            "title": "Cached Video",
            "channel_id": "channel1",
            "published_at": "2026-01-01T00:00:00Z",
            "duration": 120,
        }
    )

    api.call_api = MagicMock()

    result = api.get_channel_videos_with_cache(
        "channel1",
        "2026-01-01T00:00:00Z",
        "2026-01-02T00:00:00Z",
    )

    assert len(result) == 1
    assert result[0][0] == "video1"
    api.call_api.assert_not_called()


# ============================================================
# search_videos
# ============================================================


def test_search_videos_passes_all_parameters(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(return_value={"items": []})

    api.search_videos(
        query="test",
        channel_id="channel1",
        published_after=datetime(2026, 1, 1),
        published_before=datetime(2026, 1, 2),
        event_type="live",
        max_results=25,
        order="date",
        page_token="next-token",
    )

    api.call_api.assert_called_once_with(
        "search",
        "list",
        part="snippet",
        type="video",
        maxResults=25,
        order="date",
        q="test",
        channelId="channel1",
        publishedAfter="2026-01-01T00:00:00Z",
        publishedBefore="2026-01-02T00:00:00Z",
        eventType="live",
        pageToken="next-token",
    )


def test_search_videos_omits_optional_parameters(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(return_value={"items": []})

    api.search_videos()

    api.call_api.assert_called_once_with(
        "search",
        "list",
        part="snippet",
        type="video",
        maxResults=50,
        order="date",
    )


# ============================================================
# get_video_details
# ============================================================


def test_get_video_details_returns_first_item(tmp_path):
    api = create_api(tmp_path)

    item = {
        "id": "video1",
        "snippet": {
            "title": "Test Video",
        },
    }

    api.call_api = MagicMock(
        return_value={
            "items": [item],
        }
    )

    result = api.get_video_details("video1")

    assert result == item

    api.call_api.assert_called_once_with(
        "videos",
        "list",
        part="snippet,contentDetails",
        id="video1",
    )


def test_get_video_details_returns_none_when_not_found(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(return_value={"items": []})

    result = api.get_video_details("video1")

    assert result is None


# ============================================================
# get_playlist_items
# ============================================================


def test_get_playlist_items(tmp_path):
    api = create_api(tmp_path)

    response = {
        "items": [
            {
                "id": "item1",
            }
        ]
    }

    api.call_api = MagicMock(return_value=response)

    result = api.get_playlist_items(
        "playlist1",
        max_results=25,
        page_token="next-token",
    )

    assert result == response

    api.call_api.assert_called_once_with(
        "playlistItems",
        "list",
        part="snippet",
        playlistId="playlist1",
        maxResults=25,
        pageToken="next-token",
    )


# ============================================================
# get_live_streaming_video_ids
# ============================================================


def test_get_live_streaming_video_ids_filters_live_videos(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [
                {
                    "id": "video1",
                    "liveStreamingDetails": {},
                },
                {
                    "id": "video2",
                },
                {
                    "id": "video3",
                    "liveStreamingDetails": {},
                },
            ]
        }
    )

    result = api.get_live_streaming_video_ids(
        ["video1", "video2", "video3"]
    )

    assert result == {"video1", "video3"}

    api.call_api.assert_called_once_with(
        "videos",
        "list",
        part="liveStreamingDetails",
        id="video1,video2,video3",
    )


def test_get_live_streaming_video_ids_batches_50_ids(tmp_path):
    api = create_api(tmp_path)

    video_ids = [f"video{i}" for i in range(51)]

    api.call_api = MagicMock(
        return_value={
            "items": [],
        }
    )

    result = api.get_live_streaming_video_ids(video_ids)

    assert result == set()

    calls = [
        call
        for call in api.call_api.call_args_list
        if call.args[:2] == ("videos", "list")
    ]

    assert len(calls) == 2
    assert len(calls[0].kwargs["id"].split(",")) == 50
    assert len(calls[1].kwargs["id"].split(",")) == 1


# ============================================================
# get_video_details_with_cache
# ============================================================


def test_get_video_details_with_cache_saves_channel_and_video(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [
                {
                    "id": "video1",
                    "snippet": {
                        "title": "Test Video",
                        "channelId": "channel1",
                        "channelTitle": "Test Channel",
                        "publishedAt": "2026-01-01T00:00:00Z",
                        "thumbnails": {},
                    },
                    "contentDetails": {
                        "duration": "PT2M",
                    },
                }
            ]
        }
    )

    result = api.get_video_details_with_cache("video1")

    assert result["id"] == "video1"

    channel = api.db.get_channel_by_id("channel1")
    assert channel == ("channel1", "Test Channel")

    video = api.db.get_video_by_id("video1")
    assert video is not None
    assert video[0] == "video1"
    assert video[1] == "Test Video"
    assert video[4] == 120


def test_get_video_details_with_cache_returns_none_when_not_found(tmp_path):
    api = create_api(tmp_path)

    api.call_api = MagicMock(return_value={"items": []})

    result = api.get_video_details_with_cache("video1")

    assert result is None


def test_get_video_details_with_cache_returns_item_when_channel_info_missing(
    tmp_path,
):
    api = create_api(tmp_path)

    item = {
        "id": "video1",
        "snippet": {
            "title": "Test Video",
        },
        "contentDetails": {
            "duration": "PT2M",
        },
    }

    api.call_api = MagicMock(
        return_value={
            "items": [item],
        }
    )

    result = api.get_video_details_with_cache("video1")

    assert result == item
    assert api.db.get_video_by_id("video1") is None


def test_get_video_details_with_cache_preserves_existing_duration_when_missing(
    tmp_path,
):
    api = create_api(tmp_path)

    api.db.insert_channel("channel1", "Test Channel")
    api.db.insert_video(
        {
            "video_id": "video1",
            "title": "Old Title",
            "channel_id": "channel1",
            "published_at": "2026-01-01T00:00:00Z",
            "duration": 120,
        }
    )

    api.call_api = MagicMock(
        return_value={
            "items": [
                {
                    "id": "video1",
                    "snippet": {
                        "title": "New Title",
                        "channelId": "channel1",
                        "channelTitle": "Test Channel",
                        "publishedAt": "2026-01-01T00:00:00Z",
                        "thumbnails": {},
                    },
                    "contentDetails": {},
                }
            ]
        }
    )

    result = api.get_video_details_with_cache("video1")

    assert result["id"] == "video1"

    video = api.db.get_video_by_id("video1")

    assert video[1] == "New Title"
    assert video[4] == 120


# ============================================================
# _to_utc_z
# ============================================================


def test_to_utc_z_converts_datetime():
    value = datetime(2026, 1, 2, 3, 4, 5)

    assert _to_utc_z(value) == "2026-01-02T03:04:05Z"


def test_to_utc_z_adds_z_to_string():
    assert _to_utc_z("2026-01-02T03:04:05") == "2026-01-02T03:04:05Z"


def test_to_utc_z_keeps_existing_z():
    value = "2026-01-02T03:04:05Z"

    assert _to_utc_z(value) == value


def test_to_utc_z_returns_other_values_unchanged():
    assert _to_utc_z(None) is None


# ============================================================
# _parse_duration
# ============================================================


def test_parse_duration():
    assert _parse_duration("PT1H2M3S") == 3723


def test_parse_duration_returns_none_for_invalid_value():
    assert _parse_duration("invalid") is None


# ============================================================
# _video_from_search_item
# ============================================================


def test_video_from_search_item():
    item = {
        "id": {
            "videoId": "video1",
        },
        "snippet": {
            "title": "Test Video",
            "publishedAt": "2026-01-01T00:00:00Z",
            "thumbnails": {
                "default": {
                    "url": "default.jpg",
                },
                "medium": {
                    "url": "medium.jpg",
                },
                "high": {
                    "url": "high.jpg",
                },
            },
        },
    }

    result = _video_from_search_item(item, "channel1")

    assert result == {
        "video_id": "video1",
        "title": "Test Video",
        "channel_id": "channel1",
        "published_at": "2026-01-01T00:00:00Z",
        "duration": None,
        "thumbnail_default": "default.jpg",
        "thumbnail_medium": "medium.jpg",
        "thumbnail_high": "high.jpg",
    }


# ============================================================
# _video_from_api_item
# ============================================================

def test_video_from_api_item_handles_missing_fields():
    item = {
        "id": "video1",
        "snippet": {},
        "contentDetails": {},
    }

    result = _video_from_api_item(item)

    assert result == {
        "video_id": "video1",
        "title": "",
        "channel_id": None,
        "published_at": None,
        "duration": None,
        "thumbnail_default": None,
        "thumbnail_medium": None,
        "thumbnail_high": None,
    }

def test_video_from_api_item_handles_missing_content_details():
    item = {
        "id": "video1",
        "snippet": {
            "title": "Test Video",
            "channelId": "channel1",
            "publishedAt": "2026-01-01T00:00:00Z",
            "thumbnails": {},
        },
    }

    result = _video_from_api_item(item)

    assert result["video_id"] == "video1"
    assert result["title"] == "Test Video"
    assert result["channel_id"] == "channel1"
    assert result["duration"] is None

def test_video_from_api_item():
    item = {
        "id": "video1",
        "snippet": {
            "title": "Test Video",
            "channelId": "channel1",
            "publishedAt": "2026-01-01T00:00:00Z",
            "thumbnails": {
                "default": {
                    "url": "default.jpg",
                },
                "medium": {
                    "url": "medium.jpg",
                },
                "high": {
                    "url": "high.jpg",
                },
            },
        },
        "contentDetails": {
            "duration": "PT1M30S",
        },
    }

    result = _video_from_api_item(item)

    assert result == {
        "video_id": "video1",
        "title": "Test Video",
        "channel_id": "channel1",
        "published_at": "2026-01-01T00:00:00Z",
        "duration": 90,
        "thumbnail_default": "default.jpg",
        "thumbnail_medium": "medium.jpg",
        "thumbnail_high": "high.jpg",
    }


def test_video_from_api_item_without_duration():
    item = {
        "id": "video1",
        "snippet": {
            "title": "Test Video",
            "channelId": "channel1",
            "publishedAt": "2026-01-01T00:00:00Z",
            "thumbnails": {},
        },
        "contentDetails": {},
    }

    result = _video_from_api_item(item)

    assert result["duration"] is None


# ============================================================
# _channel_from_api_item
# ============================================================


def test_channel_from_api_item():
    item = {
        "id": "channel1",
        "snippet": {
            "title": "Test Channel",
        },
    }

    result = _channel_from_api_item(item)

    assert result == {
        "channel_id": "channel1",
        "channel_title": "Test Channel",
    }

def test_chunks():
    assert list(_chunks([1, 2, 3, 4, 5], 2)) == [
        [1, 2],
        [3, 4],
        [5],
    ]
