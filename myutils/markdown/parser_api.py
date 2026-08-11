import os
import re
import glob
from .core_reader import get_content_by_heading, get_sub_headings_by_heading, extract_lists_from_content

def extract_lists_from_heading(file_path, target_heading):
    base_name = os.path.basename(file_path)
    file_name = os.path.splitext(base_name)[0]
    content = get_content_by_heading(file_path, target_heading)
    lists = extract_lists_from_content(content) if content else {"bullets": [], "numbered": [], "tasks": []}
    return {"file_name": file_name, "heading": target_heading, "lists": lists}

def extract_lists_from_all_sub_headings(file_path, target_heading):
    sub_headings = get_sub_headings_by_heading(file_path, target_heading)
    return [extract_lists_from_heading(file_path, sh["text"]) for sh in sub_headings]

def parse_vocabulary_line(line):
    cleaned = re.sub(r"^[\s\-*+\d\.]+", "", line).strip()
    if ":" in cleaned:
        word, meaning = cleaned.split(":", 1)
    elif "：" in cleaned:
        word, meaning = cleaned.split("：", 1)
    else:
        return None
    return {"word": word.strip(), "meaning": meaning.strip()}

def find_headings_by_tag_in_file(file_path: str, tag: str) -> list:
    """
    1つのファイルを対象に、本文内に指定タグが含まれる行が属する見出しをすべて取得する
    """
    matched_headings = []
    current_heading = "Top"
    
    # タグの正規表現パターン（例: #tag や #tag/sub など）
    tag_pattern = re.compile(rf"(^|\s)(#{re.escape(tag)}(?:\/[^\s]+)?)(\s|$)", re.IGNORECASE)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                # 見出し行の検出（# で始まる行）
                if stripped.startswith('#'):
                    current_heading = stripped.lstrip('#').strip()
                elif tag_pattern.search(line):
                    if current_heading not in matched_headings:
                        matched_headings.append(current_heading)
    except Exception as e:
        print(f"ファイル読み込みエラー ({file_path}): {e}")
        
    return matched_headings

def find_headings_by_tag_in_directory(target_dir: str, tag: str, extension: str = "md") -> list:
    """
    ディレクトリを対象に、配下のすべてのファイルを走査して指定タグが含まれる見出しのリストを取得する
    """
    search_pattern = os.path.join(target_dir, f"**/*.{extension}")
    all_results = []
    
    for file_path in glob.glob(search_pattern, recursive=True):
        headings = find_headings_by_tag_in_file(file_path, tag)
        if headings:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            all_results.append({
                "file_name": file_name,
                "file_path": file_path,
                "headings": headings
            })
            
    return all_results
