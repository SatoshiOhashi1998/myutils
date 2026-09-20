from unittest.mock import MagicMock

from myutils.youtube_api.fetch_youtube_data import YouTubeAPI
from myutils.youtube_api.youtube_db import YouTubeDB


def create_api(tmp_path):
    return YouTubeAPI(
        youtube=MagicMock(),
        db=YouTubeDB(tmp_path / "youtube.db"),
    )

def test_get_video_with_cache_returns_cached_video(tmp_path):
    """DBにキャッシュが存在する場合、その動画を返す。"""
    api = create_api(tmp_path)

    # videos.channel_id は channels.channel_id を
    # 外部キーとして参照するため、先にチャンネルを登録する。
    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.db.insert_video(
        {
            "video_id": "video1",
            "title": "キャッシュ動画",
            "channel_id": "channel1",
            "published_at": "2025-07-01T00:00:00Z",
            "duration": 300,
            "thumbnail_default": "default.jpg",
            "thumbnail_medium": "medium.jpg",
            "thumbnail_high": "high.jpg",
        }
    )

    # キャッシュが存在する場合、APIは呼ばれない
    api.call_api = MagicMock()

    result = api.get_video_with_cache("video1")

    assert result is not None

    # SQLiteのSELECT結果はtuple
    assert result[0] == "video1"
    assert result[1] == "キャッシュ動画"
    assert result[2] == "channel1"
    assert result[3] == "2025-07-01T00:00:00Z"
    assert result[4] == 300
    assert result[5] == "default.jpg"
    assert result[6] == "medium.jpg"
    assert result[7] == "high.jpg"

    api.call_api.assert_not_called()


def test_get_video_with_cache_fetches_from_api(tmp_path):
    """DBにキャッシュがない場合、APIから取得してDBへ保存する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.call_api = MagicMock(
        return_value={
            "items": [
                {
                    "id": {
                        "videoId": "video1",
                    },
                    "snippet": {
                        "title": "テスト動画",
                        "channelId": "channel1",
                        "publishedAt": "2025-07-01T00:00:00Z",
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
                        "duration": "PT5M",
                    },
                }
            ]
        }
    )

    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    result = api.get_video_with_cache("video1")

    assert result is not None

    # APIから取得した場合はdictが返る
    assert result["video_id"] == "video1"
    assert result["title"] == "テスト動画"
    assert result["channel_id"] == "channel1"
    assert result["published_at"] == "2025-07-01T00:00:00Z"
    assert result["duration"] == 300
    assert result["thumbnail_default"] == "default.jpg"
    assert result["thumbnail_medium"] == "medium.jpg"
    assert result["thumbnail_high"] == "high.jpg"

    api.call_api.assert_called_once_with(
        "videos",
        "list",
        part="snippet,contentDetails",
        id="video1",
    )

    api.get_channel_with_cache.assert_called_once_with(
        "channel1",
    )

    # DBにも保存されたことを確認する
    cached = api.db.get_video_by_id("video1")

    assert cached is not None
    assert cached[0] == "video1"
    assert cached[1] == "テスト動画"
    assert cached[2] == "channel1"
    assert cached[4] == 300


def test_get_video_with_cache_returns_none_when_api_returns_no_items(
    tmp_path,
):
    """APIのレスポンスに動画が存在しない場合、Noneを返す。"""
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [],
        }
    )

    result = api.get_video_with_cache("video1")

    assert result is None

    api.call_api.assert_called_once_with(
        "videos",
        "list",
        part="snippet,contentDetails",
        id="video1",
    )


def test_get_video_with_cache_converts_duration_to_seconds(tmp_path):
    """ISO 8601形式のdurationを秒数へ変換する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.call_api = MagicMock(
        return_value={
            "items": [
                {
                    "id": {
                        "videoId": "video1",
                    },
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
            ]
        }
    )

    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    result = api.get_video_with_cache("video1")

    assert result is not None
    assert result["duration"] == 3723


def test_get_video_with_cache_handles_invalid_duration(tmp_path):
    """durationが不正な場合、durationをNoneにする。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.call_api = MagicMock(
        return_value={
            "items": [
                {
                    "id": {
                        "videoId": "video1",
                    },
                    "snippet": {
                        "title": "テスト動画",
                        "channelId": "channel1",
                        "publishedAt": "2025-07-01T00:00:00Z",
                        "thumbnails": {},
                    },
                    "contentDetails": {
                        "duration": "invalid",
                    },
                }
            ]
        }
    )

    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    result = api.get_video_with_cache("video1")

    assert result is not None
    assert result["duration"] is None
