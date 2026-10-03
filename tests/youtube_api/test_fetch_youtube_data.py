from datetime import datetime, timezone
from unittest.mock import MagicMock

from myutils.youtube_api.fetch_youtube_data import (
    YouTubeAPI,
    _chunks,
    to_utc_z,
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


def test_fetch_and_save_videos_from_channel_converts_datetimeto_utc_z(tmp_path):
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


def testto_utc_z_converts_datetime():
    value = datetime(2025, 7, 1, 12, 30, 45)

    assert to_utc_z(value) == "2025-07-01T12:30:45Z"


def testto_utc_z_adds_z_to_string_without_z():
    value = "2025-07-01T12:30:45"

    assert to_utc_z(value) == "2025-07-01T12:30:45Z"


def testto_utc_z_keeps_string_with_z():
    value = "2025-07-01T12:30:45Z"

    assert to_utc_z(value) == value


def testto_utc_z_keeps_none():
    assert to_utc_z(None) is None


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

def test_get_channel_uploads_playlist_id_fetches_and_caches(tmp_path):
    client = MagicMock()
    db = YouTubeDB(tmp_path / "youtube.db")

    api = YouTubeAPI(
        client=client,
        db=db,
    )

    client.call.return_value = {
        "items": [
            {
                "id": "channel-1",
                "snippet": {
                    "title": "Test Channel",
                },
                "contentDetails": {
                    "relatedPlaylists": {
                        "uploads": "playlist-1",
                    },
                },
            }
        ]
    }

    playlist_id = api.get_channel_uploads_playlist_id(
        "channel-1"
    )

    assert playlist_id == "playlist-1"

    state = db.get_channel_sync_state("channel-1")

    assert state == (
        "channel-1",
        "playlist-1",
        None,
        None,
    )

    client.call.assert_called_once_with(
        "channels",
        "list",
        part="contentDetails,snippet",
        id="channel-1",
    )

def test_get_channel_uploads_playlist_id_uses_cache(tmp_path):
    client = MagicMock()
    db = YouTubeDB(tmp_path / "youtube.db")

    api = YouTubeAPI(
        client=client,
        db=db,
    )

    db.insert_channel(
        "channel-1",
        "Test Channel",
    )

    db.set_channel_sync_state(
        "channel-1",
        uploads_playlist_id="playlist-1",
    )

    playlist_id = api.get_channel_uploads_playlist_id(
        "channel-1"
    )

    assert playlist_id == "playlist-1"

    client.call.assert_not_called()

def test_get_playlist_videos(tmp_path):
    client = MagicMock()
    db = YouTubeDB(tmp_path / "youtube.db")

    api = YouTubeAPI(
        client=client,
        db=db,
    )

    client.call.return_value = {
        "items": [
            {
                "id": "playlist-item-1",
                "snippet": {
                    "resourceId": {
                        "videoId": "video-1",
                    },
                    "title": "Test Video",
                    "channelId": "channel-1",
                    "publishedAt": "2026-10-01T00:00:00Z",
                },
            }
        ],
        "nextPageToken": "next-token",
    }

    response = api.get_playlist_videos(
        "playlist-1",
        max_results=50,
    )

    assert response["items"][0]["snippet"]["resourceId"]["videoId"] == "video-1"
    assert response["nextPageToken"] == "next-token"

    client.call.assert_called_once_with(
        "playlistItems",
        "list",
        part="snippet,contentDetails",
        playlistId="playlist-1",
        maxResults=50,
    )

def test_fetch_and_save_videos_from_playlist(tmp_path):
    client = MagicMock()
    db = YouTubeDB(tmp_path / "youtube.db")

    db.insert_channel(
        "channel-1",
        "Test Channel",
    )

    api = YouTubeAPI(
        client=client,
        db=db,
    )

    client.call.side_effect = [
        {
            "items": [
                {
                    "snippet": {
                        "resourceId": {
                            "videoId": "video-1",
                        },
                        "title": "Video 1",
                        "channelId": "channel-1",
                        "publishedAt": "2026-10-01T00:00:00Z",
                    }
                }
            ],
            "nextPageToken": "next-token",
        },
        {
            "items": [
                {
                    "snippet": {
                        "resourceId": {
                            "videoId": "video-2",
                        },
                        "title": "Video 2",
                        "channelId": "channel-1",
                        "publishedAt": "2026-09-01T00:00:00Z",
                    }
                }
            ]
        },
    ]

    api.fetch_and_save_videos_from_playlist(
        playlist_id="playlist-1",
        channel_id="channel-1",
    )

    video_1 = db.get_video_by_id("video-1")
    video_2 = db.get_video_by_id("video-2")

    assert video_1[0] == "video-1"
    assert video_1[1] == "Video 1"

    assert video_2[0] == "video-2"
    assert video_2[1] == "Video 2"

    assert client.call.call_count == 2

    client.call.assert_any_call(
        "playlistItems",
        "list",
        part="snippet,contentDetails",
        playlistId="playlist-1",
        maxResults=50,
    )

    client.call.assert_any_call(
        "playlistItems",
        "list",
        part="snippet,contentDetails",
        playlistId="playlist-1",
        maxResults=50,
        pageToken="next-token",
    )

def test_is_channel_sync_complete(tmp_path):
    client = MagicMock()
    db = YouTubeDB(tmp_path / "youtube.db")

    db.insert_channel(
        "channel-1",
        "Test Channel",
    )

    db.set_channel_sync_state(
        "channel-1",
        uploads_playlist_id="playlist-1",
        oldest_synced_at="2026-01-01T00:00:00Z",
        newest_synced_at="2026-10-01T00:00:00Z",
    )

    api = YouTubeAPI(
        client=client,
        db=db,
    )

    assert api.is_channel_sync_complete(
        "channel-1",
        "2026-03-01",
        "2026-09-01",
    ) is True

    assert api.is_channel_sync_complete(
        "channel-1",
        "2025-12-01",
        "2026-09-01",
    ) is False

    assert api.is_channel_sync_complete(
        "channel-1",
        "2026-03-01",
        "2026-11-01",
    ) is False

def test_is_channel_sync_complete_returns_false_without_state(tmp_path):
    client = MagicMock()
    db = YouTubeDB(tmp_path / "youtube.db")

    db.insert_channel(
        "channel-1",
        "Test Channel",
    )

    api = YouTubeAPI(
        client=client,
        db=db,
    )

    assert api.is_channel_sync_complete(
        "channel-1",
        "2026-03-01",
        "2026-09-01",
    ) is False

def test_sync_channel_videos(tmp_path):
    client = MagicMock()
    db = YouTubeDB(tmp_path / "youtube.db")

    db.insert_channel(
        "channel-1",
        "Test Channel",
    )

    api = YouTubeAPI(
        client=client,
        db=db,
    )

    client.call.side_effect = [
        # channels.list
        {
            "items": [
                {
                    "id": "channel-1",
                    "snippet": {
                        "title": "Test Channel",
                    },
                    "contentDetails": {
                        "relatedPlaylists": {
                            "uploads": "playlist-1",
                        },
                    },
                }
            ]
        },
        # playlistItems.list
        {
            "items": [
                {
                    "snippet": {
                        "resourceId": {
                            "videoId": "video-2",
                        },
                        "title": "Video 2",
                        "channelId": "channel-1",
                        "videoOwnerChannelId": "channel-1",
                    },
                    "contentDetails": {
                        "videoPublishedAt": "2026-09-01T00:00:00Z",
                    },
                },
                {
                    "snippet": {
                        "resourceId": {
                            "videoId": "video-1",
                        },
                        "title": "Video 1",
                        "channelId": "channel-1",
                        "videoOwnerChannelId": "channel-1",
                    },
                    "contentDetails": {
                        "videoPublishedAt": "2026-08-01T00:00:00Z",
                    },
                },
            ]
        },
    ]

    result = api.sync_channel_videos(
        channel_id="channel-1",
        start_date="2026-08-01",
        end_date="2026-10-01",
    )

    assert result is True

    video_1 = db.get_video_by_id("video-1")
    video_2 = db.get_video_by_id("video-2")

    assert video_1[0] == "video-1"
    assert video_1[1] == "Video 1"

    assert video_2[0] == "video-2"
    assert video_2[1] == "Video 2"

    state = db.get_channel_sync_state("channel-1")

    assert state == (
        "channel-1",
        "playlist-1",
        "2026-08-01T00:00:00Z",
        "2026-10-01T00:00:00Z",
    )

def test_sync_channel_videos_skips_api_when_already_synced(tmp_path):
    client = MagicMock()
    db = YouTubeDB(tmp_path / "youtube.db")

    db.insert_channel(
        "channel-1",
        "Test Channel",
    )

    db.set_channel_sync_state(
        "channel-1",
        uploads_playlist_id="playlist-1",
        oldest_synced_at="2026-08-01T00:00:00Z",
        newest_synced_at="2026-10-01T00:00:00Z",
    )

    api = YouTubeAPI(
        client=client,
        db=db,
    )

    result = api.sync_channel_videos(
        channel_id="channel-1",
        start_date="2026-08-01",
        end_date="2026-10-01",
    )

    assert result is True
    client.call.assert_not_called()

def test_get_live_streaming_video_ids_returns_live_video_ids(tmp_path):
    api = create_api(tmp_path)

    insert_channel(api.db)

    insert_video(api.db, video_id="video1")
    insert_video(api.db, video_id="video2")
    insert_video(api.db, video_id="video3")

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

def test_get_live_streaming_video_ids_batches_51_ids(tmp_path):
    api = create_api(tmp_path)

    insert_channel(api.db)

    video_ids = [f"video{i}" for i in range(51)]

    for video_id in video_ids:
        insert_video(
            api.db,
            video_id=video_id,
        )

    api.client.call.return_value = {"items": []}

    result = api.get_live_streaming_video_ids(video_ids)

    assert result == set()
    assert api.client.call.call_count == 2

    first_ids = api.client.call.call_args_list[0].kwargs["id"].split(",")
    second_ids = api.client.call.call_args_list[1].kwargs["id"].split(",")

    assert len(first_ids) == 50
    assert len(second_ids) == 1

def test_get_live_streaming_video_ids_saves_live_state(tmp_path):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2025-07-01T00:00:00Z",
                },
            },
        ]
    }

    result = api.get_live_streaming_video_ids(
        ["video1"]
    )

    assert result == {"video1"}

    state = api.db.get_video_live_state("video1")

    assert state["video_id"] == "video1"
    assert state["is_live"] is True
    assert state["checked_at"]

def test_get_live_streaming_video_ids_uses_cached_state(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2025-07-01T00:00:00Z",
                },
            },
        ]
    }

    first_result = api.get_live_streaming_video_ids(
        ["video1"]
    )

    assert first_result == {"video1"}
    api.client.call.assert_called_once()

    api.client.call.reset_mock()

    second_result = api.get_live_streaming_video_ids(
        ["video1"]
    )

    assert second_result == {"video1"}
    api.client.call.assert_not_called()

def test_is_live_state_cache_valid_within_ttl(tmp_path):
    api = create_api(tmp_path)

    state = {
        "video_id": "video1",
        "is_live": True,
        "checked_at": "2026-10-03T10:00:00Z",
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        59,
        tzinfo=timezone.utc,
    )

    assert api.is_live_state_cache_valid(
        state,
        now=now,
    ) is True

def test_is_live_state_cache_invalid_after_ttl(tmp_path):
    api = create_api(tmp_path)

    state = {
        "video_id": "video1",
        "is_live": True,
        "checked_at": "2026-10-03T10:00:00Z",
    }

    now = datetime(
        2026,
        10,
        3,
        13,
        0,
        tzinfo=timezone.utc,
    )

    assert api.is_live_state_cache_valid(
        state,
        now=now,
    ) is False

def test_is_live_state_cache_invalid_when_state_is_none(tmp_path):
    api = create_api(tmp_path)

    assert api.is_live_state_cache_valid(None) is False

def test_get_live_streaming_video_ids_refreshes_expired_cache(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    # 3時間以上前のキャッシュを用意する
    api.db.set_video_live_state(
        "video1",
        False,
        "2026-10-03T09:00:00Z",
    )

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
        ]
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1"],
        now=now,
    )

    assert result == {"video1"}
    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="liveStreamingDetails",
        id="video1",
    )

def test_get_live_streaming_video_ids_uses_valid_cached_state(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.db.set_video_live_state(
        "video1",
        True,
        "2026-10-03T09:00:00Z",
    )

    now = datetime(
        2026,
        10,
        3,
        11,
        59,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1"],
        now=now,
    )

    assert result == {"video1"}
    api.client.call.assert_not_called()

def test_get_live_streaming_video_ids_uses_cached_not_live_state(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.db.set_video_live_state(
        "video1",
        False,
        "2026-10-03T09:00:00Z",
    )

    now = datetime(
        2026,
        10,
        3,
        11,
        59,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1"],
        now=now,
    )

    assert result == set()
    api.client.call.assert_not_called()

def test_get_live_streaming_video_ids_updates_expired_cache(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.db.set_video_live_state(
        "video1",
        False,
        "2026-10-03T09:00:00Z",
    )

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
        ]
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1"],
        now=now,
    )

    assert result == {"video1"}

    state = api.db.get_video_live_state("video1")

    assert state["video_id"] == "video1"
    assert state["is_live"] is True
    assert state["checked_at"] == "2026-10-03T12:00:00Z"

def test_get_live_streaming_video_ids_uses_cache_and_api(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)

    for video_id in [
        "video1",
        "video2",
        "video3",
        "video4",
    ]:
        insert_video(
            api.db,
            video_id=video_id,
        )

    # 有効なキャッシュ
    api.db.set_video_live_state(
        "video1",
        True,
        "2026-10-03T10:00:00Z",
    )

    api.db.set_video_live_state(
        "video2",
        False,
        "2026-10-03T10:00:00Z",
    )

    # video4 は期限切れ
    api.db.set_video_live_state(
        "video4",
        False,
        "2026-10-03T08:00:00Z",
    )

    api.client.call.return_value = {
        "items": [
            {
                "id": "video3",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
            {
                "id": "video4",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
        ]
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        [
            "video1",
            "video2",
            "video3",
            "video4",
        ],
        now=now,
    )

    assert result == {
        "video1",
        "video3",
        "video4",
    }

    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="liveStreamingDetails",
        id="video3,video4",
    )

# ----------------------------------------------------------------------
# Live streaming cache
# ----------------------------------------------------------------------


def test_get_live_streaming_video_ids_returns_live_video_ids(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)

    insert_video(api.db, video_id="video1")
    insert_video(api.db, video_id="video2")
    insert_video(api.db, video_id="video3")

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


def test_get_live_streaming_video_ids_uses_valid_live_cache(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.db.set_video_live_state(
        "video1",
        True,
        "2026-10-03T09:00:00Z",
    )

    now = datetime(
        2026,
        10,
        3,
        11,
        59,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1"],
        now=now,
    )

    assert result == {"video1"}
    api.client.call.assert_not_called()


def test_get_live_streaming_video_ids_uses_valid_not_live_cache(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.db.set_video_live_state(
        "video1",
        False,
        "2026-10-03T09:00:00Z",
    )

    now = datetime(
        2026,
        10,
        3,
        11,
        59,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1"],
        now=now,
    )

    assert result == set()
    api.client.call.assert_not_called()


def test_get_live_streaming_video_ids_refreshes_expired_cache(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.db.set_video_live_state(
        "video1",
        False,
        "2026-10-03T09:00:00Z",
    )

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
        ]
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1"],
        now=now,
    )

    assert result == {"video1"}

    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="liveStreamingDetails",
        id="video1",
    )


def test_get_live_streaming_video_ids_updates_expired_cache(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.db.set_video_live_state(
        "video1",
        False,
        "2026-10-03T09:00:00Z",
    )

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
        ]
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1"],
        now=now,
    )

    assert result == {"video1"}

    state = api.db.get_video_live_state("video1")

    assert state == {
        "video_id": "video1",
        "is_live": True,
        "checked_at": "2026-10-03T12:00:00Z",
    }


def test_get_live_streaming_video_ids_uses_cache_and_api(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)

    for video_id in [
        "video1",
        "video2",
        "video3",
        "video4",
    ]:
        insert_video(
            api.db,
            video_id=video_id,
        )

    # 有効なキャッシュ
    api.db.set_video_live_state(
        "video1",
        True,
        "2026-10-03T10:00:00Z",
    )

    api.db.set_video_live_state(
        "video2",
        False,
        "2026-10-03T10:00:00Z",
    )

    # video4 はTTL切れ
    api.db.set_video_live_state(
        "video4",
        False,
        "2026-10-03T08:00:00Z",
    )

    # video3 はキャッシュなし
    api.client.call.return_value = {
        "items": [
            {
                "id": "video3",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
            {
                "id": "video4",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
        ]
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    state = api.db.get_video_live_state("video1")

    print("STATE:", state)
    print(
        "CACHE VALID:",
        api.is_live_state_cache_valid(
            state,
            now=now,
        ),
    )

    result = api.get_live_streaming_video_ids(
        ["video1", "video2", "video3", "video4"],
        now=now,
    )

    assert result == {
        "video1",
        "video3",
        "video4",
    }

    api.client.call.assert_called_once_with(
        "videos",
        "list",
        part="liveStreamingDetails",
        id="video3,video4",
    )


def test_get_live_streaming_video_ids_batches_51_ids(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)

    video_ids = [
        f"video{i}"
        for i in range(51)
    ]

    for video_id in video_ids:
        insert_video(
            api.db,
            video_id=video_id,
        )

    api.client.call.return_value = {
        "items": []
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        video_ids,
        now=now,
    )

    assert result == set()
    assert api.client.call.call_count == 2

    first_ids = (
        api.client.call.call_args_list[0]
        .kwargs["id"]
        .split(",")
    )

    second_ids = (
        api.client.call.call_args_list[1]
        .kwargs["id"]
        .split(",")
    )

    assert len(first_ids) == 50
    assert len(second_ids) == 1


def test_get_live_streaming_video_ids_returns_empty_for_empty_input(
    tmp_path,
):
    api = create_api(tmp_path)

    result = api.get_live_streaming_video_ids([])

    assert result == set()
    api.client.call.assert_not_called()


def test_get_live_streaming_video_ids_caches_missing_api_items(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")
    insert_video(api.db, video_id="video2")

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
        ]
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1", "video2"],
        now=now,
    )

    assert result == {"video1"}

    state = api.db.get_video_live_state("video2")

    assert state == {
        "video_id": "video2",
        "is_live": False,
        "checked_at": "2026-10-03T12:00:00Z",
    }


def test_get_live_streaming_video_ids_uses_cached_state_on_second_call(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
        ]
    }

    first_now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    first_result = api.get_live_streaming_video_ids(
        ["video1"],
        now=first_now,
    )

    assert first_result == {"video1"}
    api.client.call.assert_called_once()

    api.client.call.reset_mock()

    second_now = datetime(
        2026,
        10,
        3,
        14,
        59,
        tzinfo=timezone.utc,
    )

    second_result = api.get_live_streaming_video_ids(
        ["video1"],
        now=second_now,
    )

    assert second_result == {"video1"}
    api.client.call.assert_not_called()


def test_get_live_streaming_video_ids_refreshes_cache_at_exact_ttl(
    tmp_path,
):
    api = create_api(tmp_path)

    insert_channel(api.db)
    insert_video(api.db, video_id="video1")

    api.db.set_video_live_state(
        "video1",
        False,
        "2026-10-03T09:00:00Z",
    )

    api.client.call.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2026-10-03T12:00:00Z",
                },
            },
        ]
    }

    now = datetime(
        2026,
        10,
        3,
        12,
        0,
        tzinfo=timezone.utc,
    )

    result = api.get_live_streaming_video_ids(
        ["video1"],
        now=now,
    )

    assert result == {"video1"}
    api.client.call.assert_called_once()
