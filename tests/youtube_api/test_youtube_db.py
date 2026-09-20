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
