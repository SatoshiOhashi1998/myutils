# note_processor.py
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Callable
from jinja2 import Template

from .vault import Vault, Note
from .utils import calculate_week_range, parse_tag_time_line_with_start

class NoteParser:
    """Markdownの解析やリスト・タスクの抽出を行うクラス"""
    def __init__(self, note: 'Note'):
        self.note = note

    def get_headings(self) -> list[dict]:
        headings = []
        for line in self.note.content.splitlines():
            if line.startswith("#"):
                headings.append({
                    "level": len(line.split()[0]),
                    "text": line.lstrip("#").strip()
                })
        return headings

    def extract_lists(self, target_heading: str = None) -> dict:
        content = self.note.get_content_by_heading(target_heading) if target_heading else self.note.content
        if not content:
            return {"bullets": [], "numbered": [], "tasks": []}

        bullet_list, numbered_list, task_list = [], [], []
        for line in content.splitlines():
            stripped = line.strip()
            task_match = re.match(r"^-\s*\[([ xX])\]\s+(.*)", stripped)
            if task_match:
                task_list.append({"text": task_match.group(2), "completed": task_match.group(1).strip() != ""})
                continue
            bullet_match = re.match(r"^[-*+]\s+(.*)", stripped)
            if bullet_match:
                bullet_list.append(bullet_match.group(1))
                continue
            numbered_match = re.match(r"^\d+\.\s+(.*)", stripped)
            if numbered_match:
                numbered_list.append(numbered_match.group(1))

        return {"bullets": bullet_list, "numbered": numbered_list, "tasks": task_list}

    def extract_nested_lists(self, target_heading: str = None, tab_size: int = 4) -> dict:
        """インデント深さを保持してツリー構造のリストを抽出する"""
        content = self.note.get_content_by_heading(target_heading) if target_heading else self.note.content
        if not content:
            return {"bullets": [], "tasks": []}

        flat_tasks = []
        flat_bullets = []

        for line in content.splitlines():
            if not line.strip():
                continue

            expanded_line = line.expandtabs(tab_size)
            indent_spaces = len(expanded_line) - len(expanded_line.lstrip(" "))
            stripped_line = line.strip()

            task_match = re.match(r"^[-*+]\s+\[([ xX])\](?:\s+(.*))?$", stripped_line)
            if task_match:
                text = task_match.group(2) or ""
                if text.strip():
                    flat_tasks.append({
                        "text": text.strip(),
                        "completed": task_match.group(1).strip() != "",
                        "indent": indent_spaces,
                        "children": []
                    })
                continue

            bullet_match = re.match(r"^[-*+]\s+(.*)", stripped_line)
            if bullet_match:
                text = bullet_match.group(1).strip()
                if text:
                    flat_bullets.append({"text": text, "indent": indent_spaces})

        task_tree = []
        stack = []

        for item in flat_tasks:
            indent = item["indent"]
            while stack and stack[-1][0] >= indent:
                stack.pop()

            if stack:
                stack[-1][1]["children"].append(item)
            else:
                task_tree.append(item)

            stack.append((indent, item))

        return {"bullets": flat_bullets, "tasks": task_tree}

    def parse_tasks_to_tree(self, tasks: list[dict]) -> list[dict]:
        """ツリー構造のタスクリストから詳細メタデータを抽出する"""
        tree = []
        for item in tasks:
            text = item.get("text", "")
            parsed = parse_tag_time_line_with_start(text)
            
            if parsed:
                node = {
                    "tag": parsed["tag"],
                    "minutes": parsed["minutes"],
                    "start_time": parsed["start_time"],
                    "children": self.parse_tasks_to_tree(item.get("children", [])) if item.get("children") else item.get("children", [])
                }
                tree.append(node)
        return tree

    def get_heading_task_tree(self, target_heading: str) -> list[dict] | None:
        """指定した見出しから、構造化されたタスクツリーを取得する"""
        nested_lists = self.extract_nested_lists(target_heading)
        tasks = nested_lists.get("tasks", [])
        if not tasks:
            return None
        return self.parse_tasks_to_tree(tasks)


class NoteGenerator:
    """ノートの自動生成・テンプレート適用を管理するクラス"""
    def __init__(self, vault: 'Vault'):
        self.vault = vault

    def _resolve_template_path(self, template_spec, target_date: datetime) -> str:
        if isinstance(template_spec, str):
            return template_spec
        elif isinstance(template_spec, dict):
            weekday = target_date.strftime('%A').upper()
            return template_spec.get(weekday) or template_spec.get('DEFAULT')
        elif callable(template_spec):
            return template_spec(target_date)
        raise ValueError("無効な template_spec の型です")

    def _create_from_template(self, relative_path: str, template_path: str, context: dict, target_date: datetime) -> bool:
        full_path = os.path.join(self.vault.target_dir, relative_path)
        if os.path.exists(full_path):
            return False

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(template_path, 'r', encoding='utf-8') as f:
            rendered = Template(f.read()).render(**context)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(rendered)
            
        note = self.vault.get_note(relative_path)
        note.set_created_date(target_date)
        return True

    def create_daily_note(self, output_dir: str, target_date: datetime, template_spec) -> bool:
        file_name = f"{target_date.strftime('%Y-%m-%d')}.md"
        relative_path = os.path.join(output_dir, file_name)
        template_path = self._resolve_template_path(template_spec, target_date)
        context = {"date": target_date.strftime('%Y-%m-%d'), "weekday": target_date.strftime('%A')}

        if self._create_from_template(relative_path, template_path, context, target_date):
            note = self.vault.get_note(relative_path)
            cal_url = f"https://calendar.google.com/calendar/u/0/r/week/{target_date.year}/{target_date.month}/{target_date.day}"
            cal_link = f"[{target_date.strftime('%Y/%m/%d')}のリンク]({cal_url})"
            note.append_to_heading('Google Calender', cal_link)
            return True
        return False

    def batch_create_dailies(self, output_dir: str, start_date: datetime, days_count: int, template_spec) -> int:
        """複数日分のデイリーノートを一括作成する"""
        created_count = 0
        for i in range(days_count):
            target_date = start_date + timedelta(days=i)
            if self.create_daily_note(output_dir, target_date, template_spec):
                created_count += 1
        return created_count

    def create_weekly_note(self, output_dir: str, target_date: datetime, template_path: str, plan_dir: Optional[str] = None, start_of_week: str = "monday") -> bool:
        """ウィークリーノートを作成し、デイリー・計画リンクを挿入する"""
        start_date, end_date, year, week_num = calculate_week_range(target_date, start_of_week)
        file_name = f"{year}-W{week_num:02d}.md"
        relative_path = os.path.join(output_dir, file_name)
        
        context = {
            "year": year,
            "week": week_num,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }
        
        if not self._create_from_template(relative_path, template_path, context, target_date):
            return False
            
        note = self.vault.get_note(relative_path)
        
        # デイリーノートのリンクを挿入
        daily_links = []
        current_date = start_date
        while current_date <= end_date:
            daily_links.append(f"[[{current_date.strftime('%Y-%m-%d')}]]")
            current_date += timedelta(days=1)
        note.append_to_heading('デイリーノート', "\n".join(daily_links))
        
        # 計画ノートのリンクを挿入
        if plan_dir:
            plan_full_path = os.path.join(self.vault.target_dir, plan_dir) if not os.path.isabs(plan_dir) else plan_dir
            plan_vault = Vault(plan_full_path)
            plan_notes = plan_vault.find_notes_by_keyword(keyword="計画")
            if plan_notes:
                week_str = f"{year}-W{week_num:02d}"
                plan_links = [f"[[{os.path.splitext(os.path.basename(n.file_path))[0]}#{week_str}]]" for n in plan_notes]
                note.append_to_heading('計画ノート', "\n".join(plan_links))

        return True
