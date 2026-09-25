from unittest.mock import MagicMock

from myutils.youtube_api.youtube_client import YouTubeClient


def test_call_delegates_to_google_api_resource_method():
    youtube = MagicMock()
    youtube.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "video1"}],
    }

    client = YouTubeClient(youtube)

    result = client.call(
        "videos",
        "list",
        part="snippet",
        id="video1",
    )

    assert result == {
        "items": [{"id": "video1"}],
    }

    youtube.videos.return_value.list.assert_called_once_with(
        part="snippet",
        id="video1",
    )
    youtube.videos.return_value.list.return_value.execute.assert_called_once_with()
