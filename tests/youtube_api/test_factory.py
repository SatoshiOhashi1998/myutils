from unittest.mock import MagicMock

import myutils.youtube_api.factory as factory


def test_create_youtube_api_builds_and_wires_dependencies(monkeypatch):
    google_youtube = MagicMock(name="google_youtube")
    client = MagicMock(name="client")
    db = MagicMock(name="db")
    api = MagicMock(name="api")

    build = MagicMock(return_value=google_youtube)
    youtube_client = MagicMock(return_value=client)
    youtube_db = MagicMock(return_value=db)
    youtube_api = MagicMock(return_value=api)

    monkeypatch.setattr(factory, "API_KEY", "test-api-key")
    monkeypatch.setattr(factory, "build", build)
    monkeypatch.setattr(factory, "YouTubeClient", youtube_client)
    monkeypatch.setattr(factory, "YouTubeDB", youtube_db)
    monkeypatch.setattr(factory, "YouTubeAPI", youtube_api)

    result = factory.create_youtube_api()

    assert result is api

    build.assert_called_once_with(
        "youtube",
        "v3",
        developerKey="test-api-key",
    )
    youtube_client.assert_called_once_with(google_youtube)
    youtube_db.assert_called_once_with()
    youtube_api.assert_called_once_with(
        client=client,
        db=db,
    )
