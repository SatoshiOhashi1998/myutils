import os
import re
from .utils import parse_tag_time_line, parse_tag_time_line_with_start


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
    タブやスペースのインデント深さを保持してツリー構造のリストを抽出する。
    """
    flat_tasks = []
    flat_bullets = []

    for line in content.splitlines():
        if not line.strip():
            continue

        expanded_line = line.expandtabs(tab_size)
        indent_spaces = len(expanded_line) - len(expanded_line.lstrip(" "))
        stripped_line = line.strip()

        # 1. タスクリストの判定 (- [ ] テキスト または * [x] テキスト)
        task_match = re.match(r"^[-*+]\s+\[([ xX])\](?:\s+(.*))?$", stripped_line)
        if task_match:
            text = task_match.group(2) or ""
            if text.strip():
                flat_tasks.append(
                    {
                        "text": text.strip(),
                        "completed": task_match.group(1).strip() != "",
                        "indent": indent_spaces,
                        "children": []
                    }
                )
            continue

        # 2. 箇条書きの判定 (- テキスト)
        bullet_match = re.match(r"^[-*+]\s+(.*)", stripped_line)
        if bullet_match:
            text = bullet_match.group(1).strip()
            if text:
                flat_bullets.append(
                    {"text": text, "indent": indent_spaces}
                )

    # スタックを使ってフラットなタスクリストを階層（ツリー）構造に変換
    task_tree = []
    stack = []  # [(indent_level, task_dict)]

    for item in flat_tasks:
        indent = item["indent"]
        
        # 自分よりインデントが深いか同等の要素をスタックからポップ
        while stack and stack[-1][0] >= indent:
            stack.pop()

        if stack:
            # 親要素の children に追加
            stack[-1][1]["children"].append(item)
        else:
            # ルートレベルのタスク
            task_tree.append(item)

        stack.append((indent, item))

    return {"bullets": flat_bullets, "tasks": task_tree}


def parse_tasks_to_tree(tasks: list[dict]) -> list[dict]:
    """
    ツリー構造のタスクリストから tag, minutes, start_time を抽出し、
    子要素のテキスト構造を維持して返す
    """
    tree = []
    for item in tasks:
        text = item.get("text", "")
        parsed = parse_tag_time_line_with_start(text)
        
        if parsed:
            # 子要素のテキストまたはオブジェクトをそのまま保持
            children = item.get("children", [])
            
            node = {
                "tag": parsed["tag"],
                "minutes": parsed["minutes"],
                "start_time": parsed["start_time"],
                "children": children 
            }
            tree.append(node)
            
    return tree
