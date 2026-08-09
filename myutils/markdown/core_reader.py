import frontmatter
import re
import os
import glob

def get_file_content(file_path):
    """ファイルからYAMLを除いた本文を取得する"""
    try:
        post = frontmatter.load(file_path)
        return post.content
    except Exception as e:
        print(f"エラー ({file_path}): {e}")
        return None

def get_content_by_heading(file_path, target_heading):
    """指定した見出しから次の同等以上の見出しまでの本文を取得する"""
    try:
        post = frontmatter.load(file_path)
        lines = post.content.splitlines()
        
        capturing = False
        target_level = 0
        heading_lines = []
        
        for line in lines:
            if line.startswith("#"):
                level = len(line.split()[0])
                heading_text = line.lstrip("#").strip()
                
                if not capturing:
                    if heading_text == target_heading:
                        capturing = True
                        target_level = level
                        continue
                else:
                    if level <= target_level:
                        break
            
            if capturing:
                heading_lines.append(line)
                
        return "\n".join(heading_lines).strip()
    except Exception as e:
        print(f"エラー ({file_path}): {e}")
        return None

def append_content_to_heading(file_path, target_heading, text_to_append):
    """指定したファイル内の特定の見出しセクションの末尾の次に行にテキストを書き込む"""
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
            
            if capturing and is_heading and level <= target_level:
                if not inserted:
                    new_lines.append(text_to_append)
                    inserted = True
                capturing = False

            new_lines.append(line)
            
            if not capturing and is_heading and heading_text == target_heading:
                capturing = True
                target_level = level
                
        if capturing and not inserted:
            new_lines.append(text_to_append)
            inserted = True
            
        if not inserted:
            print(f"警告: 見出し '{target_heading}' が見つからないため、末尾に追加します。")
            new_lines.append(f"## {target_heading}")
            new_lines.append(text_to_append)
            
        post.content = "\n".join(new_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))
            
    except Exception as e:
        print(f"エラー発生 ({file_path}): {e}")

def extract_lists_from_content(content):
    """本文から箇条書き、順序リスト、タスクリストを抽出する"""
    bullet_list, numbered_list, task_list = [], [], []
    for line in content.splitlines():
        stripped = line.strip()
        task_match = re.match(r"^-\s*\[([ xX])\]\s+(.*)", stripped)
        if task_match:
            task_list.append({"text": task_match.group(2), "completed": task_match.group(1).strip() != ""})
            continue
        bullet_match = re.match(r"^[-*+]\s+(.*)", stripped)
        if bullet_match:
            bullet_list.append(bullet_match.group(1))
            continue
        numbered_match = re.match(r"^\d+\.\s+(.*)", stripped)
        if numbered_match:
            numbered_list.append(numbered_match.group(1))
            
    return {"bullets": bullet_list, "numbered": numbered_list, "tasks": task_list}

def get_headings_from_content(content):
    headings = []
    for line in content.splitlines():
        if line.startswith("#"):
            headings.append({"level": len(line.split()[0]), "text": line.lstrip("#").strip()})
    return headings

def get_sub_headings_by_heading(file_path, target_heading):
    content = get_content_by_heading(file_path, target_heading)
    return get_headings_from_content(content) if content else []

def find_files_by_keyword(target_dir: str, keyword: str = "計画", extension: str = "md") -> list:
    """
    指定ディレクトリから特定のキーワードを含むファイル名を検索し、拡張子を除いたファイル名のリストを返す
    """
    search_pattern = os.path.join(target_dir, f"*.{extension}")
    matched_names = []
    
    for file_path in glob.glob(search_pattern):
        base_name = os.path.basename(file_path)
        file_title, _ = os.path.splitext(base_name)
        
        if keyword in file_title:
            matched_names.append(file_title)
            
    return matched_names
