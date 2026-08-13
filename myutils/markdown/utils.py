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
    """「運動: 30分」「アニメ鑑賞: 1時間半」「読書: 1.5時間」「作業: 1時間30分」などのテキストから tag と minutes を抽出する。"""
    # [タグ名]: [時間表記] の形式にマッチさせる
    match = re.search(r"^(.*?):\s*(.+)$", text.strip())
    if not match:
        return None

    tag = match.group(1).strip()
    time_str = match.group(2).strip()

    total_minutes = 0

    # パターン1: 1.5時間、0.5時間（小数表現）
    m_float_hours = re.fullmatch(r"(\d+(?:\.\d+)?)時間", time_str)
    if m_float_hours:
        total_minutes = int(float(m_float_hours.group(1)) * 60)
        return {"tag": tag, "minutes": total_minutes}

    # パターン2: 1時間半
    m_hour_half = re.fullmatch(r"(\d+)時間半", time_str)
    if m_hour_half:
        total_minutes = int(m_hour_half.group(1)) * 60 + 30
        return {"tag": tag, "minutes": total_minutes}

    # パターン3: 1時間30分 / 1時間 / 30分
    m_hour_min = re.fullmatch(r"(?:(\d+)時間)?\s*(?:(\d+)分)?", time_str)
    if m_hour_min and (m_hour_min.group(1) or m_hour_min.group(2)):
        hours = int(m_hour_min.group(1)) if m_hour_min.group(1) else 0
        minutes = int(m_hour_min.group(2)) if m_hour_min.group(2) else 0
        total_minutes = hours * 60 + minutes
        return {"tag": tag, "minutes": total_minutes}

    return None


def _parse_time_str_to_minutes(time_str: str) -> Optional[int]:
    """「30分」「1時間」「1時間半」「1.5時間」「1時間30分」などの文字列を分数(int)に変換するヘルパー関数"""
    time_str = time_str.strip()

    # パターン1: 1.5時間、0.5時間（小数表現）
    m_float_hours = re.fullmatch(r"(\d+(?:\.\d+)?)時間", time_str)
    if m_float_hours:
        return int(float(m_float_hours.group(1)) * 60)

    # パターン2: 1時間半
    m_hour_half = re.fullmatch(r"(\d+)時間半", time_str)
    if m_hour_half:
        return int(m_hour_half.group(1)) * 60 + 30

    # パターン3: 1時間30分 / 1時間 / 30分
    m_hour_min = re.fullmatch(r"(?:(\d+)時間)?\s*(?:(\d+)分)?", time_str)
    if m_hour_min and (m_hour_min.group(1) or m_hour_min.group(2)):
        hours = int(m_hour_min.group(1)) if m_hour_min.group(1) else 0
        minutes = int(m_hour_min.group(2)) if m_hour_min.group(2) else 0
        return hours * 60 + minutes

    return None


def parse_tag_time_line_with_start(text: str) -> Optional[Dict[str, Any]]:
    """
    タスク文字列から タグ, 分数, 開始時刻(任意) を抽出する。
    例:
      - "- [ ] 運動: 30分 @18:00"      -> {'tag': '運動', 'minutes': 30, 'start_time': '18:00'}
      - "- [ ] 読書: 1時間半 @21:30"   -> {'tag': '読書', 'minutes': 90, 'start_time': '21:30'}
      - "アニメ鑑賞: 1.5時間"          -> {'tag': 'アニメ鑑賞', 'minutes': 90, 'start_time': None}
    """
    if not text:
        return None

    # 1. 先頭の箇条書き記号を完全に除去
    clean_text = re.sub(r"^[\s\t]*[-*+]\s*(\[[ xX]\]\s*)?", "", text).strip()

    # 2. 末尾の @時刻 (例: @18:00) を分離
    start_time = None
    time_match = re.search(r"\s*@(\d{1,2}:\d{2})$", clean_text)
    if time_match:
        start_time = time_match.group(1)
        clean_text = clean_text[:time_match.start()].strip()

    # 3. [タグ名]: [時間表現] のパターンで分離
    tag_time_match = re.search(r"^(.*?):\s*(.+)$", clean_text)
    if not tag_time_match:
        return None

    tag = tag_time_match.group(1).strip()
    time_str = tag_time_match.group(2).strip()

    # 4. 時間文字列を分数に変換
    minutes = _parse_time_str_to_minutes(time_str)
    if minutes is None:
        return None

    return {
        "tag": tag,
        "minutes": minutes,
        "start_time": start_time,
    }
