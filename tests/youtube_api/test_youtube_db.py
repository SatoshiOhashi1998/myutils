import json
import sqlite3

import pytest

from myutils.youtube_api.youtube_db import YouTubeDB


# ============================================================
# Helpers
# ============================================================


def create_db(tmp_path):
    return YouTubeDB(tmp_path / "youtube.db")


def create_channel(db, channel_id="channel1", channel_title="Test Channel"):
    db.insert_channel(channel_id, channel_title)


def create_video(
    db,
    video_id="video1",
    title="Test Video",
    channel_id="channel1",
    published_at="2026-01-01T00:00:00Z",
    duration=None,
    thumbnail_default=None,
    thumbnail_medium=None,
    thumbnail_high=None,
):
    db.insert_video(
        {
            "video_id": video_id,
            "title": title,
            "channel_id": channel_id,
            "published_at": published_at,
            "duration": duration,
            "thumbnail_default": thumbnail_default,
            "thumbnail_medium": thumbnail_medium,
            "thumbnail_high": thumbnail_high,
        }
    )


# ============================================================
# Initialization
# ============================================================


def test_db_initialization_creates_tables(tmp_path):
    db = create_db(tmp_path)

    with db._connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert "channels" in tables
    assert "videos" in tables


def test_db_initialization_creates_tags_column(tmp_path):
    db = create_db(tmp_path)

    with db._connect() as conn:
        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(channels)"
            ).fetchall()
        }

    assert "tags" in columns


def test_db_initialization_creates_indexes(tmp_path):
    db = create_db(tmp_path)

    with db._connect() as conn:
        indexes = {
            row[1]
            for row in conn.execute(
                """
                SELECT type, name
                FROM sqlite_master
                WHERE type = 'index'
                """
            ).fetchall()
        }

    assert "idx_videos_channel_id" in indexes
    assert "idx_videos_published_at" in indexes


def test_db_enables_foreign_keys(tmp_path):
    db = create_db(tmp_path)

    with db._connect() as conn:
        foreign_keys = conn.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0]

    assert foreign_keys == 1


# ============================================================
# insert_video / get_video_by_id
# ============================================================


def test_insert_and_get_video(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    create_video(
        db,
        video_id="video1",
        title="Test Video",
        duration=120,
    )

    result = db.get_video_by_id("video1")

    assert result is not None
    assert result[0] == "video1"
    assert result[1] == "Test Video"
    assert result[2] == "channel1"
    assert result[4] == 120


def test_get_video_by_id_returns_none_when_not_found(tmp_path):
    db = create_db(tmp_path)

    result = db.get_video_by_id("unknown")

    assert result is None


def test_insert_video_does_not_duplicate(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    video = {
        "video_id": "video1",
        "title": "Original Title",
        "channel_id": "channel1",
        "published_at": "2026-01-01T00:00:00Z",
        "duration": 120,
    }

    db.insert_video(video)
    db.insert_video(
        {
            **video,
            "title": "Updated Title",
            "duration": 240,
        }
    )

    result = db.get_video_by_id("video1")

    assert result[1] == "Original Title"
    assert result[4] == 120


def test_insert_video_requires_existing_channel(tmp_path):
    db = create_db(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        create_video(
            db,
            channel_id="unknown-channel",
        )


def test_update_video_duration(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    create_video(
        db,
        duration=None,
    )

    db.update_video_duration("video1", 180)

    result = db.get_video_by_id("video1")

    assert result[4] == 180


def test_update_video_duration_does_nothing_for_unknown_video(tmp_path):
    db = create_db(tmp_path)

    db.update_video_duration("unknown", 180)

    assert db.get_video_by_id("unknown") is None


# ============================================================
# upsert_video
# ============================================================


def test_upsert_video_inserts_new_video(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    db.upsert_video(
        {
            "video_id": "video1",
            "title": "Test Video",
            "channel_id": "channel1",
            "published_at": "2026-01-01T00:00:00Z",
            "duration": 120,
        }
    )

    result = db.get_video_by_id("video1")

    assert result is not None
    assert result[0] == "video1"
    assert result[1] == "Test Video"
    assert result[2] == "channel1"
    assert result[4] == 120


def test_upsert_video_updates_existing_video(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    create_video(
        db,
        title="Old Title",
        published_at="2026-01-01T00:00:00Z",
        duration=120,
    )

    db.upsert_video(
        {
            "video_id": "video1",
            "title": "New Title",
            "channel_id": "channel1",
            "published_at": "2026-01-02T00:00:00Z",
            "duration": 240,
        }
    )

    result = db.get_video_by_id("video1")

    assert result[1] == "New Title"
    assert result[3] == "2026-01-02T00:00:00Z"
    assert result[4] == 240


def test_upsert_video_preserves_existing_duration_when_new_duration_is_none(
    tmp_path,
):
    db = create_db(tmp_path)
    create_channel(db)

    create_video(
        db,
        duration=120,
    )

    db.upsert_video(
        {
            "video_id": "video1",
            "title": "Updated Title",
            "channel_id": "channel1",
            "published_at": "2026-01-01T00:00:00Z",
            "duration": None,
        }
    )

    result = db.get_video_by_id("video1")

    assert result[1] == "Updated Title"
    assert result[4] == 120


def test_upsert_video_updates_thumbnails(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    create_video(
        db,
        thumbnail_default="old-default.jpg",
        thumbnail_medium="old-medium.jpg",
        thumbnail_high="old-high.jpg",
    )

    db.upsert_video(
        {
            "video_id": "video1",
            "title": "Updated Video",
            "channel_id": "channel1",
            "published_at": "2026-01-01T00:00:00Z",
            "duration": 120,
            "thumbnail_default": "new-default.jpg",
            "thumbnail_medium": "new-medium.jpg",
            "thumbnail_high": "new-high.jpg",
        }
    )

    result = db.get_video_by_id("video1")

    assert result[5] == "new-default.jpg"
    assert result[6] == "new-medium.jpg"
    assert result[7] == "new-high.jpg"


def test_upsert_video_requires_existing_channel(tmp_path):
    db = create_db(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        db.upsert_video(
            {
                "video_id": "video1",
                "title": "Test Video",
                "channel_id": "unknown-channel",
                "published_at": "2026-01-01T00:00:00Z",
                "duration": 120,
            }
        )


# ============================================================
# search_channels_by_title
# ============================================================


def test_search_channels_by_title(tmp_path):
    db = create_db(tmp_path)

    db.insert_channel("channel1", "Test Channel")
    db.insert_channel("channel2", "Another Channel")
    db.insert_channel("channel3", "Completely Different")

    result = db.search_channels_by_title("Channel")

    assert ("channel1", "Test Channel") in result
    assert ("channel2", "Another Channel") in result
    assert ("channel3", "Completely Different") not in result


def test_search_channels_by_title_returns_empty_when_no_match(tmp_path):
    db = create_db(tmp_path)

    db.insert_channel("channel1", "Test Channel")

    result = db.search_channels_by_title("Unknown")

    assert result == []


def test_search_channels_by_title_matches_partial_title(tmp_path):
    db = create_db(tmp_path)

    db.insert_channel("channel1", "Test Channel")
    db.insert_channel("channel2", "Another Channel")

    result = db.search_channels_by_title("Test")

    assert result == [("channel1", "Test Channel")]


# ============================================================
# insert_channel / get_channel_by_id
# ============================================================


def test_insert_and_get_channel(tmp_path):
    db = create_db(tmp_path)

    db.insert_channel("channel1", "Test Channel")

    result = db.get_channel_by_id("channel1")

    assert result == ("channel1", "Test Channel")


def test_get_channel_by_id_returns_none_when_not_found(tmp_path):
    db = create_db(tmp_path)

    result = db.get_channel_by_id("unknown")

    assert result is None


def test_insert_channel_does_not_update_existing_channel(tmp_path):
    db = create_db(tmp_path)

    db.insert_channel("channel1", "Original Title")
    db.insert_channel("channel1", "Updated Title")

    result = db.get_channel_by_id("channel1")

    assert result == ("channel1", "Original Title")


# ============================================================
# get_videos_by_channel_and_date
# ============================================================


def test_get_videos_by_channel_and_date_filters_channel_and_date(tmp_path):
    db = create_db(tmp_path)

    create_channel(db, "channel1", "Channel 1")
    create_channel(db, "channel2", "Channel 2")

    create_video(
        db,
        video_id="video1",
        title="Video 1",
        channel_id="channel1",
        published_at="2026-01-01T10:00:00Z",
    )
    create_video(
        db,
        video_id="video2",
        title="Video 2",
        channel_id="channel1",
        published_at="2026-01-02T10:00:00Z",
    )
    create_video(
        db,
        video_id="video3",
        title="Video 3",
        channel_id="channel1",
        published_at="2026-01-03T10:00:00Z",
    )
    create_video(
        db,
        video_id="video4",
        title="Video 4",
        channel_id="channel2",
        published_at="2026-01-02T10:00:00Z",
    )

    result = db.get_videos_by_channel_and_date(
        "channel1",
        "2026-01-01T00:00:00Z",
        "2026-01-03T00:00:00Z",
    )

    video_ids = [row[0] for row in result]

    assert video_ids == ["video2", "video1"]


def test_get_videos_by_channel_and_date_uses_end_exclusive_range(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    create_video(
        db,
        video_id="video1",
        published_at="2026-01-01T00:00:00Z",
    )
    create_video(
        db,
        video_id="video2",
        published_at="2026-01-02T00:00:00Z",
    )

    result = db.get_videos_by_channel_and_date(
        "channel1",
        "2026-01-01T00:00:00Z",
        "2026-01-02T00:00:00Z",
    )

    video_ids = [row[0] for row in result]

    assert video_ids == ["video1"]


def test_get_videos_by_channel_and_date_orders_newest_first(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    create_video(
        db,
        video_id="video1",
        published_at="2026-01-01T00:00:00Z",
    )
    create_video(
        db,
        video_id="video2",
        published_at="2026-01-03T00:00:00Z",
    )
    create_video(
        db,
        video_id="video3",
        published_at="2026-01-02T00:00:00Z",
    )

    result = db.get_videos_by_channel_and_date(
        "channel1",
        "2026-01-01T00:00:00Z",
        "2026-01-04T00:00:00Z",
    )

    video_ids = [row[0] for row in result]

    assert video_ids == ["video2", "video3", "video1"]


def test_get_videos_by_channel_and_date_returns_empty_when_no_match(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    create_video(
        db,
        published_at="2026-01-01T00:00:00Z",
    )

    result = db.get_videos_by_channel_and_date(
        "channel1",
        "2026-02-01T00:00:00Z",
        "2026-02-02T00:00:00Z",
    )

    assert result == []


# ============================================================
# Channel tags
# ============================================================


def test_update_and_get_channel_tags(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    tags = ["music", "live", "推し"]

    db.update_channel_tags("channel1", tags)

    assert db.get_channel_tags("channel1") == tags


def test_update_channel_tags_overwrites_existing_tags(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    db.update_channel_tags(
        "channel1",
        ["music", "live"],
    )

    db.update_channel_tags(
        "channel1",
        ["game", "stream"],
    )

    assert db.get_channel_tags("channel1") == [
        "game",
        "stream",
    ]


def test_update_channel_tags_accepts_empty_list(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    db.update_channel_tags("channel1", [])

    assert db.get_channel_tags("channel1") == []


def test_get_channel_tags_returns_empty_list_when_tags_are_unset(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    assert db.get_channel_tags("channel1") == []


def test_get_channel_tags_returns_empty_list_when_channel_does_not_exist(
    tmp_path,
):
    db = create_db(tmp_path)

    assert db.get_channel_tags("unknown") == []


def test_update_channel_tags_stores_json(tmp_path):
    db = create_db(tmp_path)
    create_channel(db)

    tags = ["music", "日本語", "ライブ"]

    db.update_channel_tags("channel1", tags)

    with db._connect() as conn:
        row = conn.execute(
            "SELECT tags FROM channels WHERE channel_id = ?",
            ("channel1",),
        ).fetchone()

    assert json.loads(row[0]) == tags
