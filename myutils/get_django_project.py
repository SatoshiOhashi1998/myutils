import os
import re
import argparse

TARGET_DIR = r'C:\Users\user\PycharmProjects\MyUtilProject\MyApp\vtuber-music\video_player'


def find_apps(project_dir=TARGET_DIR):
    """__init__.py が存在するすべての再帰ディレクトリをアプリとみなす"""
    apps = []
    for root, dirs, files in os.walk(project_dir):
        if '__init__.py' in files:
            apps.append(root)
    return apps


def gather_app_files(app_paths):
    """各アプリの urls.py, views.py, models.py を収集"""
    target_files = ['urls.py', 'views.py', 'models.py']
    gathered_code = ""
    for app_path in app_paths:
        app_name = os.path.relpath(app_path)  # 相対パスで表示
        gathered_code += f"\n# ===== App: {app_name} =====\n"
        for filename in target_files:
            file_path = os.path.join(app_path, filename)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    gathered_code += f"\n# --- File: {filename} ---\n"
                    gathered_code += f.read() + "\n"
            else:
                gathered_code += f"\n# --- File: {filename} not found ---\n"
    return gathered_code


def find_settings_py(project_dir=TARGET_DIR):
    """settings.pyを再帰的に探索"""
    for root, dirs, files in os.walk(project_dir):
        if 'settings.py' in files:
            return os.path.join(root, 'settings.py')
    return None


def extract_key_settings(settings_path):
    """settings.pyから主要な設定を抽出"""
    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = {
        'INSTALLED_APPS': re.search(r'INSTALLED_APPS\s*=\s*\[.*?\]', content, re.DOTALL),
        'AUTH_USER_MODEL': re.search(r'AUTH_USER_MODEL\s*=\s*[\'"].*?[\'"]', content),
        'TEMPLATES': re.search(r'TEMPLATES\s*=\s*\[.*?\]', content, re.DOTALL),
        'DATABASES': re.search(r'DATABASES\s*=\s*\{.*?\}', content, re.DOTALL),
        'LANGUAGE_CODE': re.search(r'LANGUAGE_CODE\s*=\s*[\'"].*?[\'"]', content),
        'TIME_ZONE': re.search(r'TIME_ZONE\s*=\s*[\'"].*?[\'"]', content),
    }

    result = "# ===== File: settings.py =====\n\n"
    for key, match in sections.items():
        if match:
            result += f"{match.group()}\n\n"
        else:
            result += f"# {key} not found\n\n"
    return result


def gather_all_templates(project_dir=TARGET_DIR):
    """プロジェクト全体のtemplatesディレクトリを再帰的に探索し、.htmlファイルを収集"""
    gathered = "# ===== Templates =====\n\n"

    for root, dirs, files in os.walk(project_dir):
        if os.path.basename(root) == "templates":
            for dirpath, _, filenames in os.walk(root):
                for file in filenames:
                    if file.endswith(".html"):
                        full_path = os.path.join(dirpath, file)
                        rel_path = os.path.relpath(full_path, project_dir)
                        gathered += f"\n# --- Template: {rel_path} ---\n"
                        with open(full_path, 'r', encoding='utf-8') as f:
                            gathered += f.read() + "\n"

    if gathered.strip() == "# ===== Templates =====":
        return "# templates directory or HTML files not found\n"

    return gathered


def main():
    # python get_django_project.py --project-dir <プロジェクトのパス> [--settings] [--code] [--templates]
    parser = argparse.ArgumentParser(description="Djangoプロジェクトの構成を抽出")
    parser.add_argument('--project-dir', required=True, help='Djangoプロジェクトのルートディレクトリ（manage.pyがある場所）')
    parser.add_argument('--settings', action='store_true', help='settings.pyの要点を抽出')
    parser.add_argument('--code', action='store_true', help='各アプリのurls.py/views.py/models.pyを抽出（再帰的）')
    parser.add_argument('--templates', action='store_true', help='templates/ディレクトリのテンプレートを抽出')

    args = parser.parse_args()
    output = ""

    if args.settings:
        settings_path = find_settings_py(args.project_dir)
        if settings_path:
            output += extract_key_settings(settings_path)
        else:
            output += "# ===== File: settings.py not found =====\n\n"

    if args.code:
        app_paths = find_apps(args.project_dir)
        output += gather_app_files(app_paths)

    if args.templates:
        output += gather_all_templates()

    print(output)


if __name__ == "__main__":
    main()
