from datetime import timedelta
import os
from jinja2 import Template
from .yaml_editor import set_created_date_to_markdown

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

# 使い方例：テンプレートファイルを指定して複数日分を一括作成
def batch_create_dailies_from_file(output_dir, start_date, days_count, template_path):
    for i in range(days_count):
        target = start_date + timedelta(days=i)
        create_daily_note_from_file(output_dir, target, template_path)
