import os
import re
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Callable
from jinja2 import Template

from vault import Vault, Note

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
