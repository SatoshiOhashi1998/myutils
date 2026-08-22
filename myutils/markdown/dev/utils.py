# utils.py
import re
from datetime import timedelta, datetime
from typing import Optional, Dict, Any

def format_obsidian_link(title: str) -> str:
    """タイトルをObsidianの埋め込みリンク形式（![[タイトル]]）に整形する"""
    return f"![[{title.strip()}]]"

def parse_vocabulary_line(line: str) -> dict | None:
    """「単語 : 意味」形式の行をパースして辞書化する"""
    cleaned = re.sub(r"^[\s\-*+\d\.]+", "", line).strip()
    for sep in [":", "："]:
        if sep in cleaned:
            word, meaning = cleaned.split(sep, 1)
            return {"word": word.strip(), "meaning": meaning.strip()}
    return None

def _parse_time_str_to_minutes(time_str: str) -> Optional[int]:
    """「30分」「1.5時間」などの文字列を分数(int)に変換する"""
    time_str = time_str.strip()
    if m := re.fullmatch(r"(\d+(?:\.\d+)?)時間", time_str):
        return int(float(m.group(1)) * 60)
    if m := re.fullmatch(r"(\d+)時間半", time_str):
        return int(m.group(1)) * 60 + 30
    if m := re.fullmatch(r"(?:(\d+)時間)?\s*(?:(\d+)分)?", time_str):
        if m.group(1) or m.group(2):
            return (int(m.group(1) or 0) * 60) + int(m.group(2) or 0)
    return None

def parse_tag_time_line_with_start(text: str) -> Optional[Dict[str, Any]]:
    """タスク文字列から タグ, 分数, 開始時刻(任意) を抽出する"""
    if not text: 
        return None
    clean = re.sub(r"^[\s\t]*[-*+]\s*(\[[ xX]\]\s*)?", "", text).strip()
    
    start_time = None
    if t_match := re.search(r"\s*@(\d{1,2}:\d{2})$", clean):
        start_time = t_match.group(1)
        clean = clean[:t_match.start()].strip()

    if tag_match := re.search(r"^(.*?):\s*(.+)$", clean):
        if (minutes := _parse_time_str_to_minutes(tag_match.group(2))) is not None:
            return {"tag": tag_match.group(1).strip(), "minutes": minutes, "start_time": start_time}
    return None

def calculate_week_range(target_date: datetime, start_of_week: str = "monday"):
    """週の開始日、終了日、年、週番号を計算する"""
    offset = target_date.weekday() if start_of_week == "monday" else (target_date.weekday() + 1) % 7
    start_date = target_date - timedelta(days=offset)
    end_date = start_date + timedelta(days=6)
    year, week_num, _ = target_date.isocalendar()
    return start_date, end_date, year, week_num
