import isodate


def parse_duration(value):
    try:
        return int(isodate.parse_duration(value).total_seconds())
    except Exception:
        return None


def video_data(video_id, snippet, channel_id=None, duration=None):
    thumbnails = snippet.get("thumbnails", {})

    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "channel_id": channel_id,
        "published_at": snippet.get("publishedAt"),
        "duration": duration,
        "thumbnail_default": thumbnails.get("default", {}).get("url"),
        "thumbnail_medium": thumbnails.get("medium", {}).get("url"),
        "thumbnail_high": thumbnails.get("high", {}).get("url"),
    }


def video_from_api_item(item):
    snippet = item.get("snippet", {})
    content_details = item.get("contentDetails", {})

    duration = None
    duration_iso = content_details.get("duration")

    if duration_iso:
        duration = parse_duration(duration_iso)

    return video_data(
        video_id=item.get("id"),
        snippet=snippet,
        channel_id=snippet.get("channelId"),
        duration=duration,
    )


def video_from_search_item(item, channel_id):
    snippet = item.get("snippet", {})
    video_id = item.get("id", {}).get("videoId")

    return video_data(
        video_id=video_id,
        snippet=snippet,
        channel_id=channel_id,
        duration=None,
    )


def channel_from_api_item(item):
    snippet = item.get("snippet", {})

    return {
        "channel_id": item.get("id"),
        "channel_title": snippet.get("title", ""),
    }
