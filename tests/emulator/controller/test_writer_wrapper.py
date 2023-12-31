from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from nicett6.emulator.controller.writer_manager import WriterWrapper


class TestWriterWrapper(IsolatedAsyncioTestCase):
    MSG: str = "TEST"
    EXPECTED: bytes = b"TEST\r\n"

    async def test_write_msg(self) -> None:
        writer = AsyncMock()
        ww = WriterWrapper(writer)
        await ww.write_msg(self.MSG)
        writer.write.assert_called_once_with(self.EXPECTED)
        writer.drain.assert_awaited_once_with()
        self.assertTrue(ww.ok)

    async def test_connection_lost(self) -> None:
        msg: str = "TEST"
        writer = AsyncMock()
        writer.write = MagicMock(side_effect=ConnectionResetError("Connection Reset"))
        ww = WriterWrapper(writer)
        await ww.write_msg(self.MSG)
        self.assertFalse(ww.ok)
