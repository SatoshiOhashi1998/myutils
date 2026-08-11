import os
import re
import glob
from .core_reader import get_content_by_heading, get_sub_headings_by_heading, extract_lists_from_content


# ==========================================
# 1. リスト抽出関連
# ==========================================

def extract_lists_from_heading(file_path: str, target_heading: str) -> dict:
    """
    指定したファイルの見出しセクションからリスト（箇条書き・順序・タスク）を抽出する。

    Args:
        file_path (str): 対象のMarkdownファイルのパス
        target_heading (str): 対象の見出しテキスト

    Returns:
        dict: {"file_name": ..., "heading": ..., "lists": ...} 形式の辞書
    """
    base_name = os.path.basename(file_path)
    file_name = os.path.splitext(base_name)[0]
    content = get_content_by_heading(file_path, target_heading)
    lists = extract_lists_from_content(content) if content else {"bullets": [], "numbered": [], "tasks": []}
    return {"file_name": file_name, "heading": target_heading, "lists": lists}

def extract_lists_from_all_sub_headings(file_path: str, target_heading: str) -> list:
    """
    指定した見出し配下のすべてのサブ見出しから、それぞれリストを抽出してリストで返す。

    Args:
        file_path (str): 対象のMarkdownファイルのパス
        target_heading (str): 親となる見出しのテキスト

    Returns:
        list: extract_lists_from_heading の結果のリスト
    """
    sub_headings = get_sub_headings_by_heading(file_path, target_heading)
    return [extract_lists_from_heading(file_path, sh["text"]) for sh in sub_headings]


# ==========================================
# 2. パース（解析）関連
# ==========================================

def parse_vocabulary_line(line: str) -> dict | None:
    """
    語学学習などの行（例: "- 単語 : 意味"）をパースして単語と意味の辞書に変換する。

    Args:
        line (str): 解析対象の行文字列

    Returns:
        dict | None: {"word": ..., "meaning": ...} 形式の辞書。パース失敗時はNone
    """
    cleaned = re.sub(r"^[\s\-*+\d\.]+", "", line).strip()
    if ":" in cleaned:
        word, meaning = cleaned.split(":", 1)
    elif "：" in cleaned:
        word, meaning = cleaned.split("：", 1)
    else:
        return None
    return {"word": word.strip(), "meaning": meaning.strip()}


# ==========================================
# 3. タグ検索関連
# ==========================================

def find_headings_by_tag_in_file(file_path: str, tag: str) -> list:
    """
    1つのファイルを対象に、本文内に指定タグが含まれる行が属する見出しをすべて取得する。

    Args:
        file_path (str): 対象のMarkdownファイルのパス
        tag (str): 検索するタグ名（# を除く）

    Returns:
        list: 条件に一致した見出しテキストのリスト
    """
    matched_headings = []
    current_heading = "Top"
    
    tag_pattern = re.compile(rf"(^|\s)(#{re.escape(tag)}(?:\/[^\s]+)?)(\s|$)", re.IGNORECASE)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
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
    ディレクトリを対象に、配下のすべてのファイルを走査して指定タグが含まれる見出しのリストを取得する。

    Args:
        target_dir (str): 検索対象のディレクトリパス
        tag (str): 検索するタグ名
        extension (str): 対象の拡張子（デフォルト: "md"）

    Returns:
        list: ファイル情報と該当見出しのリスト
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
