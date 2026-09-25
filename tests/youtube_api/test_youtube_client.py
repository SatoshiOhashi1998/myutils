from unittest.mock import MagicMock

from myutils.youtube_api.youtube_client import YouTubeClient


def test_call():
    youtube = MagicMock()
    youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": []
    }

    client = YouTubeClient(youtube)

    result = client.call(
        "videos",
        "list",
        part="snippet",
        id="video1",
    )

    assert result == {"items": []}

    youtube.videos.assert_called_once()
    youtube.videos.return_value.list.assert_called_once_with(
        part="snippet",
        id="video1",
    )
    youtube.videos.return_value.list.return_value.execute.assert_called_once()
