import frontmatter
import re
import os
import glob


# ==========================================
# 1. 基本的なファイル読み込み・書き込み・検索
# ==========================================

def get_file_content(file_path: str) -> str | None:
    """
    指定されたMarkdownファイルからYAMLフロントマターを除いた本文（コンテンツ）を取得する。

    Args:
        file_path (str): 対象のMarkdownファイルのパス

    Returns:
        str | None: フロントマターを除いた本文文字列。エラー時はNone
    """
    try:
        post = frontmatter.load(file_path)
        return post.content
    except Exception as e:
        print(f"エラー ({file_path}): {e}")
        return None

def find_files_by_keyword(target_dir: str, keyword: str = "計画", extension: str = "md") -> list:
    """
    指定ディレクトリから特定のキーワードをファイル名に含むファイルを検索し、
    拡張子を除いたファイル名のリストを返す。

    Args:
        target_dir (str): 検索対象のディレクトリパス
        keyword (str): ファイル名に含まれるべきキーワード（デフォルト: "計画"）
        extension (str): 対象の拡張子（デフォルト: "md"）

    Returns:
        list: 条件に一致した拡張子抜きのファイル名のリスト
    """
    search_pattern = os.path.join(target_dir, f"*.{extension}")
    matched_names = []
    
    for file_path in glob.glob(search_pattern):
        base_name = os.path.basename(file_path)
        file_title, _ = os.path.splitext(base_name)
        
        if keyword in file_title:
            matched_names.append(file_title)
            
    return matched_names


# ==========================================
# 2. 見出し（Heading）の解析・取得
# ==========================================

def get_headings_from_content(content: str) -> list:
    """
    Markdownの本文文字列からすべての見出し階層とテキストのリストを抽出する。

    Args:
        content (str): 解析対象のMarkdown本文

    Returns:
        list: [{"level": 階層(int), "text": 見出し文(str)}, ...] のリスト
    """
    headings = []
    for line in content.splitlines():
        if line.startswith("#"):
            headings.append({"level": len(line.split()[0]), "text": line.lstrip("#").strip()})
    return headings

def get_content_by_heading(file_path: str, target_heading: str) -> str | None:
    """
    指定したファイル内の特定の見出しから、次の同等以上のレベルの見出しまでの本文を取得する。

    Args:
        file_path (str): 対象のMarkdownファイルのパス
        target_heading (str): 抽出を開始する見出しのテキスト（# を除く）

    Returns:
        str | None: 抽出されたセクションの本文文字列。見つからない場合やエラー時はNone
    """
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

def get_sub_headings_by_heading(file_path: str, target_heading: str) -> list:
    """
    指定した見出しセクション内に含まれるサブ見出し（子見出し）のリストを取得する。

    Args:
        file_path (str): 対象のMarkdownファイルのパス
        target_heading (str): 親となる見出しのテキスト

    Returns:
        list: サブ見出しの情報のリスト（get_headings_from_contentの戻り値と同様）
    """
    content = get_content_by_heading(file_path, target_heading)
    return get_headings_from_content(content) if content else []


# ==========================================
# 3. コンテンツの編集・リスト抽出
# ==========================================

def append_content_to_heading(file_path: str, target_heading: str, text_to_append: str) -> None:
    """
    指定したファイル内の特定の見出しセクションの末尾（次の見出しの直前）にテキストを追記する。
    見出しが存在しない場合は、ファイルの末尾に新しい見出しとテキストを追加する。

    Args:
        file_path (str): 対象のMarkdownファイルのパス
        target_heading (str): 追記対象の見出しテキスト
        text_to_append (str): 追加するテキスト
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

def extract_lists_from_content(content: str) -> dict:
    """
    Markdownの本文文字列から、箇条書き・順序リスト・タスクリストを抽出して辞書形式で返す。

    Args:
        content (str): 解析対象のMarkdown本文

    Returns:
        dict: {"bullets": [...], "numbered": [...], "tasks": [{"text": ..., "completed": ...}]} 形式の辞書
    """
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


# ==========================================
# 4. 外部フォーマット・ユーティリティ
# ==========================================

def format_obsidian_link(title: str) -> str:
    """
    ファイルタイトルをObsidianの埋め込みリンク形式（![[タイトル]]）に加工する。

    Args:
        title (str): 対象のファイルタイトル

    Returns:
        str: 埋め込みリンク形式に加工された文字列
    """
    clean_title = title.strip()
    return f"![[{clean_title}]]"
