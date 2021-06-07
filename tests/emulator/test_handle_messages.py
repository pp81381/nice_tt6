import asyncio
from nicett6.emulator.controller import TT6Controller
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch, call

RCV_EOL = b"\r"


class TestHandleMessages(IsolatedAsyncioTestCase):
    CMD1 = b"WEB_ON" + RCV_EOL
    CMD2 = b"CMD 01 02 03" + RCV_EOL

    async def test_handle_messages1(self):
        controller = TT6Controller(False)
        with patch(
            "nicett6.emulator.line_handler.LineHandler.handle_line"
        ) as handle_line:
            reader = AsyncMock(spec_set=asyncio.StreamReader)
            reader.readuntil.side_effect = [self.CMD1, self.CMD2, b""]
            writer = AsyncMock(spec_set=asyncio.StreamWriter)
            await controller.handle_messages(reader, writer)
            self.assertEqual(handle_line.await_count, 2)
            handle_line.assert_has_awaits([call(self.CMD1), call(self.CMD2)])
            writer.close.assert_called_once()

    async def test_handle_messages_with_newlines(self):
        ex = asyncio.IncompleteReadError(b"\n", None)
        controller = TT6Controller(False)
        with patch(
            "nicett6.emulator.line_handler.LineHandler.handle_line"
        ) as handle_line:
            reader = AsyncMock(spec_set=asyncio.StreamReader)
            reader.readuntil.side_effect = [self.CMD1, self.CMD2, ex]
            writer = AsyncMock(spec_set=asyncio.StreamWriter)
            await controller.handle_messages(reader, writer)
            self.assertEqual(handle_line.await_count, 2)
            handle_line.assert_has_awaits([call(self.CMD1), call(self.CMD2)])
            writer.close.assert_called_once()

    async def test_handle_messages_with_trailing_junk(self):
        ex = asyncio.IncompleteReadError(b"\njunk", None)
        controller = TT6Controller(False)
        with patch(
            "nicett6.emulator.line_handler.LineHandler.handle_line"
        ) as handle_line:
            reader = AsyncMock(spec_set=asyncio.StreamReader)
            reader.readuntil.side_effect = [self.CMD1, self.CMD2, ex]
            writer = AsyncMock(spec_set=asyncio.StreamWriter)
            with self.assertRaises(asyncio.IncompleteReadError):
                await controller.handle_messages(reader, writer)
            self.assertEqual(handle_line.await_count, 2)
            handle_line.assert_has_awaits([call(self.CMD1), call(self.CMD2)])
            writer.close.assert_called_once()
