from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Union

from jinja2 import Template

from .vault import Note, Vault
from .utils import MarkdownUtils


TemplateSpec = Union[
    str,
    Dict[str, str],
    Callable[[datetime], str],
]


class NoteParser:
    """Markdown本文の見出し・リスト・タスクを解析するクラス。"""

    def __init__(self, note: Note):
        self.note = note

    def get_headings(self) -> list[dict]:
        """Markdown本文から見出し階層を取得する。"""
        headings: list[dict] = []

        for line in self.note.content.splitlines():
            if line.startswith("#"):
                headings.append(
                    {
                        "level": len(line.split()[0]),
                        "text": line.lstrip("#").strip(),
                    }
                )

        return headings

    def get_sub_headings_by_heading(
        self,
        target_heading: str,
    ) -> list[dict]:
        """
        指定した親見出し配下のサブ見出しを取得する。

        旧実装と同じく、親見出しの本文を取得してから見出しを解析する。
        """
        content = self.note.get_content_by_heading(target_heading)
        return self._get_headings_from_content(content) if content else []

    @staticmethod
    def _get_headings_from_content(content: str) -> list[dict]:
        headings: list[dict] = []

        for line in content.splitlines():
            if line.startswith("#"):
                headings.append(
                    {
                        "level": len(line.split()[0]),
                        "text": line.lstrip("#").strip(),
                    }
                )

        return headings

    def extract_lists(self, target_heading: str | None = None) -> dict:
        """本文または指定見出しから箇条書き・番号付き・タスクを抽出する。"""
        if target_heading is None:
            content = self.note.content
        else:
            content = self.note.get_content_by_heading(
                target_heading
            )

        if not content:
            return {
                "bullets": [],
                "numbered": [],
                "tasks": [],
            }

        bullet_list: list[str] = []
        numbered_list: list[str] = []
        task_list: list[dict] = []

        for line in content.splitlines():
            stripped = line.strip()

            task_match = re.match(
                r"^-\s+\[([ xX])\]\s+(.*)",
                stripped,
            )
            if task_match:
                task_list.append(
                    {
                        "text": task_match.group(2),
                        "completed": (
                            task_match.group(1).strip() != ""
                        ),
                    }
                )
                continue

            bullet_match = re.match(
                r"^[-*+]\s+(.*)",
                stripped,
            )
            if bullet_match:
                bullet_list.append(
                    bullet_match.group(1)
                )
                continue

            numbered_match = re.match(
                r"^\d+\.\s+(.*)",
                stripped,
            )
            if numbered_match:
                numbered_list.append(
                    numbered_match.group(1)
                )

        return {
            "bullets": bullet_list,
            "numbered": numbered_list,
            "tasks": task_list,
        }

    def extract_lists_from_heading(
        self,
        target_heading: str,
    ) -> dict:
        """
        旧extract_lists_from_headingと同じ形式を返す。

        {
            "file_name": ...,
            "heading": ...,
            "lists": {...}
        }
        """
        file_name = os.path.splitext(
            os.path.basename(self.note.file_path)
        )[0]

        lists = self.extract_lists(target_heading)

        return {
            "file_name": file_name,
            "heading": target_heading,
            "lists": lists,
        }

    def extract_lists_from_all_sub_headings(
        self,
        target_heading: str,
    ) -> list[dict]:
        """親見出し配下の全サブ見出しからリストを抽出する。"""
        sub_headings = self.get_sub_headings_by_heading(
            target_heading
        )

        return [
            self.extract_lists_from_heading(sh["text"])
            for sh in sub_headings
        ]

    def extract_nested_lists(
        self,
        target_heading: str | None = None,
        tab_size: int = 4,
    ) -> dict:
        """インデントを保持して箇条書き・タスクをツリー化する。"""
        if target_heading is None:
            content = self.note.content
        else:
            content = self.note.get_content_by_heading(
                target_heading
            )

        if not content:
            return {"bullets": [], "tasks": []}

        flat_tasks: list[dict] = []
        flat_bullets: list[dict] = []

        for line in content.splitlines():
            if not line.strip():
                continue

            expanded_line = line.expandtabs(tab_size)
            indent_spaces = (
                len(expanded_line)
                - len(expanded_line.lstrip(" "))
            )
            stripped_line = line.strip()

            task_match = re.match(
                r"^[-*+]\s+\[([ xX])\](?:\s+(.*))?$",
                stripped_line,
            )

            if task_match:
                text = task_match.group(2) or ""

                if text.strip():
                    flat_tasks.append(
                        {
                            "text": text.strip(),
                            "completed": (
                                task_match.group(1).strip()
                                != ""
                            ),
                            "indent": indent_spaces,
                            "children": [],
                        }
                    )
                continue

            bullet_match = re.match(
                r"^[-*+]\s+(.*)",
                stripped_line,
            )
            if bullet_match:
                text = bullet_match.group(1).strip()
                if text:
                    flat_bullets.append(
                        {
                            "text": text,
                            "indent": indent_spaces,
                        }
                    )

        task_tree: list[dict] = []
        stack: list[tuple[int, dict]] = []

        for item in flat_tasks:
            indent = item["indent"]

            while stack and stack[-1][0] >= indent:
                stack.pop()

            if stack:
                stack[-1][1]["children"].append(item)
            else:
                task_tree.append(item)

            stack.append((indent, item))

        return {
            "bullets": flat_bullets,
            "tasks": task_tree,
        }

    def parse_tasks_to_tree(
        self,
        tasks: list[dict],
    ) -> list[dict]:
        """
        タスク本文からtag/minutes/start_timeを抽出する。

        重要:
        旧実装と同じく、childrenは再帰解析せずそのまま保持する。
        これにより「メールを読む」のような子タスク本文を失わない。
        """
        tree: list[dict] = []

        for item in tasks:
            text = item.get("text", "")
            parsed = MarkdownUtils.parse_tag_time_line_with_start(
                text
            )

            if parsed:
                children = item.get("children", [])

                tree.append(
                    {
                        "tag": parsed["tag"],
                        "minutes": parsed["minutes"],
                        "start_time": parsed["start_time"],
                        "children": children,
                    }
                )

        return tree

    def get_heading_task_tree(
        self,
        target_heading: str,
    ) -> list[dict] | None:
        """
        指定見出しのタスクツリーを取得する。

        旧APIの「タスクが存在しなければ []」を維持する。
        解析対象そのものが見つからない場合も、旧実装に合わせて
        空リストを返す。
        """
        nested_lists = self.extract_nested_lists(target_heading)
        tasks = nested_lists.get("tasks", [])
        return self.parse_tasks_to_tree(tasks)


class NoteGenerator:
    """ノート自動生成・テンプレート適用を管理するクラス。"""

    def __init__(self, vault: Vault):
        self.vault = vault

    def _resolve_template_path(
        self,
        template_spec: TemplateSpec,
        target_date: datetime,
    ) -> str:
        if isinstance(template_spec, str):
            template_path = template_spec

        elif isinstance(template_spec, dict):
            weekday = target_date.strftime("%A").upper()
            template_path = (
                template_spec.get(weekday)
                or template_spec.get("DEFAULT")
            )

        elif callable(template_spec):
            template_path = template_spec(target_date)

        else:
            raise ValueError(
                f"無効なtemplate_specの型です: "
                f"{type(template_spec)}"
            )

        if not template_path or not os.path.exists(template_path):
            raise FileNotFoundError(
                f"テンプレートファイルが見つかりません: "
                f"{template_path}"
            )

        return template_path

    def _create_from_template(
        self,
        relative_path: str,
        template_path: str,
        context: dict,
        target_date: datetime,
    ) -> bool:
        full_path = (
            relative_path
            if os.path.isabs(relative_path)
            else os.path.join(
                self.vault.target_dir, relative_path
            )
        )

        if os.path.exists(full_path):
            return False

        parent = os.path.dirname(full_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(template_path, "r", encoding="utf-8") as f:
            rendered = Template(f.read()).render(**context)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        note = self.vault.get_note(full_path)
        note.set_created_date(target_date)

        return True

    def create_daily_note(
        self,
        output_dir: str,
        target_date: datetime,
        template_spec: TemplateSpec,
    ) -> bool:
        file_name = (
            f"{target_date.strftime('%Y-%m-%d')}.md"
        )
        relative_path = os.path.join(
            output_dir, file_name
        )

        template_path = self._resolve_template_path(
            template_spec,
            target_date,
        )

        context = {
            "date": target_date.strftime("%Y-%m-%d"),
            "weekday": target_date.strftime("%A"),
        }

        if self._create_from_template(
            relative_path,
            template_path,
            context,
            target_date,
        ):
            note = self.vault.get_note(relative_path)
            note.append_to_heading(
                "Google Calender",
                MarkdownUtils.generate_google_calendar_link_text(
                    target_date
                ),
            )
            return True

        return False

    def batch_create_dailies(
        self,
        output_dir: str,
        start_date: datetime,
        days_count: int,
        template_spec: TemplateSpec,
    ) -> int:
        """複数日分のデイリーノートを一括作成する。"""
        created_count = 0

        for i in range(days_count):
            target_date = start_date + timedelta(days=i)

            if self.create_daily_note(
                output_dir,
                target_date,
                template_spec,
            ):
                created_count += 1

        return created_count

    def create_weekly_note(
        self,
        output_dir: str,
        target_date: datetime,
        template_path: str,
        plan_dir: Optional[str] = None,
        start_of_week: str = "monday",
    ) -> bool:
        """ウィークリーノートを作成し関連リンクを挿入する。"""
        (
            start_date,
            end_date,
            year,
            week_num,
        ) = MarkdownUtils.calculate_week_range(
            target_date,
            start_of_week,
        )

        file_name = f"{year}-W{week_num:02d}.md"
        relative_path = os.path.join(
            output_dir, file_name
        )

        context = {
            "year": year,
            "week": week_num,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }

        if not self._create_from_template(
            relative_path,
            template_path,
            context,
            target_date,
        ):
            return False

        note = self.vault.get_note(relative_path)

        note.append_to_heading(
            "デイリーノート",
            MarkdownUtils.generate_dailynote_links(
                start_date,
                end_date,
            ),
        )

        if plan_dir:
            plan_path = (
                plan_dir
                if os.path.isabs(plan_dir)
                else os.path.join(
                    self.vault.target_dir,
                    plan_dir,
                )
            )

            plan_vault = Vault(plan_path)
            plan_notes = plan_vault.find_notes_by_keyword(
                keyword="計画",
                extension="md",
                recursive=False,
            )

            plan_titles = [
                os.path.splitext(
                    os.path.basename(n.file_path)
                )[0]
                for n in plan_notes
            ]

            plan_links = (
                MarkdownUtils.generate_plan_note_links(
                    plan_titles,
                    year,
                    week_num,
                )
            )

            if plan_links:
                note.append_to_heading(
                    "計画ノート",
                    plan_links,
                )

        return True
