from datetime import datetime
from unittest.mock import MagicMock

from myutils.youtube_api.fetch_youtube_data import (
    YouTubeAPI,
    _chunks,
    _to_utc_z,
)
from myutils.youtube_api.youtube_db import YouTubeDB


def create_api(tmp_path):
    return YouTubeAPI(
        client=MagicMock(),
        db=YouTubeDB(tmp_path / "youtube.db"),
    )


def insert_channel(db, channel_id="channel1", title="テストチャンネル"):
    db.insert_channel(channel_id, title)


def insert_video(
    db,
    video_id="video1",
    title="テスト動画",
    channel_id="channel1",
    published_at="2025-07-01T00:00:00Z",
    duration=None,
):
    db.insert_video(
        {
            "video_id": video_id,
            "title": title,
            "channel_id": channel_id,
            "published_at": published_at,
            "duration": duration,
        }
    )


# ----------------------------------------------------------------------
# Video cache
# ----------------------------------------------------------------------


def test_get_video_with_cache_returns_cached_video(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)
    insert_video(
        api.db,
        title="キャッシュ動画",
        duration=300,
    )

    api.client.call = MagicMock()

    result = api.get_video_with_cache("video1")

    assert result is not None
    assert result[0] == "video1"
    assert result[1] == "キャッシュ動画"
    assert result[2] == "channel1"
    assert result[3] == "2025-07-01T00:00:00Z"
    assert result[4] == 300
    api.client.call.assert_not_called()


def test_get_video_with_cache_fetches_from_api(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "テスト動画",
                    "channelId": "channel1",
                    "publishedAt": "2025-07-01T00:00:00Z",
                    "thumbnails": {
                        "default": {"url": "default.jpg"},
                        "medium": {"url": "medium.jpg"},
                        "high": {"url": "high.jpg"},
                    },
                },
                "contentDetails": {
                    "duration": "PT5M",
                },
            }
        ]
    }
    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    result = api.get_video_with_cache("video1")

    assert result == {
        "video_id": "video1",
        "title": "テスト動画",
        "channel_id": "channel1",
        "published_at": "2025-07-01T00:00:00Z",
        "duration": 300,
        "thumbnail_default": "default.jpg",
        "thumbnail_medium": "medium.jpg",
        "thumbnail_high": "high.jpg",
    }

    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="snippet,contentDetails",
        id="video1",
    )
    api.get_channel_with_cache.assert_called_once_with("channel1")

    cached = api.db.get_video_by_id("video1")
    assert cached is not None
    assert cached[1] == "テスト動画"
    assert cached[4] == 300


def test_get_video_with_cache_returns_none_when_api_returns_no_items(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": []}

    result = api.get_video_with_cache("video1")

    assert result is None


def test_get_video_with_cache_returns_none_when_api_response_has_no_items_key(
    tmp_path,
):
    api = create_api(tmp_path)
    api.client.call.return_value = {}

    result = api.get_video_with_cache("video1")

    assert result is None


def test_get_video_with_cache_handles_invalid_duration(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "テスト動画",
                    "channelId": "channel1",
                },
                "contentDetails": {
                    "duration": "invalid",
                },
            }
        ]
    }
    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    result = api.get_video_with_cache("video1")

    assert result["duration"] is None


# ----------------------------------------------------------------------
# Channel cache
# ----------------------------------------------------------------------


def test_get_channel_with_cache_returns_cached_channel(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)
    api.client.call = MagicMock()

    result = api.get_channel_with_cache("channel1")

    assert result == ("channel1", "テストチャンネル")
    api.client.call.assert_not_called()


def test_get_channel_with_cache_fetches_from_api(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {
        "items": [
            {
                "id": "channel1",
                "snippet": {
                    "title": "APIチャンネル",
                },
            }
        ]
    }

    result = api.get_channel_with_cache("channel1")

    assert result == ("channel1", "APIチャンネル")
    api.client.call.assert_called_once_with(
        "channels",
        "list",
        part="snippet",
        id="channel1",
    )
    assert api.db.get_channel_by_id("channel1") == (
        "channel1",
        "APIチャンネル",
    )


def test_get_channel_with_cache_returns_none_when_not_found(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {}

    result = api.get_channel_with_cache("channel1")

    assert result is None


# ----------------------------------------------------------------------
# fetch_and_save_videos_from_channel
# ----------------------------------------------------------------------


def test_fetch_and_save_videos_from_channel_saves_videos(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)
    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    api.client.call.return_value = {
        "items": [
            {
                "id": {"videoId": "video1"},
                "snippet": {
                    "title": "動画1",
                    "publishedAt": "2025-07-01T00:00:00Z",
                    "thumbnails": {
                        "default": {"url": "default1.jpg"},
                        "medium": {"url": "medium1.jpg"},
                        "high": {"url": "high1.jpg"},
                    },
                },
            },
            {
                "id": {"videoId": "video2"},
                "snippet": {
                    "title": "動画2",
                    "publishedAt": "2025-07-02T00:00:00Z",
                    "thumbnails": {},
                },
            },
        ]
    }

    api.fetch_and_save_videos_from_channel("channel1")

    video1 = api.db.get_video_by_id("video1")
    video2 = api.db.get_video_by_id("video2")

    assert video1[1] == "動画1"
    assert video1[2] == "channel1"
    assert video1[3] == "2025-07-01T00:00:00Z"
    assert video1[4] is None
    assert video1[5] == "default1.jpg"
    assert video1[6] == "medium1.jpg"
    assert video1[7] == "high1.jpg"

    assert video2[1] == "動画2"

    api.client.call.assert_called_once_with(
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


def test_fetch_and_save_videos_from_channel_does_nothing_when_channel_missing(
    tmp_path,
):
    api = create_api(tmp_path)
    api.get_channel_with_cache = MagicMock(return_value=None)

    api.fetch_and_save_videos_from_channel("channel1")

    api.get_channel_with_cache.assert_called_once_with("channel1")
    api.client.call.assert_not_called()


def test_fetch_and_save_videos_from_channel_converts_datetime_to_utc_z(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)
    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )
    api.client.call.return_value = {"items": []}

    api.fetch_and_save_videos_from_channel(
        "channel1",
        published_after=datetime(2025, 7, 1, 12, 30, 0),
        published_before=datetime(2025, 7, 2, 12, 30, 0),
    )

    api.client.call.assert_called_once_with(
        "search",
        "list",
        part="id,snippet",
        channelId="channel1",
        maxResults=50,
        order="date",
        publishedAfter="2025-07-01T12:30:00Z",
        publishedBefore="2025-07-02T12:30:00Z",
        pageToken=None,
        type="video",
    )


def test_fetch_and_save_videos_from_channel_handles_pagination(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)
    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )
    api.client.call.side_effect = [
        {
            "items": [
                {
                    "id": {"videoId": "video1"},
                    "snippet": {"title": "動画1"},
                }
            ],
            "nextPageToken": "page2",
        },
        {
            "items": [
                {
                    "id": {"videoId": "video2"},
                    "snippet": {"title": "動画2"},
                }
            ]
        },
    ]

    api.fetch_and_save_videos_from_channel("channel1")

    assert api.db.get_video_by_id("video1") is not None
    assert api.db.get_video_by_id("video2") is not None
    assert api.client.call.call_count == 2
    assert api.client.call.call_args_list[0].kwargs["pageToken"] is None
    assert api.client.call.call_args_list[1].kwargs["pageToken"] == "page2"


def test_fetch_and_save_videos_from_channel_gets_duration_when_requested(
    tmp_path,
):
    api = create_api(tmp_path)
    insert_channel(api.db)
    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )
    api.client.call.return_value = {
        "items": [
            {
                "id": {"videoId": "video1"},
                "snippet": {"title": "動画1"},
            }
        ]
    }
    api.fetch_and_update_video_details = MagicMock()

    api.fetch_and_save_videos_from_channel(
        "channel1",
        get_duration=True,
    )

    api.fetch_and_update_video_details.assert_called_once_with(["video1"])


def test_fetch_and_save_videos_from_channel_does_not_fetch_duration_by_default(
    tmp_path,
):
    api = create_api(tmp_path)
    insert_channel(api.db)
    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )
    api.client.call.return_value = {
        "items": [
            {
                "id": {"videoId": "video1"},
                "snippet": {"title": "動画1"},
            }
        ]
    }

    api.fetch_and_save_videos_from_channel("channel1")

    assert api.client.call.call_count == 1
    assert api.client.call.call_args.args[:2] == ("search", "list")


# ----------------------------------------------------------------------
# fetch_and_update_video_details
# ----------------------------------------------------------------------


def test_fetch_and_update_video_details_updates_duration(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)
    insert_video(api.db, duration=None)

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "contentDetails": {
                    "duration": "PT10M",
                },
            }
        ]
    }

    api.fetch_and_update_video_details(["video1"])

    assert api.db.get_video_by_id("video1")[4] == 600
    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="contentDetails",
        id="video1",
    )


def test_fetch_and_update_video_details_sends_exactly_50_ids_in_one_request(
    tmp_path,
):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": []}

    video_ids = [f"video{i}" for i in range(50)]
    api.fetch_and_update_video_details(video_ids)

    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="contentDetails",
        id=",".join(video_ids),
    )


def test_fetch_and_update_video_details_batches_51_ids_into_50_and_1(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": []}

    video_ids = [f"video{i}" for i in range(51)]
    api.fetch_and_update_video_details(video_ids)

    assert api.client.call.call_count == 2

    first_ids = api.client.call.call_args_list[0].kwargs["id"].split(",")
    second_ids = api.client.call.call_args_list[1].kwargs["id"].split(",")

    assert len(first_ids) == 50
    assert len(second_ids) == 1
    assert second_ids == ["video50"]


def test_fetch_and_update_video_details_updates_only_items_returned_by_api(
    tmp_path,
):
    api = create_api(tmp_path)
    insert_channel(api.db)
    insert_video(api.db, "video1", duration=None)
    insert_video(api.db, "video2", duration=None)
    insert_video(api.db, "video3", duration=None)

    api.client.call.return_value = {
        "items": [
            {
                "id": "video2",
                "contentDetails": {
                    "duration": "PT7M",
                },
            }
        ]
    }

    api.fetch_and_update_video_details(
        ["video1", "video2", "video3"]
    )

    assert api.db.get_video_by_id("video1")[4] is None
    assert api.db.get_video_by_id("video2")[4] == 420
    assert api.db.get_video_by_id("video3")[4] is None


def test_fetch_and_update_video_details_does_nothing_for_empty_ids(tmp_path):
    api = create_api(tmp_path)

    api.fetch_and_update_video_details([])

    api.client.call.assert_not_called()


# ----------------------------------------------------------------------
# get_channel_videos_with_cache
# ----------------------------------------------------------------------


def test_get_channel_videos_with_cache_returns_cached_videos(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)
    insert_video(
        api.db,
        published_at="2025-07-01T12:00:00Z",
        duration=300,
    )

    api.fetch_and_save_videos_from_channel = MagicMock()

    result = api.get_channel_videos_with_cache(
        "channel1",
        "2025-07-01T00:00:00Z",
        "2025-07-02T00:00:00Z",
    )

    assert len(result) == 1
    assert result[0][0] == "video1"
    api.fetch_and_save_videos_from_channel.assert_not_called()


def test_get_channel_videos_with_cache_fetches_when_cache_is_empty(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)

    def save_video(*args, **kwargs):
        insert_video(
            api.db,
            title="API動画",
            published_at="2025-07-01T12:00:00Z",
        )

    api.fetch_and_save_videos_from_channel = MagicMock(
        side_effect=save_video
    )

    result = api.get_channel_videos_with_cache(
        "channel1",
        "2025-07-01T00:00:00Z",
        "2025-07-02T00:00:00Z",
    )

    assert len(result) == 1
    assert result[0][0] == "video1"
    api.fetch_and_save_videos_from_channel.assert_called_once_with(
        "channel1",
        published_after="2025-07-01T00:00:00Z",
        published_before="2025-07-02T00:00:00Z",
    )


def test_get_channel_videos_with_cache_adds_z_to_datetime_strings(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)
    api.fetch_and_save_videos_from_channel = MagicMock()

    api.get_channel_videos_with_cache(
        "channel1",
        "2025-07-01T00:00:00",
        "2025-07-02T00:00:00",
    )

    api.fetch_and_save_videos_from_channel.assert_called_once_with(
        "channel1",
        published_after="2025-07-01T00:00:00Z",
        published_before="2025-07-02T00:00:00Z",
    )


# ----------------------------------------------------------------------
# Search / details / playlist
# ----------------------------------------------------------------------


def test_search_videos_passes_all_parameters(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": []}

    result = api.search_videos(
        query="Python",
        channel_id="channel1",
        published_after=datetime(2025, 7, 1, 12, 30, 0),
        published_before=datetime(2025, 7, 2, 12, 30, 0),
        event_type="completed",
        max_results=10,
        order="date",
        page_token="page2",
    )

    assert result == {"items": []}
    api.client.call.assert_called_once_with(
        "search",
        "list",
        part="snippet",
        type="video",
        maxResults=10,
        order="date",
        q="Python",
        channelId="channel1",
        publishedAfter="2025-07-01T12:30:00Z",
        publishedBefore="2025-07-02T12:30:00Z",
        eventType="completed",
        pageToken="page2",
    )


def test_search_videos_omits_unspecified_optional_parameters(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": []}

    api.search_videos()

    api.client.call.assert_called_once_with(
        "search",
        "list",
        part="snippet",
        type="video",
        maxResults=50,
        order="date",
    )


def test_get_video_details_returns_first_item(tmp_path):
    api = create_api(tmp_path)
    item = {
        "id": "video1",
        "snippet": {"title": "テスト動画"},
    }
    api.client.call.return_value = {
        "items": [item, {"id": "video2"}],
    }

    result = api.get_video_details("video1")

    assert result == item
    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="snippet,contentDetails",
        id="video1",
    )


def test_get_video_details_returns_none_when_not_found(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": []}

    assert api.get_video_details("video1") is None


def test_get_video_details_uses_custom_part(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": [{"id": "video1"}]}

    api.get_video_details("video1", part="snippet")

    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="snippet",
        id="video1",
    )


def test_get_playlist_items_passes_page_token(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": []}

    result = api.get_playlist_items(
        "playlist1",
        max_results=20,
        page_token="page2",
    )

    assert result == {"items": []}
    api.client.call.assert_called_once_with(
        "playlistItems",
        "list",
        part="snippet",
        playlistId="playlist1",
        maxResults=20,
        pageToken="page2",
    )


def test_get_playlist_items_omits_page_token_when_not_provided(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": []}

    api.get_playlist_items("playlist1")

    api.client.call.assert_called_once_with(
        "playlistItems",
        "list",
        part="snippet",
        playlistId="playlist1",
        maxResults=50,
    )


# ----------------------------------------------------------------------
# Live streaming
# ----------------------------------------------------------------------


def test_get_live_streaming_video_ids_returns_live_video_ids(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2025-07-01T00:00:00Z",
                },
            },
            {"id": "video2"},
            {
                "id": "video3",
                "liveStreamingDetails": {
                    "scheduledStartTime": "2025-07-02T00:00:00Z",
                },
            },
        ]
    }

    result = api.get_live_streaming_video_ids(
        ["video1", "video2", "video3"]
    )

    assert result == {"video1", "video3"}
    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="liveStreamingDetails",
        id="video1,video2,video3",
    )


def test_get_live_streaming_video_ids_batches_51_ids(tmp_path):
    api = create_api(tmp_path)
    api.client.call.return_value = {"items": []}

    video_ids = [f"video{i}" for i in range(51)]

    result = api.get_live_streaming_video_ids(video_ids)

    assert result == set()
    assert api.client.call.call_count == 2

    first_ids = api.client.call.call_args_list[0].kwargs["id"].split(",")
    second_ids = api.client.call.call_args_list[1].kwargs["id"].split(",")

    assert len(first_ids) == 50
    assert len(second_ids) == 1


def test_get_live_streaming_video_ids_returns_empty_set_for_empty_input(tmp_path):
    api = create_api(tmp_path)

    assert api.get_live_streaming_video_ids([]) == set()
    api.client.call.assert_not_called()


# ----------------------------------------------------------------------
# get_video_details_with_cache
# ----------------------------------------------------------------------


def test_get_video_details_with_cache_saves_channel_and_video(tmp_path):
    api = create_api(tmp_path)
    item = {
        "id": "video1",
        "snippet": {
            "title": "テスト動画",
            "channelId": "channel1",
            "channelTitle": "テストチャンネル",
            "publishedAt": "2025-07-01T00:00:00Z",
            "thumbnails": {},
        },
        "contentDetails": {
            "duration": "PT5M",
        },
    }
    api.get_video_details = MagicMock(return_value=item)

    result = api.get_video_details_with_cache("video1")

    assert result is item
    assert api.db.get_channel_by_id("channel1") == (
        "channel1",
        "テストチャンネル",
    )

    cached_video = api.db.get_video_by_id("video1")
    assert cached_video is not None
    assert cached_video[1] == "テスト動画"
    assert cached_video[2] == "channel1"
    assert cached_video[4] == 300


def test_get_video_details_with_cache_returns_none_when_not_found(tmp_path):
    api = create_api(tmp_path)
    api.get_video_details = MagicMock(return_value=None)

    assert api.get_video_details_with_cache("video1") is None


def test_get_video_details_with_cache_uses_custom_part(tmp_path):
    api = create_api(tmp_path)
    item = {
        "id": "video1",
        "snippet": {
            "channelId": "channel1",
            "channelTitle": "テストチャンネル",
        },
    }
    api.get_video_details = MagicMock(return_value=item)

    result = api.get_video_details_with_cache(
        "video1",
        part="snippet",
    )

    assert result is item
    api.get_video_details.assert_called_once_with(
        "video1",
        part="snippet",
    )


def test_get_video_details_with_cache_does_not_save_when_channel_id_missing(
    tmp_path,
):
    api = create_api(tmp_path)
    item = {
        "id": "video1",
        "snippet": {
            "channelTitle": "テストチャンネル",
        },
    }
    api.get_video_details = MagicMock(return_value=item)
    api.db.insert_channel = MagicMock()
    api.db.upsert_video = MagicMock()

    result = api.get_video_details_with_cache("video1")

    assert result is item
    api.db.insert_channel.assert_not_called()
    api.db.upsert_video.assert_not_called()


def test_get_video_details_with_cache_does_not_save_when_channel_title_missing(
    tmp_path,
):
    api = create_api(tmp_path)
    item = {
        "id": "video1",
        "snippet": {
            "channelId": "channel1",
        },
    }
    api.get_video_details = MagicMock(return_value=item)
    api.db.insert_channel = MagicMock()
    api.db.upsert_video = MagicMock()

    result = api.get_video_details_with_cache("video1")

    assert result is item
    api.db.insert_channel.assert_not_called()
    api.db.upsert_video.assert_not_called()


def test_get_video_details_with_cache_preserves_existing_duration(tmp_path):
    api = create_api(tmp_path)
    insert_channel(api.db)
    insert_video(api.db, duration=300)

    item = {
        "id": "video1",
        "snippet": {
            "title": "更新タイトル",
            "channelId": "channel1",
            "channelTitle": "テストチャンネル",
            "publishedAt": "2025-07-02T00:00:00Z",
            "thumbnails": {},
        },
        "contentDetails": {},
    }
    api.get_video_details = MagicMock(return_value=item)

    api.get_video_details_with_cache("video1")

    result = api.db.get_video_by_id("video1")
    assert result[1] == "更新タイトル"
    assert result[4] == 300


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def test_to_utc_z_converts_datetime():
    value = datetime(2025, 7, 1, 12, 30, 45)

    assert _to_utc_z(value) == "2025-07-01T12:30:45Z"


def test_to_utc_z_adds_z_to_string_without_z():
    value = "2025-07-01T12:30:45"

    assert _to_utc_z(value) == "2025-07-01T12:30:45Z"


def test_to_utc_z_keeps_string_with_z():
    value = "2025-07-01T12:30:45Z"

    assert _to_utc_z(value) == value


def test_to_utc_z_keeps_none():
    assert _to_utc_z(None) is None


def test_chunks_splits_sequence():
    result = list(_chunks(list(range(5)), 2))

    assert result == [
        [0, 1],
        [2, 3],
        [4],
    ]


def test_chunks_returns_empty_for_empty_sequence():
    assert list(_chunks([], 50)) == []


def test_chunks_keeps_exact_50_items_in_one_chunk():
    values = list(range(50))

    result = list(_chunks(values, 50))

    assert result == [values]
