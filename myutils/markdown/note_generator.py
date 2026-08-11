import os
from datetime import timedelta
from jinja2 import Template
from .yaml_handler import set_created_date_to_markdown
from .core_reader import append_content_to_heading, find_files_by_keyword
from .note_builder import (
    generate_google_calendar_link_text,
    generate_dailynote_links,
    generate_plan_note_links,
    calculate_week_range
)

def _create_note_from_template(file_path: str, template_path: str, context: dict, target_date):
    """共通のノート作成・初期化処理"""
    if os.path.exists(file_path):
        return False  

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(template_path, 'r', encoding='utf-8') as f:
        rendered_content = Template(f.read()).render(**context)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(rendered_content)

    set_created_date_to_markdown(file_path, target_date)
    return True

def create_daily_note_from_file(output_dir, target_date, template_path):
    """デイリーノートを作成する"""
    file_path = os.path.join(output_dir, f"{target_date.strftime('%Y-%m-%d')}.md")
    context = {
        "date": target_date.strftime('%Y-%m-%d'),
        "weekday": target_date.strftime('%A')
    }
    
    if _create_note_from_template(file_path, template_path, context, target_date):
        append_content_to_heading(file_path, 'Google Calender', generate_google_calendar_link_text(target_date))

def batch_create_dailies_from_file(output_dir, start_date, days_count, template_path):
    for i in range(days_count):
        create_daily_note_from_file(output_dir, start_date + timedelta(days=i), template_path)

def create_weekly_note(output_dir, target_date, template_path, plan_dir=None, start_of_week="monday"):
    """ウィークリーノートを作成し、該当週のデイリーノートおよび計画ノートのリンクを挿入する"""
    start_date, end_date, year, week_num = calculate_week_range(target_date, start_of_week)
    file_path = os.path.join(output_dir, f"{year}-W{week_num:02d}.md")
    
    context = {
        "year": year,
        "week": week_num,
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d')
    }
    
    if not _create_note_from_template(file_path, template_path, context, target_date):
        return
    
    # 1. デイリーノートのリンクを挿入
    append_content_to_heading(file_path, 'デイリーノート', generate_dailynote_links(start_date, end_date))
    
    # 2. 計画ノートのリンクを挿入
    if plan_dir:
        plan_files = find_files_by_keyword(plan_dir, keyword="計画", extension="md")
        plan_links_text = generate_plan_note_links(plan_files, year, week_num)
        if plan_links_text:
            append_content_to_heading(file_path, '計画ノート', plan_links_text)
