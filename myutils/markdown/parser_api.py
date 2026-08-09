import os
import re
from .core_reader import get_content_by_heading, get_sub_headings_by_heading, extract_lists_from_content

def extract_lists_from_heading(file_path, target_heading):
    base_name = os.path.basename(file_path)
    file_name = os.path.splitext(base_name)[0]
    content = get_content_by_heading(file_path, target_heading)
    lists = extract_lists_from_content(content) if content else {"bullets": [], "numbered": [], "tasks": []}
    return {"file_name": file_name, "heading": target_heading, "lists": lists}

def extract_lists_from_all_sub_headings(file_path, target_heading):
    sub_headings = get_sub_headings_by_heading(file_path, target_heading)
    return [extract_lists_from_heading(file_path, sh["text"]) for sh in sub_headings]

def parse_vocabulary_line(line):
    cleaned = re.sub(r"^[\s\-*+\d\.]+", "", line).strip()
    if ":" in cleaned:
        word, meaning = cleaned.split(":", 1)
    elif "：" in cleaned:
        word, meaning = cleaned.split("：", 1)
    else:
        return None
    return {"word": word.strip(), "meaning": meaning.strip()}
