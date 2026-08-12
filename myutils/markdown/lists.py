import os
import re
from .headings import get_content_by_heading, get_sub_headings_by_heading


def extract_lists_from_content(content: str) -> dict:
    """Markdown本文から箇条書き・順序リスト・タスクリストを抽出する。"""
    bullet_list, numbered_list, task_list = [], [], []

    for line in content.splitlines():
        stripped = line.strip()

        task_match = re.match(r"^-\s*\[([ xX])\]\s+(.*)", stripped)
        if task_match:
            task_list.append(
                {
                    "text": task_match.group(2),
                    "completed": task_match.group(1).strip() != "",
                }
            )
            continue

        bullet_match = re.match(r"^[-*+]\s+(.*)", stripped)
        if bullet_match:
            bullet_list.append(bullet_match.group(1))
            continue

        numbered_match = re.match(r"^\d+\.\s+(.*)", stripped)
        if numbered_match:
            numbered_list.append(numbered_match.group(1))

    return {
        "bullets": bullet_list,
        "numbered": numbered_list,
        "tasks": task_list,
    }


def extract_nested_lists_from_content(content: str, tab_size: int = 4) -> dict:
    """
    タブやスペースのインデント深さを保持してリスト構造を抽出する。
    """
    bullet_list, task_list = [], []

    for line in content.splitlines():
        if not line.strip():
            continue

        # タブをスペースに変換（デフォルト: タブ1個 ＝ スペース4個）
        expanded_line = line.expandtabs(tab_size)
        indent_spaces = len(expanded_line) - len(expanded_line.lstrip(' '))

        # 1. タスクリストの判定 (- [ ] テキスト)
        task_match = re.match(r"^\s*[-\*+]\s+\[([ xX])\](?:\s+(.*))?$", line)
        if task_match:
            text = task_match.group(2) or ""
            # 空のタスク（"- [ ] " のみ）を除外したい場合は下の条件を残す
            if text.strip():
                task_list.append({
                    "text": text.strip(),
                    "completed": task_match.group(1).strip() != "",
                    "indent": indent_spaces
                })
            continue

        # 2. 箇条書きの判定 (- テキスト)
        bullet_match = re.match(r"^\s*[-\*+]\s+(.*)", line)
        if bullet_match:
            text = bullet_match.group(1).strip()
            if text:
                bullet_list.append({
                    "text": text,
                    "indent": indent_spaces
                })

    return {"bullets": bullet_list, "tasks": task_list}


def extract_lists_from_heading(file_path: str, target_heading: str) -> dict:
    """特定見出しセクションからリストを抽出する。"""
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    content = get_content_by_heading(file_path, target_heading)
    lists = (
        extract_lists_from_content(content)
        if content
        else {"bullets": [], "numbered": [], "tasks": []}
    )
    return {"file_name": file_name, "heading": target_heading, "lists": lists}


def extract_lists_from_all_sub_headings(
    file_path: str, target_heading: str
) -> list[dict]:
    """親見出し配下の全サブ見出しからリストを抽出する。"""
    sub_headings = get_sub_headings_by_heading(file_path, target_heading)
    return [
        extract_lists_from_heading(file_path, sh["text"])
        for sh in sub_headings
    ]
