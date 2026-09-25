from myutils.youtube_api.converters import (
    channel_from_api_item,
    parse_duration,
    video_data,
    video_from_api_item,
    video_from_search_item,
)


def test_parse_duration_converts_iso_duration():
    assert parse_duration("PT5M") == 300


def test_parse_duration_converts_hours_minutes_seconds():
    assert parse_duration("PT1H2M3S") == 3723


def test_parse_duration_returns_zero_for_zero_duration():
    assert parse_duration("PT0S") == 0


def test_parse_duration_returns_none_for_invalid_value():
    assert parse_duration("invalid") is None


def test_parse_duration_returns_none_for_empty_value():
    assert parse_duration("") is None


def test_video_data_builds_common_video_dict():
    result = video_data(
        video_id="video1",
        snippet={
            "title": "テスト動画",
            "channelId": "channel1",
            "publishedAt": "2025-07-01T00:00:00Z",
            "thumbnails": {
                "default": {"url": "default.jpg"},
                "medium": {"url": "medium.jpg"},
                "high": {"url": "high.jpg"},
            },
        },
        channel_id="channel1",
        duration=300,
    )

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


def test_video_data_uses_safe_defaults_for_missing_fields():
    result = video_data(
        video_id="video1",
        snippet={},
    )

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


def test_video_from_search_item_converts_item():
    item = {
        "id": {
            "kind": "youtube#video",
            "videoId": "video1",
        },
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
    }

    result = video_from_search_item(item, "channel1")

    assert result == {
        "video_id": "video1",
        "title": "テスト動画",
        "channel_id": "channel1",
        "published_at": "2025-07-01T00:00:00Z",
        "duration": None,
        "thumbnail_default": "default.jpg",
        "thumbnail_medium": "medium.jpg",
        "thumbnail_high": "high.jpg",
    }


def test_video_from_search_item_handles_missing_fields():
    result = video_from_search_item({}, "channel1")

    assert result == {
        "video_id": None,
        "title": "",
        "channel_id": "channel1",
        "published_at": None,
        "duration": None,
        "thumbnail_default": None,
        "thumbnail_medium": None,
        "thumbnail_high": None,
    }


def test_video_from_api_item_converts_duration():
    item = {
        "id": "video1",
        "snippet": {
            "title": "テスト動画",
            "channelId": "channel1",
            "publishedAt": "2025-07-01T00:00:00Z",
            "thumbnails": {},
        },
        "contentDetails": {
            "duration": "PT1H2M3S",
        },
    }

    result = video_from_api_item(item)

    assert result["video_id"] == "video1"
    assert result["channel_id"] == "channel1"
    assert result["duration"] == 3723
    assert result["thumbnail_default"] is None
    assert result["thumbnail_medium"] is None
    assert result["thumbnail_high"] is None


def test_video_from_api_item_handles_missing_duration():
    item = {
        "id": "video1",
        "snippet": {
            "title": "テスト動画",
            "channelId": "channel1",
        },
    }

    result = video_from_api_item(item)

    assert result["video_id"] == "video1"
    assert result["duration"] is None


def test_video_from_api_item_handles_invalid_duration():
    item = {
        "id": "video1",
        "snippet": {},
        "contentDetails": {
            "duration": "invalid",
        },
    }

    result = video_from_api_item(item)

    assert result["duration"] is None


def test_channel_from_api_item_converts_item():
    result = channel_from_api_item(
        {
            "id": "channel1",
            "snippet": {
                "title": "テストチャンネル",
            },
        }
    )

    assert result == {
        "channel_id": "channel1",
        "channel_title": "テストチャンネル",
    }


def test_channel_from_api_item_handles_missing_fields():
    result = channel_from_api_item({})

    assert result == {
        "channel_id": None,
        "channel_title": "",
    }
