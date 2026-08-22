import os
import glob
import re
from datetime import datetime, date
import frontmatter

class Note:
    """個別のMarkdownファイルを操作するクラス"""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._load()

    def _load(self):
        try:
            self.post = frontmatter.load(self.file_path)
        except Exception as e:
            print(f"読み込みエラー ({self.file_path}): {e}")
            self.post = frontmatter.Post("")

    def save(self):
        """変更をファイルに保存する"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(self.post))

    @property
    def content(self) -> str:
        return self.post.content

    @content.setter
    def content(self, value: str):
        self.post.content = value

    def set_created_date(self, target_date=None):
        """作成日をセットして保存"""
        if target_date is None:
            target_date = datetime.now()
        date_str = target_date.strftime('%Y-%m-%d') if isinstance(target_date, datetime) else str(target_date)
        self.post.metadata['created'] = date_str
        self.save()

    def add_tag(self, new_tag: str):
        """タグを追加して保存"""
        tags = self.post.metadata.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        if new_tag not in tags:
            tags.append(new_tag)
            self.post.metadata['tags'] = tags
            self.save()

    def append_to_heading(self, target_heading: str, text_to_append: str):
        """指定見出しの末尾に追記して保存"""
        lines = self.content.splitlines()
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
            new_lines.append(f"## {target_heading}")
            new_lines.append(text_to_append)

        self.content = "\n".join(new_lines)
        self.save()

    def get_content_by_heading(self, target_heading: str) -> str | None:
        """特定見出しの本文を取得"""
        lines = self.content.splitlines()
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
                elif level <= target_level:
                    break
            if capturing:
                heading_lines.append(line)

        return "\n".join(heading_lines).strip() if heading_lines else None


class Vault:
    """Vault全体（ディレクトリ）を管理するクラス"""
    def __init__(self, target_dir: str):
        self.target_dir = target_dir

    def get_note(self, relative_path: str) -> Note:
        """指定パスのノートオブジェクトを取得"""
        return Note(os.path.join(self.target_dir, relative_path))

    def find_notes_by_keyword(self, keyword: str = "計画", extension: str = "md") -> list[Note]:
        """キーワードを含むノートのリストを取得"""
        search_pattern = os.path.join(self.target_dir, f"*.{extension}")
        notes = []
        for file_path in glob.glob(search_pattern):
            if keyword in os.path.basename(file_path):
                notes.append(Note(file_path))
        return notes

    def find_notes_by_created_date(self, start_date, end_date, extension: str = "md") -> list[Note]:
        """作成日の範囲からノートを取得"""
        # ※ここに元の find_files_by_created_date_range の日付判定ロジックを入れ、
        # マッチしたものを Note(file_path) としてリストに詰めて返します。
        pass
