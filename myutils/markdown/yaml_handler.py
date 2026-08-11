import os
import glob
from datetime import datetime, date
import frontmatter

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

def find_files_by_created_date_range(target_dir: str, start_date: [str, date], end_date: [str, date], extension: str = "md") -> list:
    """
    指定ディレクトリ内のファイルを走査し、YAMLの `created` が指定日時の範囲内にある
    ファイルのパス（またはファイル名）のリストを返す
    
    Parameters:
        target_dir (str): 検索対象のディレクトリパス
        start_date: 開始日 ("YYYY-MM-DD" 文字列 または datetime.date型)
        end_date: 終了日 ("YYYY-MM-DD" 文字列 または datetime.date型)
        extension (str): 対象の拡張子
    """
    # 文字列で渡された場合は date 型に変換
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
        
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()

    search_pattern = os.path.join(target_dir, f"**/*.{extension}")
    matched_files = []

    for file_path in glob.glob(search_pattern, recursive=True):
        try:
            # frontmatter を使ってYAMLと本文を安全に読み込む
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                post = frontmatter.load(f)
                
            created_val = post.get("created")
            if not created_val:
                continue
                
            # YAMLの記述形式（datetime型、date型、または "YYYY-MM-DD" などの文字列）に対応
            file_date = None
            if isinstance(created_val, datetime):
                file_date = created_val.date()
            elif isinstance(created_val, date):
                file_date = created_val
            elif isinstance(created_val, str):
                # 文字列の場合は先頭10文字（YYYY-MM-DD）を切り出してパース
                try:
                    file_date = datetime.strptime(created_val[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue
            
            # 指定された日付範囲内（開始日〜終了日を含む）かチェック
            if file_date and (start_date <= file_date <= end_date):
                matched_files.append(file_path)
                
        except Exception as e:
            # パースエラー等のファイルはスキップ
            print(f"ファイル読み込みスキップ ({file_path}): {e}")
            
    return matched_files
