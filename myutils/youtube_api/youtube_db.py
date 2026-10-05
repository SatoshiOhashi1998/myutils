import os
import json
import sqlite3
import csv
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
            channel_title TEXT NOT NULL,
            tags TEXT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_sync_state (
            channel_id TEXT PRIMARY KEY,
            uploads_playlist_id TEXT,
            oldest_synced_at TEXT,
            newest_synced_at TEXT,
            FOREIGN KEY (channel_id)
                REFERENCES channels(channel_id)
                ON DELETE CASCADE
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

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_live_state (
            video_id TEXT PRIMARY KEY,
            is_live INTEGER NOT NULL,
            checked_at TEXT NOT NULL,
            FOREIGN KEY (video_id)
                REFERENCES videos(video_id)
                ON DELETE CASCADE
        );
        """)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_videos_channel_id "
            "ON videos(channel_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_videos_published_at "
            "ON videos(published_at DESC);"
        )

        conn.commit()
        conn.close()

    def insert_channel(self, channel_id, channel_title):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO channels (channel_id, channel_title)
                VALUES (?, ?)
                """,
                (channel_id, channel_title),
            )

    def insert_video(self, video):
        self.upsert_video(video)

    def get_video_by_id(self, video_id):
        """
        指定された video_id の動画情報を取得します。
        """
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM videos WHERE video_id = ?",
                (video_id,),
            ).fetchone()

    def update_video_duration(self, video_id, duration):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE videos SET duration = ?
                WHERE video_id = ?
                """,
                (duration, video_id),
            )

    def search_channels_by_title(self, keyword):
        query = """
            SELECT channel_id, channel_title
            FROM channels
            WHERE channel_title LIKE ?
        """
        param = f"%{keyword}%"

        with self._connect() as conn:
            return conn.execute(query, (param,)).fetchall()

    def get_channel_by_id(self, channel_id):
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT channel_id, channel_title
                FROM channels
                WHERE channel_id = ?
                """,
                (channel_id,),
            ).fetchone()

    def get_videos_by_channel_and_date(self, channel_id, start_date, end_date):
        """
        指定チャンネル・指定期間の動画を取得する。

        start_date は含む。
        end_date は含まない。
        """
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT *
                FROM videos
                WHERE channel_id = ?
                  AND published_at >= ?
                  AND published_at < ?
                ORDER BY published_at DESC
                """,
                (channel_id, start_date, end_date),
            ).fetchall()

    def upsert_video(self, video):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO videos (
                    video_id,
                    title,
                    channel_id,
                    published_at,
                    duration,
                    thumbnail_default,
                    thumbnail_medium,
                    thumbnail_high
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    title = excluded.title,
                    channel_id = excluded.channel_id,
                    published_at = excluded.published_at,
                    duration = COALESCE(
                        excluded.duration,
                        videos.duration
                    ),
                    thumbnail_default = excluded.thumbnail_default,
                    thumbnail_medium = excluded.thumbnail_medium,
                    thumbnail_high = excluded.thumbnail_high
                """,
                (
                    video["video_id"],
                    video["title"],
                    video["channel_id"],
                    video.get("published_at"),
                    video.get("duration"),
                    video.get("thumbnail_default"),
                    video.get("thumbnail_medium"),
                    video.get("thumbnail_high"),
                ),
            )

    def update_channel_tags(self, channel_id, tags):
        """
        指定チャンネルのタグを更新する。

        tags:
            list[str]
        """
        tags_json = json.dumps(
            tags,
            ensure_ascii=False,
        )

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE channels
                SET tags = ?
                WHERE channel_id = ?
                """,
                (tags_json, channel_id),
            )


    def get_channel_tags(self, channel_id):
        """
        指定チャンネルのタグを取得する。

        Returns:
            list[str]:
                タグが未設定の場合は空のリスト。
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT tags
                FROM channels
                WHERE channel_id = ?
                """,
                (channel_id,),
            ).fetchone()

        if row is None or row[0] is None:
            return []

        return json.loads(row[0])

    def set_video_live_state(
        self,
        video_id,
        is_live,
        checked_at,
    ):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO video_live_state (
                    video_id,
                    is_live,
                    checked_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(video_id)
                DO UPDATE SET
                    is_live = excluded.is_live,
                    checked_at = excluded.checked_at
                """,
                (
                    video_id,
                    int(is_live),
                    checked_at,
                ),
            )
            
    def get_video_live_state(self, video_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT video_id, is_live, checked_at
                FROM video_live_state
                WHERE video_id = ?
                """,
                (video_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "video_id": row[0],
            "is_live": bool(row[1]),
            "checked_at": row[2],
        }

    def get_channel_sync_state(self, channel_id):
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT
                    channel_id,
                    uploads_playlist_id,
                    oldest_synced_at,
                    newest_synced_at
                FROM channel_sync_state
                WHERE channel_id = ?
                """,
                (channel_id,),
            ).fetchone()

    def set_channel_sync_state(
        self,
        channel_id,
        uploads_playlist_id=None,
        oldest_synced_at=None,
        newest_synced_at=None,
    ):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO channel_sync_state (
                    channel_id,
                    uploads_playlist_id,
                    oldest_synced_at,
                    newest_synced_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(channel_id)
                DO UPDATE SET
                    uploads_playlist_id =
                        COALESCE(
                            excluded.uploads_playlist_id,
                            channel_sync_state.uploads_playlist_id
                        ),
                    oldest_synced_at =
                        COALESCE(
                            excluded.oldest_synced_at,
                            channel_sync_state.oldest_synced_at
                        ),
                    newest_synced_at =
                        COALESCE(
                            excluded.newest_synced_at,
                            channel_sync_state.newest_synced_at
                        )
                """,
                (
                    channel_id,
                    uploads_playlist_id,
                    oldest_synced_at,
                    newest_synced_at,
                ),
            )

    # for debug 
    def print_table(self, table_name):
        with self._connect() as conn:
            cursor = conn.execute(
                f"SELECT * FROM {table_name}"
            )

            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

        print(f"\n=== {table_name} ===")
        print(" | ".join(columns))

        for row in rows:
            print(" | ".join(str(value) for value in row))

    def export_table_to_csv(self, table_name, output_path):
        with self._connect() as conn:
            cursor = conn.execute(
                f"SELECT * FROM {table_name}"
            )

            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()

        with open(
            output_path,
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as f:
            writer = csv.writer(f)

            writer.writerow(columns)
            writer.writerows(rows)

    def export_channel_video_summary_to_csv(self, output_path):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.channel_id,
                    c.channel_title,
                    COUNT(v.video_id) AS video_count,
                    MIN(v.published_at) AS oldest_published_at,
                    MAX(v.published_at) AS newest_published_at
                FROM channels c
                LEFT JOIN videos v
                    ON c.channel_id = v.channel_id
                GROUP BY
                    c.channel_id,
                    c.channel_title
                ORDER BY
                    c.channel_id
                """
            ).fetchall()

        with open(
            output_path,
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as f:
            writer = csv.writer(f)

            writer.writerow(
                [
                    "channel_id",
                    "channel_title",
                    "video_count",
                    "oldest_published_at",
                    "newest_published_at",
                ]
            )

            writer.writerows(rows)

    def print_channel_video_summary(self):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.channel_id,
                    c.channel_title,
                    COUNT(v.video_id) AS video_count,
                    MIN(v.published_at) AS oldest_published_at,
                    MAX(v.published_at) AS newest_published_at
                FROM channels c
                LEFT JOIN videos v
                    ON c.channel_id = v.channel_id
                GROUP BY
                    c.channel_id,
                    c.channel_title
                ORDER BY
                    c.channel_id
                """
            ).fetchall()

        print("\n=== channel video summary ===")
        print(
            "channel_id | "
            "channel_title | "
            "video_count | "
            "oldest_published_at | "
            "newest_published_at"
        )

        for row in rows:
            print(" | ".join(str(value) for value in row))