import frontmatter
import os
from datetime import datetime

def set_created_date_to_markdown(file_path, target_date=None):
    """Front Matterの 'created' に日付を設定する"""
    try:
        if target_date is None:
            target_date = datetime.now()
        date_str = target_date.strftime('%Y-%m-%d') if isinstance(target_date, datetime) else str(target_date)

        post = frontmatter.load(file_path)
        post.metadata['created'] = date_str
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))
    except Exception as e:
        print(f"エラー発生 ({file_path}): {e}")

def add_tag_to_markdown(file_path, new_tag):
    """Front Matterにタグを追加する"""
    try:
        post = frontmatter.load(file_path)
        if 'tags' not in post.metadata:
            post.metadata['tags'] = []
        if isinstance(post.metadata['tags'], str):
            post.metadata['tags'] = [post.metadata['tags']]
        if new_tag not in post.metadata['tags']:
            post.metadata['tags'].append(new_tag)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
    except Exception as e:
        print(f"エラー発生 ({file_path}): {e}")
