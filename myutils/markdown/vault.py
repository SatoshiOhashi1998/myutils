from __future__ import annotations

import glob
import os
from datetime import date, datetime
import re

import frontmatter


class Note:
    """個別のMarkdownファイルを操作するクラス。"""

    def __init__(self, file_path: str):
        self.file_path = os.path.abspath(file_path)
        self.post = frontmatter.load(self.file_path)

    @property
    def content(self) -> str:
        """Front Matterを除いたMarkdown本文。"""
        return self.post.content

    @content.setter
    def content(self, value: str) -> None:
        self.post.content = value

    @property
    def metadata(self) -> dict:
        """Front Matterのメタデータ。"""
        return self.post.metadata

    def save(self) -> None:
        """変更をファイルへ保存する。"""
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(self.post))

    def set_created_date(self, target_date=None) -> None:
        """Front Matterのcreatedを設定して保存する。"""
        if target_date is None:
            target_date = datetime.now()

        if isinstance(target_date, datetime):
            date_str = target_date.strftime("%Y-%m-%d")
        else:
            date_str = str(target_date)

        self.post.metadata["created"] = date_str
        self.save()

    def add_tag(self, new_tag: str) -> None:
        """Front Matterのtagsへタグを追加して保存する。"""
        tags = self.post.metadata.get("tags", [])

        if tags is None:
            tags = []
        elif isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            tags = list(tags)

        if new_tag not in tags:
            tags.append(new_tag)
            self.post.metadata["tags"] = tags
            self.save()

    def append_to_heading(
        self, target_heading: str, text_to_append: str
    ) -> None:
        """
        指定した見出しセクションの末尾に追記する。
        見出しが存在しない場合は ## 見出し を末尾へ追加する。
        """
        lines = self.content.splitlines()
        new_lines: list[str] = []
        capturing = False
        target_level = 0
        inserted = False

        for line in lines:
            is_heading = line.startswith("#")
            level = len(line.split()[0]) if is_heading else 0
            heading_text = (
                line.lstrip("#").strip() if is_heading else ""
            )

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
            if new_lines and new_lines[-1] != "":
                new_lines.append("")
            new_lines.append(f"## {target_heading}")
            new_lines.append(text_to_append)

        self.content = "\n".join(new_lines)
        self.save()

    def get_content_by_heading(self, target_heading: str) -> str | None:
        """
        特定見出しから次の同等以上の見出しまでの本文を返す。

        旧実装の挙動を維持し、見出しが存在しない場合や本文が空の場合は
        空文字列を返す。読み込み等で例外が発生した場合のみ呼び出し側へ伝播する。
        """
        lines = self.content.splitlines()
        capturing = False
        target_level = 0
        heading_lines: list[str] = []

        for line in lines:
            if line.startswith("#"):
                level = len(line.split()[0])
                heading_text = line.lstrip("#").strip()

                if not capturing:
                    if heading_text == target_heading:
                        capturing = True
                        target_level = level
                        continue
                elif level <= target_level:
                    break

            if capturing:
                heading_lines.append(line)

        return "\n".join(heading_lines).strip()

    def find_headings_by_tag(self, tag: str) -> list[str]:
        """単一ノート内で指定タグが含まれる行が属する見出しを取得する。"""
        matched_headings: list[str] = []
        current_heading = "Top"

        tag_pattern = re.compile(
            rf"(?:^|[\s\W])"
            rf"(#{re.escape(tag)}(?:/[^\s]+)?)"
            rf"(\s|$)",
            re.IGNORECASE,
        )

        for line in self.content.splitlines():
            stripped = line.strip()

            if re.match(r"^#{1,6}[\s\t]", stripped):
                current_heading = stripped.lstrip("#").strip()

            if tag_pattern.search(line):
                if current_heading not in matched_headings:
                    matched_headings.append(current_heading)

        return matched_headings


class Vault:
    """Vault全体（ディレクトリ）を管理するクラス。"""

    def __init__(self, target_dir: str):
        self.target_dir = os.path.abspath(target_dir)

    def get_note(self, relative_path: str) -> Note:
        """
        指定パスのNoteを取得する。

        relative_pathが絶対パスの場合はそのまま利用するため、
        既存のFlask側からも扱いやすい。
        """
        if os.path.isabs(relative_path):
            path = relative_path
        else:
            path = os.path.join(self.target_dir, relative_path)
        return Note(path)

    def find_notes_by_keyword(
        self,
        keyword: str = "計画",
        extension: str = "md",
        recursive: bool = False,
    ) -> list[Note]:
        """
        キーワードをファイル名に含むノートを取得する。

        旧find_files_by_keywordの挙動を維持し、recursive=Falseが既定値。
        """
        search_pattern = os.path.join(
            self.target_dir, f"*.{extension}"
        )
        if recursive:
            search_pattern = os.path.join(
                self.target_dir, f"**/*.{extension}"
            )

        notes: list[Note] = []

        for file_path in glob.glob(search_pattern, recursive=recursive):
            if keyword in os.path.basename(file_path):
                notes.append(Note(file_path))

        return notes

    def find_notes_by_created_date(
        self,
        start_date,
        end_date,
        extension: str = "md",
    ) -> list[Note]:
        """Front Matterのcreatedが指定範囲内にあるノートを取得する。"""
        if isinstance(start_date, str):
            start_date = datetime.strptime(
                start_date, "%Y-%m-%d"
            ).date()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()

        if isinstance(end_date, str):
            end_date = datetime.strptime(
                end_date, "%Y-%m-%d"
            ).date()
        elif isinstance(end_date, datetime):
            end_date = end_date.date()

        search_pattern = os.path.join(
            self.target_dir, f"**/*.{extension}"
        )
        matched_notes: list[Note] = []

        for file_path in glob.glob(search_pattern, recursive=True):
            try:
                note = Note(file_path)
                created_val = note.metadata.get("created")
                if not created_val:
                    continue

                file_date = None

                if isinstance(created_val, datetime):
                    file_date = created_val.date()
                elif isinstance(created_val, date):
                    file_date = created_val
                elif isinstance(created_val, str):
                    try:
                        file_date = datetime.strptime(
                            created_val[:10], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        continue

                if (
                    file_date
                    and start_date <= file_date <= end_date
                ):
                    matched_notes.append(note)

            except Exception as e:
                print(
                    f"ファイル読み込みスキップ "
                    f"({file_path}): {e}"
                )

        return matched_notes

    def find_headings_by_tag(
        self,
        tag: str,
        extension: str = "md",
    ) -> list[dict]:
        """Vault配下の全Markdownを対象にタグを含む見出しを検索する。"""
        search_pattern = os.path.join(
            self.target_dir, f"**/*.{extension}"
        )
        all_results: list[dict] = []

        for file_path in glob.glob(search_pattern, recursive=True):
            try:
                note = Note(file_path)
                headings = note.find_headings_by_tag(tag)
            except Exception as e:
                print(
                    f"ファイル読み込みエラー "
                    f"({file_path}): {e}"
                )
                continue

            if headings:
                file_name = os.path.splitext(
                    os.path.basename(file_path)
                )[0]
                all_results.append(
                    {
                        "file_name": file_name,
                        "file_path": file_path,
                        "headings": headings,
                    }
                )

        return all_results
