"""Publication times use Kosovo's civil time, including DST changes."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Europe/Belgrade is the IANA zone covering Kosovo.
NEWS_TIMEZONE = ZoneInfo("Europe/Belgrade")


def news_now():
    return datetime.now(NEWS_TIMEZONE)


def parse_publication_time(value):
    """Supabase timestamps are UTC when no explicit offset is supplied."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(NEWS_TIMEZONE)
