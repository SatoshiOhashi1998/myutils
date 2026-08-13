import glob
import os
import re
import frontmatter

from .lists import (
    extract_nested_lists_from_content,
    parse_tasks_to_tree,
)



def get_headings_from_content(content: str) -> list[dict]:
    """Markdown本文から見出し階層（level）とテキスト（text）のリストを抽出する。"""
    headings = []
    for line in content.splitlines():
        if line.startswith("#"):
            headings.append(
                {
                    "level": len(line.split()[0]),
                    "text": line.lstrip("#").strip(),
                }
            )
    return headings


def get_content_by_heading(
    file_path: str, target_heading: str
) -> str | None:
    """特定の見出しから次の同等以上の見出しまでの本文を取得する。"""
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


def get_sub_headings_by_heading(
    file_path: str, target_heading: str
) -> list[dict]:
    """指定した見出しセクション内に含まれるサブ見出しのリストを取得する。"""
    content = get_content_by_heading(file_path, target_heading)
    return get_headings_from_content(content) if content else []


def find_headings_by_tag_in_file(file_path: str, tag: str) -> list[str]:
    """単一ファイル内で指定タグが含まれる行が属する見出しを取得する。"""
    matched_headings = []
    current_heading = "Top"

    tag_pattern = re.compile(
        rf"(?:^|[\s\W])(#{re.escape(tag)}(?:/[^\s]+)?)(\s|$)", re.IGNORECASE
    )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()

                # 正しい見出しの判定: `#` の直後にスペース（またはタブ）があるか判定
                # 例: "# test" は見出しだが、"#test" はタグ（または通常テキスト）
                if re.match(r"^#{1,6}[\s\t]", stripped):
                    current_heading = stripped.lstrip("#").strip()

                # タグの判定
                if tag_pattern.search(line):
                    if current_heading not in matched_headings:
                        matched_headings.append(current_heading)

    except Exception as e:
        print(f"ファイル読み込みエラー ({file_path}): {e}")

    return matched_headings


def find_headings_by_tag_in_directory(
    target_dir: str, tag: str, extension: str = "md"
) -> list[dict]:
    """ディレクトリ配下の全ファイルを対象に指定タグが含まれる見出しを検索する。"""
    search_pattern = os.path.join(target_dir, f"**/*.{extension}")
    all_results = []

    for file_path in glob.glob(search_pattern, recursive=True):
        headings = find_headings_by_tag_in_file(file_path, tag)
        if headings:
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            all_results.append(
                {
                    "file_name": file_name,
                    "file_path": file_path,
                    "headings": headings,
                }
            )

    return all_results


def get_heading_task_tree(
    file_path: str, target_heading: str
) -> list[dict] | None:
    """指定したファイルと見出しから、構造化されたタスクツリーを取得する。"""
    content = get_content_by_heading(file_path, target_heading)
    if content is None:
        return None

    nested_lists = extract_nested_lists_from_content(content)
    tasks = nested_lists.get("tasks", [])

    return parse_tasks_to_tree(tasks)
