"""Repair only a known malformed font-import remainder, preserving news text."""
from pathlib import Path
import re


def repair_style(text):
    return re.sub(r'(<style\b[^>]*>)\s*\d+(?:;\d+)*&display=swap[\x27\x22]?\)\s*;', r'\1', text)


def repair_files(root):
    root = Path(root)
    count = 0
    for path in [root / 'index.html', *(root / 'lajme').glob('*/index.html')]:
        original = path.read_text(encoding='utf-8')
        updated = repair_style(original)
        if updated != original:
            path.write_text(updated, encoding='utf-8')
            count += 1
    return count


if __name__ == '__main__':
    print(f'Font styles repaired: {repair_files(Path(__file__).resolve().parents[1])}')
