import re
from typing import Optional, Dict, Any


def format_obsidian_link(title: str) -> str:
    """タイトルをObsidianの埋め込みリンク形式（![[タイトル]]）に整形する。"""
    clean_title = title.strip()
    return f"![[{clean_title}]]"


def parse_vocabulary_line(line: str) -> dict | None:
    """「単語 : 意味」形式の行をパースして辞書化する。"""
    cleaned = re.sub(r"^[\s\-*+\d\.]+", "", line).strip()
    if ":" in cleaned:
        word, meaning = cleaned.split(":", 1)
    elif "：" in cleaned:
        word, meaning = cleaned.split("：", 1)
    else:
        return None
    return {"word": word.strip(), "meaning": meaning.strip()}

def parse_tag_time_line(text: str) -> dict | None:
    """
    「運動: 30分」や「アニメ鑑賞: 90分」のようなテキストから
    tag と minutes を抽出する。
    """
    # 「タスク名: 数字分」のパターンにマッチさせる
    match = re.search(r"^(.*?):\s*(\d+)分$", text.strip())
    if match:
        return {
            "tag": match.group(1).strip(),
            "minutes": int(match.group(2))
        }
    return None

def parse_tag_time_line_with_start(line: str) -> Optional[Dict[str, Any]]:
    """
    タスク行から タグ、所要時間(分)、開始時刻(任意: @HH:MM) を抽出する

    対応フォーマット例:
      - "* [ ] アニメ鑑賞: 90分 @18:00" -> tag: "アニメ鑑賞", minutes: 90, start_time: "18:00"
      - "- [ ] 運動: 30分 @9:30"        -> tag: "運動", minutes: 30, start_time: "09:30"
      - "* [ ] 読書: 45分"              -> tag: "読書", minutes: 45, start_time: None
    """
    # 箇条書き記号とチェックボックスを無視し、タグ、所要時間、任意の @HH:MM を取得する正規表現
    pattern = r"^\s*[-*]\s+\[[\sxX]\]\s*(?P<tag>[^:\s]+):\s*(?P<minutes>\d+)分(?:\s+@(?P<time>\d{1,2}:\d{2}))?"

    match = re.search(pattern, line)
    if not match:
        return None

    tag = match.group("tag").strip()
    minutes = int(match.group("minutes"))
    raw_time = match.group("time")

    start_time = None
    if raw_time:
        # "9:30" などの1桁時を "09:30" にゼロパディングして統一
        hours, mins = raw_time.split(":")
        start_time = f"{int(hours):02d}:{mins}"

    return {
        "tag": tag,
        "minutes": minutes,
        "start_time": start_time  # 時刻指定がない場合は None
    }
