"""Inspect the current repository's photos without running the news/AI/FB bot."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from image_health import audit_photos
from news_utils import load_news_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=30, choices=range(1, 51))
    args = parser.parse_args()
    news = load_news_file(ROOT / 'lajmet.json')
    audit_photos([n for n in news if not n.get('duplicate_of')], ROOT / 'image-health.json', limit=args.limit)
