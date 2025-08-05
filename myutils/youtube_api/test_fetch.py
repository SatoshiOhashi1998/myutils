import datetime
from myutils.youtube_api.fetch_youtube_data import YouTubeAPI


def test_get_channel_videos_with_cache_returns_list():
    api = YouTubeAPI()

    # テスト用のチャンネルIDと期間
    channel_id = "UCyLGcqYs7RsBb3L0SJfzGYA"
    start_date = datetime.datetime(2025, 7, 1)
    end_date = datetime.datetime(2025, 8, 1)

    results = api.get_channel_videos_with_cache(channel_id, start_date, end_date)

    # 結果がリストで返ってくることを確認
    assert isinstance(results, list)

    # 中身に要素があるなら、最低限の構造をチェック
    if results:
        video = results[0]
        assert "video_id" in video or len(video) >= 1  # SQLiteのRowならタプル
