"""Fail a GitHub Actions check when the automated public feeds need attention."""
from datetime import datetime, timedelta
import json
from pathlib import Path
from news_time import news_now


def health_issues(report, services, now):
    issues = []
    if report.get('status') not in ('ok','degraded'):
        issues.append('Roboti i lajmeve nuk ka raport të suksesshëm.')
    try:
        finished = datetime.fromisoformat(report['finished_at'].replace('Z','+00:00'))
        if finished.tzinfo is None or now - finished > timedelta(minutes=90):
            issues.append('Roboti nuk ka përfunduar prej më shumë se 90 minutash.')
    except (KeyError, ValueError, TypeError):
        issues.append('Raporti i robotit nuk ka datë të vlefshme.')
    if any(source.get('status') == 'error' for source in report.get('sources',[])):
        issues.append('Të paktën një burim RSS ka dështuar.')
    # Allow one hour after 21:30 for queued GitHub runners and collection.
    expected = now.date() if (now.hour,now.minute) >= (22,30) else now.date() - timedelta(days=1)
    for key, name in [('keds','KEDS'),('weather','Meteo Kosova')]:
        source = services.get(key,{})
        if source.get('status') != 'ok' or not source.get('collected_on') or source['collected_on'] < expected.isoformat():
            issues.append(f'{name}: mungon përditësimi i fundit i mbrëmjes ose burimi ka dështuar.')
    return issues


if __name__ == '__main__':
    try:
        report = json.loads(Path('bot-status.json').read_text(encoding='utf-8'))
        services = json.loads(Path('daily-services.json').read_text(encoding='utf-8'))
        issues = health_issues(report, services, news_now())
    except (OSError, ValueError, TypeError):
        issues = ['Skedarët e gjendjes mungojnë ose nuk lexohen.']
    for issue in issues:
        print('::error::' + issue)
    if issues:
        raise SystemExit(1)
    print('Lajmet, KEDS dhe moti kanë përditësime të vlefshme.')
