# note_builder.py
from datetime import timedelta, datetime

def generate_google_calendar_link_text(target_date=None) -> str:
    """Googleカレンダーのリンク付き文字列を生成する"""
    if target_date is None:
        target_date = datetime.now()
    date_display = target_date.strftime('%Y/%m/%d')
    calendar_url = f"https://calendar.google.com/calendar/u/0/r/week/{target_date.year}/{target_date.month}/{target_date.day}"
    return f"[{date_display}のリンク]({calendar_url})"

def generate_dailynote_links(start_date: datetime, end_date: datetime) -> str:
    """指定期間のデイリーノートリンク（[[YYYY-MM-DD]]）を改行区切りで生成"""
    links = []
    current_date = start_date
    while current_date <= end_date:
        links.append(f"[[{current_date.strftime('%Y-%m-%d')}]]")
        current_date += timedelta(days=1)
    return "\n".join(links)

def generate_plan_note_links(plan_file_titles: list, year: int, week_num: int) -> str:
    """ファイルタイトルのリストから指定週の計画リンク文字列を生成する"""
    week_str = f"{year}-W{week_num:02d}"
    plan_links = [f"[[{file_title}#{week_str}]]" for file_title in plan_file_titles]
    return "\n".join(plan_links)

def calculate_week_range(target_date: datetime, start_of_week: str = "monday"):
    """週の開始日、終了日、年、週番号を計算する"""
    if start_of_week == "monday":
        start_date = target_date - timedelta(days=target_date.weekday())
    else:
        start_date = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
        
    end_date = start_date + timedelta(days=6)
    year, week_num, _ = target_date.isocalendar()
    return start_date, end_date, year, week_num
