from asyncio import StreamWriter
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from nicett6.emulator.controller.writer_manager import WriterManager


class TestWriterManager(IsolatedAsyncioTestCase):
    async def test_add(self) -> None:
        writer1 = AsyncMock(spec_set=StreamWriter)
        writer2 = AsyncMock(spec_set=StreamWriter)
        wm = WriterManager()
        self.assertEqual(len(wm.writers), 0)
        wm = WriterManager()
        with wm.wrap_writer(writer1):
            self.assertEqual(len(wm.writers), 1)
            with wm.wrap_writer(writer2):
                self.assertEqual(len(wm.writers), 2)
            self.assertEqual(len(wm.writers), 1)
        self.assertEqual(len(wm.writers), 0)

    async def test_write_all(self) -> None:
        writer1 = AsyncMock(spec_set=StreamWriter)
        writer2 = AsyncMock(spec_set=StreamWriter)
        wm = WriterManager()
        with wm.wrap_writer(writer1):
            with wm.wrap_writer(writer2):
                msg: str = "TEST"
                expected: bytes = b"TEST\r\n"
                await wm.write_all(msg)
                writer1.write.assert_called_once_with(expected)
                writer2.write.assert_called_once_with(expected)
