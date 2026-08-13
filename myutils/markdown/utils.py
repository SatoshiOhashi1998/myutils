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
    """「運動: 30分」や「アニメ鑑賞: 90分」のようなテキストから tag と minutes を抽出する。"""
    match = re.search(r"^(.*?):\s*(\d+)分$", text.strip())
    if match:
        return {
            "tag": match.group(1).strip(),
            "minutes": int(match.group(2))
        }
    return None


def parse_tag_time_line_with_start(text: str) -> Optional[Dict[str, Any]]:
    """
    タスク文字列から タグ, 分数, 開始時刻(任意) を抽出する。
    例:
      - "- [ ] 運動: 30分 @18:00" -> {'tag': '運動', 'minutes': 30, 'start_time': '18:00'}
      - "運動: 30分"               -> {'tag': '運動', 'minutes': 30, 'start_time': None}
    """
    if not text:
        return None

    # 1. 先頭の箇条書き記号を完全に除去
    clean_text = re.sub(r"^[\s\t]*[-*+]\s*(\[[ xX]\]\s*)?", "", text).strip()

    # 2. タグ: 分数 [@時刻] のパターンにマッチング（スペースを含むタグにも対応）
    pattern = r"^(?P<tag>[^:]+?)\s*:\s*(?P<minutes>\d+)分(?:\s*@(?P<start_time>\d{1,2}:\d{2}))?"
    
    match = re.search(pattern, clean_text)
    if not match:
        return None

    data = match.groupdict()
    return {
        "tag": data["tag"].strip(),
        "minutes": int(data["minutes"]),
        "start_time": data.get("start_time"),
    }
