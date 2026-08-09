from datetime import datetime

from .create_dailynote import *
from.fetch_md_file import *

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

def extract_lists_from_heading(file_path, target_heading):
    """
    指定したファイルと見出しから本文を取得し、リストを抽出してまとめる（共通処理）
    """
    file_name = os.path.basename(file_path)
    content = get_content_by_heading(file_path, target_heading)
    
    lists = extract_lists_from_content(content) if content else {"bullets": [], "numbered": [], "tasks": []}
    
    return {
        "file_name": file_name,
        "heading": target_heading,
        "lists": lists
    }

def extract_lists_from_all_sub_headings(file_path, target_heading):
    """
    指定見出し配下のすべての下位見出しに対して extract_lists_from_heading を実行する
    """
    sub_headings = get_sub_headings_by_heading(file_path, target_heading)
    
    return [
        extract_lists_from_heading(file_path, sh["text"])
        for sh in sub_headings
    ]
    
def parse_vocabulary_line(line):
    """
    「単語: 意味」の形式の文字列から単語と意味を分解する
    """
    # 記号の箇条書きマーカー（- や * や +）や数字、空白を除去
    cleaned = re.sub(r"^[\s\-*+\d\.]+", "", line).strip()
    
    # コロン（全角・半角）で分割
    if ":" in cleaned:
        word, meaning = cleaned.split(":", 1)
    elif "：" in cleaned:
        word, meaning = cleaned.split("：", 1)
    else:
        return None
        
    return {
        "word": word.strip(),
        "meaning": meaning.strip()
    }
