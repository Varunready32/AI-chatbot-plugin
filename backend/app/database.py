from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from .config import get_settings


@contextmanager
def get_connection():
    conn = psycopg.connect(get_settings().database_url, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()
