from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import daily_services as daily
from news_time import NEWS_TIMEZONE


def local(year=2026, month=11, day=14, hour=21, minute=30):
    return datetime(year, month, day, hour, minute, tzinfo=NEWS_TIMEZONE)


class DailyServiceTests(unittest.TestCase):
    def test_schedule_handles_winter_summer_and_once_per_day(self):
        for now in [datetime(2026, 11, 14, 20, 30, tzinfo=timezone.utc),
                    datetime(2026, 7, 14, 19, 30, tzinfo=timezone.utc)]:
            with self.subTest(now=now), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / 'daily.json'
                with patch.object(daily, 'collect_keds', return_value={'notices': []}) as keds, patch.object(daily, 'collect_weather', return_value={'forecasts': []}) as weather:
                    self.assertTrue(daily.update_services(now, target))
                    self.assertFalse(daily.update_services(now, target))
                    keds.assert_called_once(); weather.assert_called_once()
                    self.assertEqual(json.loads(target.read_text())['keds']['collected_on'], now.date().isoformat())
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(daily.update_services(local(hour=21, minute=29), Path(folder) / 'none.json'))

    def test_daytime_refresh_does_not_suppress_evening_run(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'daily.json'
            with patch.object(daily, 'collect_keds', return_value={}) as keds, patch.object(daily, 'collect_weather', return_value={}):
                self.assertTrue(daily.update_services(local(hour=12), target, force=True))
                self.assertIsNone(json.loads(target.read_text())['keds']['collected_on'])
                self.assertTrue(daily.update_services(local(), target))
                self.assertEqual(keds.call_count, 2)

    def test_failure_preserves_last_good_data_and_retries_only_failed_source(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'daily.json'
            target.write_text(json.dumps({'keds': {'collected_on': '2026-11-13', 'notices': ['kept']}}))
            with patch.object(daily, 'collect_keds', side_effect=TimeoutError('private details')), patch.object(daily, 'collect_weather', return_value={'forecasts': []}):
                daily.update_services(local(), target)
            data = json.loads(target.read_text())
            self.assertEqual(data['keds']['notices'], ['kept'])
            self.assertEqual(data['keds']['status'], 'error')
            self.assertNotIn('private details', target.read_text())
            with patch.object(daily, 'collect_keds', return_value={'notices': ['new']}) as keds, patch.object(daily, 'collect_weather') as weather:
                daily.update_services(local(), target)
                keds.assert_called_once(); weather.assert_not_called()

    def test_keds_covers_all_regions_and_four_future_days(self):
        regions = ''.join(f'<li data-districtid="{i}">Region {i}</li>' for i in range(1, 8))
        calls = []
        def fetch(url, body=None):
            if body is None:
                return regions + 'GetNetworkWorksByFilters'
            calls.append(body)
            query = daily.urllib.parse.parse_qs(body.decode())
            date = datetime(2026, int(query['month'][0]), int(query['day'][0]), tzinfo=NEWS_TIMEZONE)
            return json.dumps({'Date': f'/Date({int(date.timestamp()*1000)})/', 'Description': {'Description': '<p>Ora 09:00–12:00</p><p>Vendet: A &amp; B</p>'}})
        data = daily.collect_keds(local(), fetch)
        self.assertEqual(len(calls), 28)
        self.assertEqual(data['notices'][0]['text'], 'Ora 09:00–12:00\nVendet: A & B')
        # Endpoint responses from the wrong year must not be published.
        with self.assertRaises(ValueError):
            daily.collect_keds(local(month=12, day=30), fetch)

    def test_keds_null_is_no_notice_but_invalid_json_is_failure(self):
        page = ''.join(f'<li data-districtid="{i}">Rajoni {i}</li>' for i in range(1, 8)) + 'GetNetworkWorksByFilters'
        data = daily.collect_keds(local(), lambda url, body=None: page if body is None else 'null')
        self.assertEqual(len(data['notices']), 28)
        self.assertEqual(data['dates'], ['2026-11-15','2026-11-16','2026-11-17','2026-11-18'])
        self.assertTrue(all(item['status'] == 'none' for item in data['notices']))
        empty = daily.collect_keds(local(), lambda url, body=None: page if body is None else '')
        self.assertTrue(all(item['status'] == 'none' for item in empty['notices']))
        with self.assertRaises(json.JSONDecodeError):
            daily.collect_keds(local(), lambda url, body=None: page if body is None else '<html>error</html>')

    def test_weather_filters_unrelated_news_and_keeps_forecast_date(self):
        feed = '''<rss><channel><item><title>Kuriozitete</title></item>
          <item><title>Parashikimi i motit për të dielën, 15.11.2026</title>
          <link>https://www.meteokosova.com/forecast/</link><pubDate>Sat, 14 Nov 2026 19:00:00 +0000</pubDate>
          <description>&lt;p&gt;Mot me shi.&lt;/p&gt;The post boilerplate</description></item></channel></rss>'''
        result = daily.collect_weather(local(), lambda url: feed)
        self.assertEqual(len(result['forecasts']), 1)
        self.assertEqual(result['forecasts'][0]['date'], '2026-11-15')
        self.assertEqual(result['forecasts'][0]['excerpt'], 'Mot me shi…')
        with self.assertRaises(ValueError):
            daily.collect_weather(local(), lambda url: feed.replace('www.meteokosova.com/forecast', 'evil.example/forecast'))

    def test_corrupt_snapshot_is_never_erased(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'daily.json'
            path.write_text('{broken')
            with self.assertRaises(json.JSONDecodeError): daily.update_services(local(), path)
            self.assertEqual(path.read_text(), '{broken')


if __name__ == '__main__':
    unittest.main()
