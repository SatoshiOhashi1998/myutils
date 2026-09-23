from datetime import datetime
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


# ----------------------------------------------------------------------
# Channel cache
# ----------------------------------------------------------------------


def test_get_channel_with_cache_returns_cached_channel(tmp_path):
    """DBにチャンネルが存在する場合、そのチャンネルを返す。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.call_api = MagicMock()

    result = api.get_channel_with_cache("channel1")

    assert result == (
        "channel1",
        "テストチャンネル",
        None,
    )

    api.call_api.assert_not_called()


def test_get_channel_with_cache_fetches_from_api(tmp_path):
    """DBにチャンネルがない場合、APIから取得してDBへ保存する。"""
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [
                {
                    "snippet": {
                        "title": "APIチャンネル",
                    }
                }
            ]
        }
    )

    result = api.get_channel_with_cache("channel1")

    assert result == (
        "channel1",
        "APIチャンネル",
    )

    api.call_api.assert_called_once_with(
        "channels",
        "list",
        part="snippet",
        id="channel1",
    )

    assert api.db.get_channel_by_id("channel1") == (
        "channel1",
        "APIチャンネル",
    )


def test_get_channel_with_cache_returns_none_when_channel_not_found(
    tmp_path,
):
    """APIにチャンネルが存在しない場合、Noneを返す。"""
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [],
        }
    )

    result = api.get_channel_with_cache("channel1")

    assert result is None

    api.call_api.assert_called_once_with(
        "channels",
        "list",
        part="snippet",
        id="channel1",
    )


# ----------------------------------------------------------------------
# fetch_and_save_videos_from_channel
# ----------------------------------------------------------------------


def test_fetch_and_save_videos_from_channel(tmp_path):
    """チャンネルの動画をAPIから取得してDBへ保存する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    api.youtube.search.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": {
                    "videoId": "video1",
                },
                "snippet": {
                    "title": "動画1",
                    "publishedAt": "2025-07-01T00:00:00Z",
                    "thumbnails": {
                        "default": {
                            "url": "default1.jpg",
                        },
                        "medium": {
                            "url": "medium1.jpg",
                        },
                        "high": {
                            "url": "high1.jpg",
                        },
                    },
                },
            },
            {
                "id": {
                    "videoId": "video2",
                },
                "snippet": {
                    "title": "動画2",
                    "publishedAt": "2025-07-02T00:00:00Z",
                    "thumbnails": {
                        "default": {
                            "url": "default2.jpg",
                        },
                        "medium": {
                            "url": "medium2.jpg",
                        },
                        "high": {
                            "url": "high2.jpg",
                        },
                    },
                },
            },
        ]
    }

    api.fetch_and_save_videos_from_channel(
        "channel1",
    )

    video1 = api.db.get_video_by_id("video1")
    video2 = api.db.get_video_by_id("video2")

    assert video1 is not None
    assert video1[1] == "動画1"
    assert video1[2] == "channel1"
    assert video1[3] == "2025-07-01T00:00:00Z"
    assert video1[4] is None
    assert video1[5] == "default1.jpg"
    assert video1[6] == "medium1.jpg"
    assert video1[7] == "high1.jpg"

    assert video2 is not None
    assert video2[1] == "動画2"

    api.get_channel_with_cache.assert_called_once_with(
        "channel1",
    )

    api.youtube.search.return_value.list.assert_called_once_with(
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
    """チャンネルが存在しない場合、動画取得を行わない。"""
    api = create_api(tmp_path)

    api.get_channel_with_cache = MagicMock(
        return_value=None,
    )

    api.fetch_and_save_videos_from_channel(
        "channel1",
    )

    api.get_channel_with_cache.assert_called_once_with(
        "channel1",
    )

    api.youtube.search.return_value.list.assert_not_called()


def test_fetch_and_save_videos_from_channel_converts_datetime_to_utc_z(
    tmp_path,
):
    """datetimeをYouTube API用のUTC文字列へ変換する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    api.youtube.search.return_value.list.return_value.execute.return_value = {
        "items": [],
    }

    published_after = datetime(2025, 7, 1, 12, 30, 0)
    published_before = datetime(2025, 7, 2, 12, 30, 0)

    api.fetch_and_save_videos_from_channel(
        "channel1",
        published_after=published_after,
        published_before=published_before,
    )

    api.youtube.search.return_value.list.assert_called_once_with(
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
    """nextPageTokenがある場合、複数ページを取得する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    execute = api.youtube.search.return_value.list.return_value.execute

    execute.side_effect = [
        {
            "items": [
                {
                    "id": {
                        "videoId": "video1",
                    },
                    "snippet": {
                        "title": "動画1",
                        "publishedAt": "2025-07-01T00:00:00Z",
                        "thumbnails": {},
                    },
                },
            ],
            "nextPageToken": "page2",
        },
        {
            "items": [
                {
                    "id": {
                        "videoId": "video2",
                    },
                    "snippet": {
                        "title": "動画2",
                        "publishedAt": "2025-07-02T00:00:00Z",
                        "thumbnails": {},
                    },
                },
            ],
        },
    ]

    api.fetch_and_save_videos_from_channel(
        "channel1",
    )

    assert api.db.get_video_by_id("video1") is not None
    assert api.db.get_video_by_id("video2") is not None

    assert api.youtube.search.return_value.list.call_count == 2

    calls = api.youtube.search.return_value.list.call_args_list

    assert calls[0].kwargs["pageToken"] is None
    assert calls[1].kwargs["pageToken"] == "page2"


def test_fetch_and_save_videos_from_channel_gets_duration(
    tmp_path,
):
    """get_duration=Trueの場合、動画詳細を取得してdurationを更新する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.get_channel_with_cache = MagicMock(
        return_value=("channel1", "テストチャンネル")
    )

    api.youtube.search.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": {
                    "videoId": "video1",
                },
                "snippet": {
                    "title": "動画1",
                    "publishedAt": "2025-07-01T00:00:00Z",
                    "thumbnails": {},
                },
            },
        ]
    }

    api.fetch_and_update_video_details = MagicMock()

    api.fetch_and_save_videos_from_channel(
        "channel1",
        get_duration=True,
    )

    api.fetch_and_update_video_details.assert_called_once_with(
        ["video1"],
    )


def test_fetch_and_update_video_details_updates_duration(tmp_path):
    """動画詳細APIからdurationを取得してDBを更新する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.db.insert_video(
        {
            "video_id": "video1",
            "title": "テスト動画",
            "channel_id": "channel1",
            "published_at": "2025-07-01T00:00:00Z",
            "duration": None,
        }
    )

    api.youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "video1",
                "contentDetails": {
                    "duration": "PT10M",
                },
            },
        ]
    }

    api.fetch_and_update_video_details(
        ["video1"],
    )

    result = api.db.get_video_by_id("video1")

    assert result[4] == 600

    api.youtube.videos.return_value.list.assert_called_once_with(
        part="contentDetails",
        id="video1",
    )


def test_fetch_and_update_video_details_processes_batches_of_50(
    tmp_path,
):
    """動画IDが50件を超える場合、50件ずつAPIへ送る。"""
    api = create_api(tmp_path)

    video_ids = [
        f"video{i}"
        for i in range(51)
    ]

    api.youtube.videos.return_value.list.return_value.execute.side_effect = [
        {
            "items": [],
        },
        {
            "items": [],
        },
    ]

    api.fetch_and_update_video_details(video_ids)

    assert api.youtube.videos.return_value.list.call_count == 2

    calls = api.youtube.videos.return_value.list.call_args_list

    assert len(calls[0].kwargs["id"].split(",")) == 50
    assert len(calls[1].kwargs["id"].split(",")) == 1


# ----------------------------------------------------------------------
# get_channel_videos_with_cache
# ----------------------------------------------------------------------


def test_get_channel_videos_with_cache_returns_cached_videos(
    tmp_path,
):
    """指定期間の動画がDBに存在する場合、APIを呼ばずに返す。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.db.insert_video(
        {
            "video_id": "video1",
            "title": "キャッシュ動画",
            "channel_id": "channel1",
            "published_at": "2025-07-01T12:00:00Z",
            "duration": 300,
        }
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


def test_get_channel_videos_with_cache_fetches_when_cache_is_empty(
    tmp_path,
):
    """DBに動画がない場合、APIから取得して再検索する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.fetch_and_save_videos_from_channel = MagicMock()

    def save_video(*args, **kwargs):
        api.db.insert_video(
            {
                "video_id": "video1",
                "title": "API動画",
                "channel_id": "channel1",
                "published_at": "2025-07-01T12:00:00Z",
                "duration": None,
            }
        )

    api.fetch_and_save_videos_from_channel.side_effect = save_video

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


def test_get_channel_videos_with_cache_adds_z_to_datetime_string(
    tmp_path,
):
    """Zなしの文字列日時にはZを追加する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

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


def test_search_videos(tmp_path):
    """search_videosが正しいパラメータでAPIを呼び出す。"""
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [],
        }
    )

    published_after = datetime(2025, 7, 1, 12, 30, 0)
    published_before = datetime(2025, 7, 2, 12, 30, 0)

    result = api.search_videos(
        query="Python",
        channel_id="channel1",
        published_after=published_after,
        published_before=published_before,
        event_type="completed",
        max_results=10,
        order="date",
        page_token="page2",
    )

    assert result == {
        "items": [],
    }

    api.call_api.assert_called_once_with(
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


def test_search_videos_omits_optional_parameters(tmp_path):
    """search_videosは指定されていないオプションをAPIへ渡さない。"""
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [],
        }
    )

    api.search_videos()

    api.call_api.assert_called_once_with(
        "search",
        "list",
        part="snippet",
        type="video",
        maxResults=50,
        order="date",
    )


def test_get_video_details_returns_first_item(tmp_path):
    """get_video_detailsは最初の動画を返す。"""
    api = create_api(tmp_path)

    item = {
        "id": "video1",
        "snippet": {
            "title": "テスト動画",
        },
    }

    api.call_api = MagicMock(
        return_value={
            "items": [
                item,
                {
                    "id": "video2",
                },
            ],
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
    """get_video_detailsは動画が存在しない場合Noneを返す。"""
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [],
        }
    )

    result = api.get_video_details("video1")

    assert result is None


def test_get_playlist_items(tmp_path):
    """プレイリスト動画取得APIを正しい引数で呼び出す。"""
    api = create_api(tmp_path)

    api.call_api = MagicMock(
        return_value={
            "items": [],
        }
    )

    result = api.get_playlist_items(
        "playlist1",
        max_results=20,
        page_token="page2",
    )

    assert result == {
        "items": [],
    }

    api.call_api.assert_called_once_with(
        "playlistItems",
        "list",
        part="snippet",
        playlistId="playlist1",
        maxResults=20,
        pageToken="page2",
    )


# ----------------------------------------------------------------------
# Live streaming
# ----------------------------------------------------------------------


def test_get_live_streaming_video_ids(tmp_path):
    """liveStreamingDetailsを持つ動画だけを返す。"""
    api = create_api(tmp_path)

    api.youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": [
            {
                "id": "video1",
                "liveStreamingDetails": {
                    "actualStartTime": "2025-07-01T00:00:00Z",
                },
            },
            {
                "id": "video2",
            },
            {
                "id": "video3",
                "liveStreamingDetails": {
                    "scheduledStartTime": "2025-07-02T00:00:00Z",
                },
            },
        ]
    }

    result = api.get_live_streaming_video_ids(
        ["video1", "video2", "video3"],
    )

    assert result == {
        "video1",
        "video3",
    }

    api.youtube.videos.return_value.list.assert_called_once_with(
        part="liveStreamingDetails",
        id="video1,video2,video3",
    )


def test_get_live_streaming_video_ids_processes_batches_of_50(
    tmp_path,
):
    """動画IDが50件を超える場合、50件ずつAPIへ送る。"""
    api = create_api(tmp_path)

    video_ids = [
        f"video{i}"
        for i in range(51)
    ]

    api.youtube.videos.return_value.list.return_value.execute.side_effect = [
        {
            "items": [],
        },
        {
            "items": [],
        },
    ]

    result = api.get_live_streaming_video_ids(video_ids)

    assert result == set()

    assert api.youtube.videos.return_value.list.call_count == 2

    calls = api.youtube.videos.return_value.list.call_args_list

    assert len(calls[0].kwargs["id"].split(",")) == 50
    assert len(calls[1].kwargs["id"].split(",")) == 1


# ----------------------------------------------------------------------
# get_video_details_with_cache
# ----------------------------------------------------------------------


def test_get_video_details_with_cache_saves_video_to_database(
    tmp_path,
):
    """動画詳細をAPIから取得してチャンネルと動画をDBへ保存する。"""
    api = create_api(tmp_path)

    item = {
        "id": "video1",
        "snippet": {
            "title": "テスト動画",
            "channelId": "channel1",
            "channelTitle": "テストチャンネル",
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

    api.get_video_details = MagicMock(
        return_value=item,
    )

    result = api.get_video_details_with_cache(
        "video1",
    )

    assert result == item

    assert api.db.get_channel_by_id("channel1") == (
        "channel1",
        "テストチャンネル",
    )

    video = api.db.get_video_by_id("video1")

    assert video is not None
    assert video[0] == "video1"
    assert video[1] == "テスト動画"
    assert video[2] == "channel1"
    assert video[3] == "2025-07-01T00:00:00Z"
    assert video[4] == 300
    assert video[5] == "default.jpg"
    assert video[6] == "medium.jpg"
    assert video[7] == "high.jpg"

    api.get_video_details.assert_called_once_with(
        "video1",
        part="snippet,contentDetails",
    )


def test_get_video_details_with_cache_returns_none_when_video_not_found(
    tmp_path,
):
    """動画が存在しない場合、Noneを返す。"""
    api = create_api(tmp_path)

    api.get_video_details = MagicMock(
        return_value=None,
    )

    result = api.get_video_details_with_cache(
        "video1",
    )

    assert result is None

    api.get_video_details.assert_called_once_with(
        "video1",
        part="snippet,contentDetails",
    )


def test_get_video_details_with_cache_returns_item_without_channel_info(
    tmp_path,
):
    """channel_idまたはchannel_titleがない場合、DB保存せずitemを返す。"""
    api = create_api(tmp_path)

    item = {
        "id": "video1",
        "snippet": {
            "title": "テスト動画",
        },
    }

    api.get_video_details = MagicMock(
        return_value=item,
    )

    result = api.get_video_details_with_cache(
        "video1",
    )

    assert result == item

    assert api.db.get_video_by_id("video1") is None


def test_get_video_details_with_cache_preserves_existing_duration(
    tmp_path,
):
    """API側のdurationがない場合、既存DBのdurationを維持する。"""
    api = create_api(tmp_path)

    api.db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    api.db.insert_video(
        {
            "video_id": "video1",
            "title": "旧タイトル",
            "channel_id": "channel1",
            "published_at": "2025-07-01T00:00:00Z",
            "duration": 300,
        }
    )

    item = {
        "id": "video1",
        "snippet": {
            "title": "新タイトル",
            "channelId": "channel1",
            "channelTitle": "テストチャンネル",
            "publishedAt": "2025-07-02T00:00:00Z",
            "thumbnails": {},
        },
    }

    api.get_video_details = MagicMock(
        return_value=item,
    )

    api.get_video_details_with_cache(
        "video1",
    )

    video = api.db.get_video_by_id("video1")

    assert video[1] == "新タイトル"
    assert video[3] == "2025-07-02T00:00:00Z"

    # API側にdurationがないので既存値を維持
    assert video[4] == 300
