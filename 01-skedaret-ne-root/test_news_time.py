import unittest
from news_time import parse_publication_time


class PublicationTimeTests(unittest.TestCase):
    def test_winter_and_summer(self):
        for value, expected in [
            ("2026-01-15T12:00:00Z", "15/01/2026 13:00 +0100"),
            ("2026-07-15T12:00:00Z", "15/07/2026 14:00 +0200"),
            ("2026-11-10T12:00:00+00:00", "10/11/2026 13:00 +0100"),
            ("2026-07-15T14:00:00+02:00", "15/07/2026 14:00 +0200"),
            ("2026-01-15T12:00:00", "15/01/2026 13:00 +0100"),
        ]:
            with self.subTest(value=value):
                self.assertEqual(parse_publication_time(value).strftime("%d/%m/%Y %H:%M %z"), expected)

    def test_spring_transition(self):
        self.assertEqual(parse_publication_time("2026-03-29T00:59:00Z").strftime("%H:%M %z"), "01:59 +0100")
        self.assertEqual(parse_publication_time("2026-03-29T01:00:00Z").strftime("%H:%M %z"), "03:00 +0200")

    def test_autumn_repeated_hour(self):
        before = parse_publication_time("2026-10-25T00:30:00Z")
        after = parse_publication_time("2026-10-25T01:30:00Z")
        self.assertEqual(before.strftime("%H:%M %z"), "02:30 +0200")
        self.assertEqual(after.strftime("%H:%M %z"), "02:30 +0100")
        self.assertEqual(after.fold, 1)


if __name__ == "__main__":
    unittest.main()
