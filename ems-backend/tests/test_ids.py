"""Row IDs must never collide, even when many requests are created at the same moment."""
import os
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("JWT_SECRET", "x" * 40)
os.environ.setdefault("SPREADSHEET_ID", "test")
os.environ.setdefault("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type":"service_account"}')

from sheets_client import new_id


def test_new_id_is_unique_under_concurrency():
    with ThreadPoolExecutor(max_workers=32) as pool:
        ids = list(pool.map(lambda _: new_id(), range(20_000)))
    assert len(set(ids)) == len(ids)


def test_new_id_is_a_plain_string_safe_for_sheets_and_urls():
    i = new_id()
    assert isinstance(i, str) and len(i) == 16
    assert i.isalnum()
