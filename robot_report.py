"""Public-news diagnostics only; never serialize credentials or raw exceptions."""
from collections import Counter
import os
from news_time import news_now
from news_utils import load_news_file, write_json_atomic


class RunReport:
    def __init__(self):
        self.started_at = news_now().isoformat()
        self.sources = []
        self.events = []
        self.counts = Counter()

    def event(self, title, url, outcome, reason, **extra):
        self.counts[outcome] += 1
        self.events.append({'titulli': str(title or '')[:350], 'url': url or '', 'outcome': outcome, 'reason': reason, **extra})

    def finish(self, status, featured=None, error=None):
        path = 'bot-status.json'
        history = []
        previous_events = []
        try:
            import json
            with open(path, encoding='utf-8') as stream:
                previous = json.load(stream)
            history = previous.get('history', [])
            previous_events = previous.get('recent_events', [])
        except (OSError, ValueError, AttributeError):
            pass
        summary = {'started_at': self.started_at, 'finished_at': news_now().isoformat(), 'status': status, 'counts': dict(self.counts)}
        write_json_atomic(path, {**summary, 'schema_version': 1, 'sources': self.sources,
            'events': self.events[:200], 'featured': [{'titulli': n['titulli'], 'slug': n['slug'], 'reasons': n.get('selection_reasons', [])} for n in (featured or [])],
            'recent_events': ([{**event, 'run_at': self.started_at} for event in self.events[:200]] + previous_events)[:1000],
            'error_type': type(error).__name__ if error else None,
            'workflow_url': f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}" if os.environ.get('GITHUB_REPOSITORY') and os.environ.get('GITHUB_RUN_ID') else None,
            'history': ([summary]+history)[:20]})
