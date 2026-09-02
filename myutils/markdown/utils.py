from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class MarkdownUtils:
    """Markdown/Obsidian固有の純粋なユーティリティ群。"""

    @staticmethod
    def format_obsidian_link(title: str) -> str:
        """Obsidianの埋め込みリンク形式へ整形する。"""
        return f"![[{title.strip()}]]"

    @staticmethod
    def parse_vocabulary_line(line: str) -> dict | None:
        """「単語 : 意味」形式の行を辞書へ変換する。"""
        cleaned = re.sub(
            r"^[\s\\\-*+\d\\.]+",
            "",
            line,
        ).strip()

        for separator in (":", "："):
            if separator in cleaned:
                word, meaning = cleaned.split(
                    separator,
                    1,
                )
                return {
                    "word": word.strip(),
                    "meaning": meaning.strip(),
                }

        return None

    @staticmethod
    def _parse_time_str_to_minutes(
        time_str: str,
    ) -> Optional[int]:
        """時間表記を分数へ変換する。"""
        time_str = time_str.strip()

        match = re.fullmatch(
            r"(\d+(?:\.\d+)?)時間",
            time_str,
        )
        if match:
            return int(float(match.group(1)) * 60)

        match = re.fullmatch(
            r"(\d+)時間半",
            time_str,
        )
        if match:
            return int(match.group(1)) * 60 + 30

        match = re.fullmatch(
            r"(?:(\d+)時間)?\s*(?:(\d+)分)?",
            time_str,
        )
        if match and (match.group(1) or match.group(2)):
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            return hours * 60 + minutes

        return None

    @staticmethod
    def parse_tag_time_line(
        text: str,
    ) -> dict | None:
        """
        「タグ: 時間」を解析する旧API。

        例:
          運動: 30分
          読書: 1時間半
          作業: 1時間30分
        """
        if not text:
            return None

        match = re.search(
            r"^(.*?):\s*(.+)$",
            text.strip(),
        )
        if not match:
            return None

        tag = match.group(1).strip()
        time_str = match.group(2).strip()

        minutes = (
            MarkdownUtils._parse_time_str_to_minutes(
                time_str
            )
        )
        if minutes is None:
            return None

        return {
            "tag": tag,
            "minutes": minutes,
        }

    @staticmethod
    def parse_tag_time_line_with_start(
        text: str,
    ) -> Optional[Dict[str, Any]]:
        """
        タスク文字列からtag/minutes/start_timeを抽出する。

        例:
          - [ ] 運動: 30分 @18:00
          - [ ] 読書: 1時間半 @21:30
          アニメ鑑賞: 1.5時間
        """
        if not text:
            return None

        clean_text = re.sub(
            r"^[\s\t]*[-*+]\s*(?:\[[ xX]\]\s*)?",
            "",
            text,
        ).strip()

        start_time = None
        time_match = re.search(
            r"\s*@(\d{1,2}:\d{2})$",
            clean_text,
        )

        if time_match:
            start_time = time_match.group(1)
            clean_text = clean_text[
                :time_match.start()
            ].strip()

        tag_time_match = re.search(
            r"^(.*?):\s*(.+)$",
            clean_text,
        )
        if not tag_time_match:
            return None

        minutes = (
            MarkdownUtils._parse_time_str_to_minutes(
                tag_time_match.group(2).strip()
            )
        )
        if minutes is None:
            return None

        return {
            "tag": tag_time_match.group(1).strip(),
            "minutes": minutes,
            "start_time": start_time,
        }

    @staticmethod
    def calculate_week_range(
        target_date: datetime,
        start_of_week: str = "monday",
    ):
        """週の開始日・終了日・年・週番号を計算する。"""
        if start_of_week == "monday":
            start_date = (
                target_date
                - timedelta(days=target_date.weekday())
            )
        else:
            start_date = (
                target_date
                - timedelta(
                    days=(target_date.weekday() + 1) % 7
                )
            )

        end_date = start_date + timedelta(days=6)
        year, week_num, _ = target_date.isocalendar()

        return (
            start_date,
            end_date,
            year,
            week_num,
        )

    @staticmethod
    def generate_google_calendar_link_text(
        target_date=None,
    ) -> str:
        """GoogleカレンダーへのMarkdownリンク文字列を生成する。"""
        if target_date is None:
            target_date = datetime.now()

        date_display = target_date.strftime(
            "%Y/%m/%d"
        )

        calendar_url = (
            "https://calendar.google.com/calendar/u/0/r/week/"
            f"{target_date.year}/"
            f"{target_date.month}/"
            f"{target_date.day}"
        )

        return (
            f"[{date_display}のリンク]"
            f"({calendar_url})"
        )

    @staticmethod
    def generate_dailynote_links(
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """指定期間のデイリーノートリンクを改行区切りで生成する。"""
        links = []
        current_date = start_date

        while current_date <= end_date:
            links.append(
                f"[[{current_date.strftime('%Y-%m-%d')}]]"
            )
            current_date += timedelta(days=1)

        return "\n".join(links)

    @staticmethod
    def generate_plan_note_links(
        plan_file_titles: list,
        year: int,
        week_num: int,
    ) -> str:
        """指定週の計画ノートリンクを生成する。"""
        week_str = f"{year}-W{week_num:02d}"

        links = [
            f"[[{file_title}#{week_str}]]"
            for file_title in plan_file_titles
        ]

        return "\n".join(links)
