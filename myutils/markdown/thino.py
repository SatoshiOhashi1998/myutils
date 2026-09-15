from __future__ import annotations

import os
from datetime import date, datetime, timedelta

from .note_processor import NoteParser
from .utils import MarkdownUtils
from .vault import Note


def collect_thino_links(
    daily_note_dir: str,
    target_date: date | datetime,
    start_of_week: str = "monday",
    thino_heading: str = "Thino",
) -> list[str]:
    """
    指定した週のデイリーノートからThinoの投稿見出しを取得し、
    Obsidianの見出しリンクとして返す。

    対象となるのは # Thino 配下の #### 見出しのみ。
    見出し以下の本文は解析しない。
    """
    if start_of_week not in ("monday", "sunday"):
        raise ValueError(
            "start_of_weekは'monday'または'sunday'を指定してください。"
        )

    if isinstance(target_date, datetime):
        target_date = target_date.date()

    start_date, end_date, _, _ = MarkdownUtils.calculate_week_range(
        datetime.combine(target_date, datetime.min.time()),
        start_of_week=start_of_week,
    )

    links = []

    current_date = start_date.date()

    while current_date <= end_date.date():
        file_name = f"{current_date:%Y-%m-%d}.md"
        file_path = os.path.join(daily_note_dir, file_name)

        if os.path.exists(file_path):
            note = Note(file_path)
            parser = NoteParser(note)

            headings = parser.get_sub_headings_by_heading(
                thino_heading
            )

            for heading in headings:
                if heading["level"] != 4:
                    continue

                links.append(
                    MarkdownUtils.format_obsidian_link(
                        f"{current_date:%Y-%m-%d}#{heading['text']}"
                    )
                )

        current_date += timedelta(days=1)

    return links
