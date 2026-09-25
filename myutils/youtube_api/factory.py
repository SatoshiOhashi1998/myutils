import os

from dotenv import load_dotenv
from googleapiclient.discovery import build

from .fetch_youtube_data import YouTubeAPI
from .youtube_client import YouTubeClient
from .youtube_db import YouTubeDB

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")


def create_youtube_api() -> YouTubeAPI:
    """YouTube APIを利用するための依存オブジェクトを構築する。"""
    youtube = build(
        "youtube",
        "v3",
        developerKey=API_KEY,
    )

    return YouTubeAPI(
        client=YouTubeClient(youtube),
        db=YouTubeDB(),
    )
