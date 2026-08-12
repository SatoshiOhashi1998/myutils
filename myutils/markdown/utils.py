import re


def format_obsidian_link(title: str) -> str:
    """タイトルをObsidianの埋め込みリンク形式（![[タイトル]]）に整形する。"""
    clean_title = title.strip()
    return f"![[{clean_title}]]"


def parse_vocabulary_line(line: str) -> dict | None:
    """「単語 : 意味」形式の行をパースして辞書化する。"""
    cleaned = re.sub(r"^[\s\-*+\d\.]+", "", line).strip()
    if ":" in cleaned:
        word, meaning = cleaned.split(":", 1)
    elif "：" in cleaned:
        word, meaning = cleaned.split("：", 1)
    else:
        return None
    return {"word": word.strip(), "meaning": meaning.strip()}

def parse_tag_time_line(line: str) -> dict | None:
    """「tag: time」フォーマットの文字列を分解し、タグ名と分数を取得する。

    例: "勉強: 90分" -> {"tag": "勉強", "minutes": 90}
        "- 作業 : 120分" -> {"tag": "作業", "minutes": 120}

    Args:
        line (str): 解析対象の文字列

    Returns:
        dict | None: {"tag": str, "minutes": int} 形式の辞書。パース失敗時はNone
    """
    if not line:
        return None

    # 行頭の箇条書き記号（- * + 数字.）やスペースを除去
    cleaned = re.sub(r"^[\s\-*+\d\.]+", "", line).strip()

    # 「タグ名 : 数字 + 分」にマッチする正規表現（コロンは全角・半角両対応）
    match = re.match(r"^(.+?)[\s:]+[:：]\s*(\d+)\s*分?", cleaned)

    if match:
        tag_name = match.group(1).strip()
        minutes = int(match.group(2))
        return {"tag": tag_name, "minutes": minutes}

    return None
