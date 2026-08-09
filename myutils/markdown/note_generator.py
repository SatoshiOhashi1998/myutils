from datetime import timedelta, datetime
import os
from jinja2 import Template
from .yaml_handler import set_created_date_to_markdown
from .core_reader import append_content_to_heading, find_files_by_keyword

def generate_google_calendar_link_text(target_date=None):
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

def generate_plan_note_links(target_dir: str, year: int, week_num: int) -> str:
    """
    core_reader の find_files_by_keyword を使って計画ファイルを探し、
    指定週のリンク文字列を生成する
    """
    plan_files = find_files_by_keyword(target_dir, keyword="計画", extension="md")
    week_str = f"{year}-W{week_num:02d}"
    
    plan_links = [f"[[{file_title}#{week_str}]]" for file_title in plan_files]
    return "\n".join(plan_links)

def create_daily_note_from_file(output_dir, target_date, template_path):
    """デイリーノートを作成する"""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{target_date.strftime('%Y-%m-%d')}.md")
    
    if os.path.exists(file_path):
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        rendered_content = Template(f.read()).render(
            date=target_date.strftime('%Y-%m-%d'),
            weekday=target_date.strftime('%A')
        )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(rendered_content)

    set_created_date_to_markdown(file_path, target_date)
    append_content_to_heading(file_path, 'Google Calender', generate_google_calendar_link_text(target_date))

def batch_create_dailies_from_file(output_dir, start_date, days_count, template_path):
    for i in range(days_count):
        create_daily_note_from_file(output_dir, start_date + timedelta(days=i), template_path)

def create_weekly_note(output_dir, target_date, template_path, plan_dir=None, start_of_week="monday"):
    """ウィークリーノートを作成し、該当週のデイリーノートおよび計画ノートのリンクを挿入する"""
    os.makedirs(output_dir, exist_ok=True)
    
    if start_of_week == "monday":
        start_date = target_date - timedelta(days=target_date.weekday())
    else:
        start_date = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
        
    end_date = start_date + timedelta(days=6)
    year, week_num, _ = target_date.isocalendar()
    
    file_path = os.path.join(output_dir, f"{year}-W{week_num:02d}.md")
    if os.path.exists(file_path):
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        rendered_content = Template(f.read()).render(
            year=year, week=week_num,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(rendered_content)

    set_created_date_to_markdown(file_path, target_date)
    
    # 1. デイリーノートのリンクを挿入
    append_content_to_heading(file_path, 'デイリーノート', generate_dailynote_links(start_date, end_date))
    
    # 2. 計画ノートのリンクを挿入（plan_dirが指定されている場合）
    if plan_dir:
        plan_links_text = generate_plan_note_links(plan_dir, year, week_num)
        if plan_links_text:
            append_content_to_heading(file_path, '計画ノート', plan_links_text)
