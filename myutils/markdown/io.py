import glob
import os
import frontmatter


def get_file_content(file_path: str) -> str | None:
    """指定されたMarkdownファイルからYAMLフロントマターを除いた本文を取得する。"""
    try:
        post = frontmatter.load(file_path)
        return post.content
    except Exception as e:
        print(f"エラー ({file_path}): {e}")
        return None


def find_files_by_keyword(
    target_dir: str, keyword: str = "計画", extension: str = "md"
) -> list[str]:
    """指定ディレクトリから特定のキーワードをファイル名に含むファイルを検索し、拡張子抜きのファイル名リストを返す。"""
    search_pattern = os.path.join(target_dir, f"*.{extension}")
    matched_names = []

    for file_path in glob.glob(search_pattern):
        base_name = os.path.basename(file_path)
        file_title, _ = os.path.splitext(base_name)
        if keyword in file_title:
            matched_names.append(file_title)

    return matched_names


def append_content_to_heading(
    file_path: str, target_heading: str, text_to_append: str
) -> None:
    """指定した見出しセクションの末尾にテキストを追記する。存在しない場合は末尾に新規作成する。"""
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

            if (
                not capturing
                and is_heading
                and heading_text == target_heading
            ):
                capturing = True
                target_level = level

        if capturing and not inserted:
            new_lines.append(text_to_append)
            inserted = True

        if not inserted:
            print(
                f"警告: 見出し '{target_heading}' が見つからないため、末尾に追加します。"
            )
            new_lines.append(f"## {target_heading}")
            new_lines.append(text_to_append)

        post.content = "\n".join(new_lines)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

    except Exception as e:
        print(f"エラー発生 ({file_path}): {e}")
