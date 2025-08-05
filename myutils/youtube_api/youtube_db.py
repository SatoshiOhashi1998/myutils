import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()


class YouTubeDB:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv("YOUTUBE_DB_PATH", "youtube.db")
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_title TEXT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            published_at TEXT,
            duration INTEGER,
            thumbnail_default TEXT,
            thumbnail_medium TEXT,
            thumbnail_high TEXT,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at DESC);")

        conn.commit()
        conn.close()

    def insert_channel(self, channel_id, channel_title):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO channels (channel_id, channel_title)
        VALUES (?, ?)
        """, (channel_id, channel_title))
        conn.commit()
        conn.close()

    def insert_video(self, video):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO videos (
            video_id, title, channel_id, published_at, duration,
            thumbnail_default, thumbnail_medium, thumbnail_high
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            video["video_id"],
            video["title"],
            video["channel_id"],
            video.get("published_at"),
            video.get("duration"),
            video.get("thumbnail_default"),
            video.get("thumbnail_medium"),
            video.get("thumbnail_high"),
        ))
        conn.commit()
        conn.close()

    def update_video_duration(self, video_id, duration):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE videos SET duration = ?
            WHERE video_id = ?
        """, (duration, video_id))
        conn.commit()
        conn.close()

    def search_channels_by_title(self, keyword):
        conn = self._connect()
        cursor = conn.cursor()
        query = "SELECT channel_id, channel_title FROM channels WHERE channel_title LIKE ?"
        param = f"%{keyword}%"
        cursor.execute(query, (param,))
        results = cursor.fetchall()
        conn.close()
        return results
