import frontmatter
import re

# 1. ファイルから本文を取得
def get_file_content(file_path):
    """
    ファイルからYAMLを除いた本文を取得する
    """
    try:
        post = frontmatter.load(file_path)
        return post.content
    except Exception as e:
        print(f"エラー ({file_path}): {e}")
        return None

# 2. ファイルパスと見出しを指定してその中の本文を取得
def get_content_by_heading(file_path, target_heading):
    """
    指定した見出し（# など）から次の同等以上の見出しまでの本文を取得する
    """
    try:
        post = frontmatter.load(file_path)
        lines = post.content.splitlines()
        
        capturing = False
        target_level = 0
        heading_lines = []
        
        for line in lines:
            # 見出し行か判定
            if line.startswith("#"):
                level = len(line.split()[0]) # 見出しのシャープの数
                heading_text = line.lstrip("#").strip()
                
                if not capturing:
                    if heading_text == target_heading:
                        capturing = True
                        target_level = level
                        continue
                else:
                    # 同じレベルかそれより上の見出しが出現したら終了
                    if level <= target_level:
                        break
            
            if capturing:
                heading_lines.append(line)
                
        return "\n".join(heading_lines).strip()
    except Exception as e:
        print(f"エラー ({file_path}): {e}")
        return None

# 3. ファイルからYAMLのプロパティ一覧を取得
def get_all_yaml_properties(file_path):
    """
    YAMLのプロパティ（キー）の一覧を取得する
    """
    try:
        post = frontmatter.load(file_path)
        return list(post.metadata.keys())
    except Exception as e:
        print(f"エラー ({file_path}): {e}")
        return []

# 4. ファイルパスとYAMLのプロパティを指定して値を取得
def get_yaml_property_value(file_path, property_key):
    """
    YAMLの特定のプロパティの値を取得する
    """
    try:
        post = frontmatter.load(file_path)
        return post.metadata.get(property_key, None)
    except Exception as e:
        print(f"エラー ({file_path}): {e}")
        return None

def append_content_to_heading(file_path, target_heading, text_to_append):
    """
    指定したファイル内の特定の見出しセクションの末尾の次の行にテキストを書き込む関数
    """
    try:
        post = frontmatter.load(file_path)
        lines = post.content.splitlines()
        
        new_lines = []
        capturing = False
        target_level = 0
        inserted = False
        
        for line in lines:
            is_heading = line.startswith("#")
            level = len(line.split()[0]) if is_heading else 0
            heading_text = line.lstrip("#").strip() if is_heading else ""
            
            # キャプチャ中で、同じレベルかそれより上の見出しが来たら、その手前（セクションの末尾の次）に挿入
            if capturing and is_heading and level <= target_level:
                if not inserted:
                    new_lines.append(text_to_append)
                    inserted = True
                capturing = False

            new_lines.append(line)
            
            # ターゲットの見出しにヒットした場合、キャプチャを開始
            if not capturing and is_heading and heading_text == target_heading:
                capturing = True
                target_level = level
            
        # ファイルの最後まで行っても次の見出しが来なかった場合（セクションがファイルの末尾で終わる場合）
        if capturing and not inserted:
            new_lines.append(text_to_append)
            inserted = True
            
        # 見出し自体が見つからなかった場合
        if not inserted:
            print(f"警告: 見出し '{target_heading}' が見つからなかったため、ファイルの末尾に追加します。")
            new_lines.append(f"## {target_heading}")
            new_lines.append(text_to_append)
            
        post.content = "\n".join(new_lines)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))
            
        print(f"書き込み完了: {file_path} の '{target_heading}' の末尾の次に行に追記しました。")
        
    except Exception as e:
        print(f"エラー発生 ({file_path}): {e}")

def extract_lists_from_content(content):
    """
    本文から箇条書き、順序リスト、タスクリストをそれぞれ抽出する関数
    """
    bullet_list = []
    numbered_list = []
    task_list = []
    
    lines = content.splitlines()
    
    for line in lines:
        stripped = line.strip()
        
        # 1. タスクリストの抽出 (- [ ] または - [x] など)
        task_match = re.match(r"^-\s*\[([ xX])\]\s+(.*)", stripped)
        if task_match:
            status = task_match.group(1).strip() != ""
            text = task_match.group(2)
            task_list.append({"text": text, "completed": status})
            continue
            
        # 2. 箇条書きの抽出 (- または * または +)
        bullet_match = re.match(r"^[-*+]\s+(.*)", stripped)
        if bullet_match:
            bullet_list.append(bullet_match.group(1))
            continue
            
        # 3. 順序リストの抽出 (1. など)
        numbered_match = re.match(r"^\d+\.\s+(.*)", stripped)
        if numbered_match:
            numbered_list.append(numbered_match.group(1))
            
    return {
        "bullets": bullet_list,
        "numbered": numbered_list,
        "tasks": task_list
    }
