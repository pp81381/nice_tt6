from nicett6.connection import TT6Reader, TT6Writer
from unittest.mock import AsyncMock, MagicMock


def make_mock_conn(reader_return_value):
    mock_reader = AsyncMock(name="reader")
    mock_reader.__aiter__.return_value = reader_return_value
    mock_reader.__class__ = TT6Reader

    mock_writer = AsyncMock(name="writer")
    mock_writer.__class__ = TT6Writer

    conn = AsyncMock()
    conn.add_reader = MagicMock(return_value=mock_reader)
    conn.get_writer = MagicMock(return_value=mock_writer)
    conn.remove_reader = MagicMock()
    conn.close = MagicMock()
    return conn
