import os
from datetime import datetime, timedelta
from typing import Dict, Union, Callable, Optional
from jinja2 import Template
from .yaml_handler import set_created_date_to_markdown
from .io import append_content_to_heading, find_files_by_keyword
from .note_builder import (
    generate_google_calendar_link_text,
    generate_dailynote_links,
    generate_plan_note_links,
    calculate_week_range
)

# テンプレートの指定形式を定義 (文字列、曜日名キーの辞書、または関数)
TemplateSpec = Union[str, Dict[str, str], Callable[[datetime], str]]


def resolve_template_path(template_spec: TemplateSpec, target_date: datetime) -> str:
    """
    指定された template_spec と対象日付から適切なテンプレートファイルパスを解決する
    """
    if isinstance(template_spec, str):
        template_path = template_spec
    elif isinstance(template_spec, dict):
        weekday_name = target_date.strftime('%A').upper()  # 'MONDAY', 'TUESDAY' など
        # 該当曜日の指定がなければ 'DEFAULT' キーを参照
        template_path = template_spec.get(weekday_name) or template_spec.get('DEFAULT')
    elif callable(template_spec):
        template_path = template_spec(target_date)
    else:
        raise ValueError(f"無効な template_spec の型です: {type(template_spec)}")

    if not template_path or not os.path.exists(template_path):
        raise FileNotFoundError(f"テンプレートファイルが見つかりません: {template_path}")

    return template_path


def _create_note_from_template(file_path: str, template_path: str, context: dict, target_date: datetime) -> bool:
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


def create_daily_note_from_file(output_dir: str, target_date: datetime, template_spec: TemplateSpec) -> bool:
    """
    デイリーノートを作成する

    :param output_dir: 出力先ディレクトリ
    :param target_date: 作成対象の日付
    :param template_spec: テンプレートパス文字列、曜日別パス辞書、または決定関数
    :return: ファイルが新規作成された場合は True
    """
    file_path = os.path.join(output_dir, f"{target_date.strftime('%Y-%m-%d')}.md")
    template_path = resolve_template_path(template_spec, target_date)

    context = {
        "date": target_date.strftime('%Y-%m-%d'),
        "weekday": target_date.strftime('%A')
    }
    
    if _create_note_from_template(file_path, template_path, context, target_date):
        append_content_to_heading(file_path, 'Google Calender', generate_google_calendar_link_text(target_date))
        return True
    return False


def batch_create_dailies_from_file(output_dir: str, start_date: datetime, days_count: int, template_spec: TemplateSpec) -> int:
    """
    複数日分のデイリーノートを一括作成する

    :return: 新規作成されたノートの件数
    """
    created_count = 0
    for i in range(days_count):
        target_date = start_date + timedelta(days=i)
        if create_daily_note_from_file(output_dir, target_date, template_spec):
            created_count += 1
    return created_count


def create_weekly_note(
    output_dir: str, 
    target_date: datetime, 
    template_path: str, 
    plan_dir: Optional[str] = None, 
    start_of_week: str = "monday"
) -> None:
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
