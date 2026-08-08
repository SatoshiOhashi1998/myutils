from datetime import timedelta, datetime
import os
from jinja2 import Template
from .yaml_editor import set_created_date_to_markdown
from .fetch_md_file import append_content_to_heading

def create_daily_note_from_file(output_dir, target_date, template_path):
    """
    既存のマークダウンファイルをテンプレートとして読み込み、デイリーノートを作成する関数
    """
    os.makedirs(output_dir, exist_ok=True)
    
    file_name = f"{target_date.strftime('%Y-%m-%d')}.md"
    file_path = os.path.join(output_dir, file_name)
    
    if os.path.exists(file_path):
        print(f"スキップ: {file_path} は既に存在します。")
        return

    # テンプレートファイルを読み込む
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Jinja2で変数を埋め込む
    template = Template(template_content)
    rendered_content = template.render(
        date=target_date.strftime('%Y-%m-%d'),
        weekday=target_date.strftime('%A')
    )
    
    # 新しいファイルに書き込み
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(rendered_content)
    
    print(f"作成完了: {file_path}")

    # 作成したファイルに対して created 日付を設定する
    set_created_date_to_markdown(file_path, target_date)

    calender_text = generate_google_calendar_link_text(target_date=target_date)
    append_content_to_heading(file_path, 'Google Calender', calender_text)

def generate_google_calendar_link_text(target_date=None):
    """
    指定された日付（省略時は当日）を元に、Googleカレンダーのリンク付き文字列を生成する
    """
    if target_date is None:
        target_date = datetime.now()
    
    # 日付の各要素を取得
    year = target_date.year
    month = target_date.month
    day = target_date.day
    
    # 表示用文字列（例: 2026/8/8）
    date_display = target_date.strftime('%Y/%m/%d')
    
    # Googleカレンダーの週表示URLを構築
    calendar_url = f"https://calendar.google.com/calendar/u/0/r/week/{year}/{month}/{day}"
    
    # マークダウン形式のリンク文字列を作成
    result_text = f"[{date_display}のリンク]({calendar_url})"
    
    return result_text

# 使い方例：テンプレートファイルを指定して複数日分を一括作成
def batch_create_dailies_from_file(output_dir, start_date, days_count, template_path):
    for i in range(days_count):
        target = start_date + timedelta(days=i)
        create_daily_note_from_file(output_dir, target, template_path)
