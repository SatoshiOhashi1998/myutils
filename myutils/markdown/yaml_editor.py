import frontmatter
import os
from datetime import datetime

def add_tag_to_markdown(file_path, new_tag):
    """
    指定されたマークダウンファイルのFront Matterにタグを追加する関数
    """
    try:
        # 1. ファイルの読み込み
        # frontmatter.load() でYAMLのメタデータと本文を自動で分離して読み込む
        post = frontmatter.load(file_path)
        
        # 2. 'tags' キーの有無を確認
        # メタデータ内に 'tags' がなければ、空のリストとして新しく作る
        if 'tags' not in post.metadata:
            post.metadata['tags'] = []
            
        # 3. 型の揺れを修正
        # 万が一 tags がリストではなく「文字列」で書かれていても、リストに変換してエラーを防ぐ
        if isinstance(post.metadata['tags'], str):
            post.metadata['tags'] = [post.metadata['tags']]
            
        # 4. タグの追加と保存
        # 指定したタグがまだ含まれていなければ追加する
        if new_tag not in post.metadata['tags']:
            post.metadata['tags'].append(new_tag)
            
            # 変更を反映してファイルを上書き保存する
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
            print(f"更新完了: {file_path} に '{new_tag}' を追加しました。")
        else:
            print(f"スキップ: {file_path} には既に '{new_tag}' が存在します。")
            
    except Exception as e:
        print(f"エラー発生 ({file_path}): {e}")

# 5. ディレクトリ内の全ファイルを処理する関数
def process_directory(directory_path, tag_to_add):
    for filename in os.listdir(directory_path):
        if filename.endswith(".md"):
            add_tag_to_markdown(os.path.join(directory_path, filename), tag_to_add)

def set_created_date_to_markdown(file_path, target_date=None):
    """
    指定されたマークダウンファイルのFront Matterの 'created' に日付を設定する関数
    target_date が省略された場合は当日の日付を使用します
    """
    try:
        # target_date が未指定（None）の場合は現在日時を使用
        if target_date is None:
            target_date = datetime.now()

        # 日付が datetime オブジェクトの場合は文字列に変換
        if isinstance(target_date, datetime):
            date_str = target_date.strftime('%Y-%m-%d')
        else:
            date_str = str(target_date)

        # ファイルを読み込む
        post = frontmatter.load(file_path)
        
        # created に日付を設定（上書き）
        post.metadata['created'] = date_str
        
        # ファイルを上書き保存
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))
            
        print(f"更新完了: {file_path} の created を '{date_str}' に設定しました。")
            
    except Exception as e:
        print(f"エラー発生 ({file_path}): {e}")
