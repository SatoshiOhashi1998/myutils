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

def parse_tag_time_line(text: str) -> dict | None:
    """
    「運動: 30分」や「アニメ鑑賞: 90分」のようなテキストから
    tag と minutes を抽出する。
    """
    # 「タスク名: 数字分」のパターンにマッチさせる
    match = re.search(r"^(.*?):\s*(\d+)分$", text.strip())
    if match:
        return {
            "tag": match.group(1).strip(),
            "minutes": int(match.group(2))
        }
    return None
