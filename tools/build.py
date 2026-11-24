"""Check Python and browser entry points without generating build artifacts."""
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.version_info < (3, 11):
        raise SystemExit('构建检查需要 Python 3.11 或更新版本。')
    sources = sorted([*ROOT.glob('ringtrace/*.py'), *ROOT.glob('tools/*.py')])
    for path in sources:
        compile(path.read_bytes(), str(path), 'exec')
    modules = sorted((ROOT / 'web').rglob('*.mjs'))
    node = shutil.which('node')
    if not node:
        raise SystemExit('构建检查需要 Node.js。')
    for path in modules:
        subprocess.run([node, '--check', str(path)], check=True)
    with sqlite3.connect(':memory:') as connection:
        connection.executescript((ROOT / 'ringtrace/schema.sql').read_text(encoding='utf-8'))
        if connection.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise SystemExit('SQLite 结构检查失败。')
    print(f'构建检查通过：{len(sources)} 个 Python 文件，{len(modules)} 个浏览器 ES 模块，SQLite {sqlite3.sqlite_version}。')


if __name__ == '__main__':
    main()
