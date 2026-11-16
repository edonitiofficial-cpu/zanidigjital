from datetime import datetime,timedelta
import unittest
from monitor_health import health_issues
from news_time import NEWS_TIMEZONE


class HealthTests(unittest.TestCase):
    def test_stale_news_and_failed_source_are_detected(self):
        now=datetime(2026,11,14,21,45,tzinfo=NEWS_TIMEZONE)
        services={key:dict(status='ok',collected_on='2026-11-13') for key in ['keds','weather']}
        report=dict(status='ok',finished_at=now.isoformat(),sources=[])
        self.assertEqual(health_issues(report,services,now),[])
        report.update(finished_at=(now-timedelta(hours=2)).isoformat(),sources=[dict(status='error')])
        self.assertEqual(len(health_issues(report,services,now)),2)

    def test_evening_grace_period_and_source_failure(self):
        now=datetime(2026,7,14,22,29,tzinfo=NEWS_TIMEZONE)
        report=dict(status='ok',finished_at=now.isoformat())
        services={key:dict(status='ok',collected_on='2026-07-13') for key in ['keds','weather']}
        self.assertEqual(health_issues(report,services,now),[])
        self.assertEqual(len(health_issues(report,services,now+timedelta(minutes=1))),2)
        services['keds']=dict(status='error',collected_on='2026-07-14')
        services['weather']=dict(status='ok',collected_on='2026-07-14')
        self.assertEqual(len(health_issues(report,services,now)),1)
