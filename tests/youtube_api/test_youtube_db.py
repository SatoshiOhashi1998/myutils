from myutils.youtube_api.youtube_db import YouTubeDB


def test_database_is_initialized(tmp_path):
    db_path = tmp_path / "test.db"

    db = YouTubeDB(db_path)

    with db._connect() as conn:
        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    table_names = {row[0] for row in tables}

    assert "channels" in table_names
    assert "videos" in table_names


def test_insert_and_get_video(tmp_path):
    db_path = tmp_path / "test.db"
    db = YouTubeDB(db_path)

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    video = {
        "video_id": "video1",
        "title": "テスト動画",
        "channel_id": "channel1",
        "published_at": "2025-07-01T00:00:00Z",
        "duration": 300,
        "thumbnail_default": "default.jpg",
        "thumbnail_medium": "medium.jpg",
        "thumbnail_high": "high.jpg",
    }

    db.insert_video(video)

    result = db.get_video_by_id("video1")

    assert result is not None
    assert result[0] == "video1"
    assert result[1] == "テスト動画"
    assert result[2] == "channel1"
    assert result[4] == 300


def test_insert_video_does_not_duplicate(tmp_path):
    db_path = tmp_path / "test.db"
    db = YouTubeDB(db_path)

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    video = {
        "video_id": "video1",
        "title": "テスト動画",
        "channel_id": "channel1",
        "published_at": "2025-07-01T00:00:00Z",
        "duration": 300,
    }

    db.insert_video(video)
    db.insert_video(video)

    with db._connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE video_id = ?",
            ("video1",),
        ).fetchone()[0]

    assert count == 1


def test_update_video_duration(tmp_path):
    db_path = tmp_path / "test.db"
    db = YouTubeDB(db_path)

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    video = {
        "video_id": "video1",
        "title": "テスト動画",
        "channel_id": "channel1",
        "duration": None,
    }

    db.insert_video(video)

    db.update_video_duration("video1", 600)

    result = db.get_video_by_id("video1")

    assert result[4] == 600


def test_search_channels_by_title(tmp_path):
    db_path = tmp_path / "test.db"
    db = YouTubeDB(db_path)

    db.insert_channel("channel1", "Pythonチャンネル")
    db.insert_channel("channel2", "料理チャンネル")
    db.insert_channel("channel3", "Python入門")

    results = db.search_channels_by_title("Python")

    assert len(results) == 2

    channel_ids = {row[0] for row in results}

    assert channel_ids == {"channel1", "channel3"}


# ----------------------------------------------------------------------
# Channel
# ----------------------------------------------------------------------


def test_insert_and_get_channel(tmp_path):
    """チャンネルを登録してIDから取得できる。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    result = db.get_channel_by_id("channel1")

    assert result == (
        "channel1",
        "テストチャンネル",
    )


def test_get_channel_by_id_returns_none_when_not_found(tmp_path):
    """存在しないチャンネルを取得するとNoneを返す。"""
    db = YouTubeDB(tmp_path / "test.db")

    result = db.get_channel_by_id("channel1")

    assert result is None


def test_insert_channel_does_not_update_existing_channel(
    tmp_path,
):
    """insert_channelは既存チャンネルを更新しない。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "旧チャンネル名",
    )

    db.insert_channel(
        "channel1",
        "新チャンネル名",
    )

    result = db.get_channel_by_id("channel1")

    assert result == (
        "channel1",
        "旧チャンネル名",
    )


# ----------------------------------------------------------------------
# Video upsert
# ----------------------------------------------------------------------


def test_upsert_video_inserts_new_video(tmp_path):
    """upsert_videoは存在しない動画をINSERTする。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    db.upsert_video(
        {
            "video_id": "video1",
            "title": "テスト動画",
            "channel_id": "channel1",
            "published_at": "2025-07-01T00:00:00Z",
            "duration": 300,
        }
    )

    result = db.get_video_by_id("video1")

    assert result is not None
    assert result[0] == "video1"
    assert result[1] == "テスト動画"
    assert result[4] == 300


def test_upsert_video_updates_existing_video(tmp_path):
    """upsert_videoは既存動画をUPDATEする。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    db.insert_video(
        {
            "video_id": "video1",
            "title": "旧タイトル",
            "channel_id": "channel1",
            "published_at": "2025-07-01T00:00:00Z",
            "duration": 300,
        }
    )

    db.upsert_video(
        {
            "video_id": "video1",
            "title": "新タイトル",
            "channel_id": "channel1",
            "published_at": "2025-07-02T00:00:00Z",
            "duration": 600,
        }
    )

    result = db.get_video_by_id("video1")

    assert result is not None
    assert result[1] == "新タイトル"
    assert result[2] == "channel1"
    assert result[3] == "2025-07-02T00:00:00Z"
    assert result[4] == 600


def test_upsert_video_preserves_existing_duration_when_new_duration_is_none(
    tmp_path,
):
    """upsert時のdurationがNoneなら既存durationを維持する。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    db.insert_video(
        {
            "video_id": "video1",
            "title": "旧タイトル",
            "channel_id": "channel1",
            "published_at": "2025-07-01T00:00:00Z",
            "duration": 300,
        }
    )

    db.upsert_video(
        {
            "video_id": "video1",
            "title": "新タイトル",
            "channel_id": "channel1",
            "published_at": "2025-07-02T00:00:00Z",
            "duration": None,
        }
    )

    result = db.get_video_by_id("video1")

    assert result[1] == "新タイトル"
    assert result[4] == 300


# ----------------------------------------------------------------------
# Videos by channel and date
# ----------------------------------------------------------------------


def test_get_videos_by_channel_and_date(tmp_path):
    """指定チャンネル・期間の動画を取得する。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    db.insert_video(
        {
            "video_id": "video1",
            "title": "動画1",
            "channel_id": "channel1",
            "published_at": "2025-07-01T00:00:00Z",
        }
    )

    db.insert_video(
        {
            "video_id": "video2",
            "title": "動画2",
            "channel_id": "channel1",
            "published_at": "2025-07-01T12:00:00Z",
        }
    )

    db.insert_video(
        {
            "video_id": "video3",
            "title": "動画3",
            "channel_id": "channel1",
            "published_at": "2025-07-02T00:00:00Z",
        }
    )

    results = db.get_videos_by_channel_and_date(
        "channel1",
        "2025-07-01T00:00:00Z",
        "2025-07-02T00:00:00Z",
    )

    assert len(results) == 2

    assert [row[0] for row in results] == [
        "video2",
        "video1",
    ]


def test_get_videos_by_channel_and_date_excludes_end_date(
    tmp_path,
):
    """end_dateは含まれない。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    db.insert_video(
        {
            "video_id": "video1",
            "title": "動画1",
            "channel_id": "channel1",
            "published_at": "2025-07-02T00:00:00Z",
        }
    )

    results = db.get_videos_by_channel_and_date(
        "channel1",
        "2025-07-01T00:00:00Z",
        "2025-07-02T00:00:00Z",
    )

    assert results == []


def test_get_videos_by_channel_and_date_does_not_return_other_channel(
    tmp_path,
):
    """指定したchannel_id以外の動画は取得しない。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "チャンネル1",
    )

    db.insert_channel(
        "channel2",
        "チャンネル2",
    )

    db.insert_video(
        {
            "video_id": "video1",
            "title": "動画1",
            "channel_id": "channel1",
            "published_at": "2025-07-01T12:00:00Z",
        }
    )

    db.insert_video(
        {
            "video_id": "video2",
            "title": "動画2",
            "channel_id": "channel2",
            "published_at": "2025-07-01T12:00:00Z",
        }
    )

    results = db.get_videos_by_channel_and_date(
        "channel1",
        "2025-07-01T00:00:00Z",
        "2025-07-02T00:00:00Z",
    )

    assert len(results) == 1
    assert results[0][0] == "video1"


# ----------------------------------------------------------------------
# Channel tags
# ----------------------------------------------------------------------


def test_update_and_get_channel_tags(tmp_path):
    """チャンネルのタグを保存して取得できる。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    db.update_channel_tags(
        "channel1",
        [
            "VTuber",
            "ゲーム",
            "配信",
        ],
    )

    result = db.get_channel_tags("channel1")

    assert result == [
        "VTuber",
        "ゲーム",
        "配信",
    ]


def test_get_channel_tags_returns_empty_list_when_not_set(
    tmp_path,
):
    """タグ未設定の場合は空リストを返す。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    result = db.get_channel_tags("channel1")

    assert result == []


def test_get_channel_tags_returns_empty_list_when_channel_not_found(
    tmp_path,
):
    """存在しないチャンネルのタグ取得は空リストを返す。"""
    db = YouTubeDB(tmp_path / "test.db")

    result = db.get_channel_tags("channel1")

    assert result == []

def test_get_videos_by_channel_and_date_uses_end_exclusive_range(
    tmp_path,
):
    """動画検索の終了日時は範囲に含まれない。"""
    db = YouTubeDB(tmp_path / "test.db")

    db.insert_channel(
        "channel1",
        "テストチャンネル",
    )

    videos = [
        {
            "video_id": "video1",
            "title": "開始時刻ちょうど",
            "channel_id": "channel1",
            "published_at": "2025-07-01T00:00:00Z",
            "duration": None,
        },
        {
            "video_id": "video2",
            "title": "期間内",
            "channel_id": "channel1",
            "published_at": "2025-07-01T12:00:00Z",
            "duration": None,
        },
        {
            "video_id": "video3",
            "title": "終了時刻ちょうど",
            "channel_id": "channel1",
            "published_at": "2025-07-02T00:00:00Z",
            "duration": None,
        },
    ]

    for video in videos:
        db.insert_video(video)

    result = db.get_videos_by_channel_and_date(
        "channel1",
        "2025-07-01T00:00:00Z",
        "2025-07-02T00:00:00Z",
    )

    video_ids = [row[0] for row in result]

    assert video_ids == [
        "video2",
        "video1",
    ]
