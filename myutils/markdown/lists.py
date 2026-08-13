import os
import re
from .utils import parse_tag_time_line


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
        indent_spaces = len(expanded_line) - len(expanded_line.lstrip(" "))

        # 1. タスクリストの判定 (- [ ] テキスト)
        task_match = re.match(r"^\s*[-\*+]\s+\[([ xX])\](?:\s+(.*))?$", line)
        if task_match:
            text = task_match.group(2) or ""
            if text.strip():
                task_list.append(
                    {
                        "text": text.strip(),
                        "completed": task_match.group(1).strip() != "",
                        "indent": indent_spaces,
                    }
                )
            continue

        # 2. 箇条書きの判定 (- テキスト)
        bullet_match = re.match(r"^\s*[-\*+]\s+(.*)", line)
        if bullet_match:
            text = bullet_match.group(1).strip()
            if text:
                bullet_list.append(
                    {"text": text, "indent": indent_spaces}
                )

    return {"bullets": bullet_list, "tasks": task_list}


def parse_tasks_to_tree(tasks: list[dict]) -> list[dict]:
    """フラットなタスクリスト（indent付き）を親・子の階層構造（ツリー）に変換する。"""
    tree = []
    current_parent = None

    for task in tasks:
        text = task["text"]
        indent = task.get("indent", 0)

        # 最上位階層（親）
        if indent == 0:
            parsed = parse_tag_time_line(text)
            node = {
                "text": text,
                "completed": task.get("completed", False),
                "children": [],
            }

            if parsed:
                node["tag"] = parsed["tag"]
                node["minutes"] = parsed["minutes"]

            current_parent = node
            tree.append(current_parent)

        # 配下階層（子）
        elif current_parent and indent > 0:
            current_parent["children"].append(
                {"text": text, "completed": task.get("completed", False)}
            )

    return tree
