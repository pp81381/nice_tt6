import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, call, patch

from nicett6.consts import RCV_EOL
from nicett6.emulator.controller.device_manager import DeviceManager
from nicett6.emulator.controller.handle_messages import handle_messages
from nicett6.emulator.controller.web_pos_manager import WebPosManager
from nicett6.emulator.controller.writer_manager import WriterManager


class TestHandleMessages(IsolatedAsyncioTestCase):
    CMD1 = b"WEB_ON" + RCV_EOL
    CMD2 = b"CMD 01 02 03" + RCV_EOL

    async def asyncSetUp(self):
        self.writer_manager = WriterManager()
        self.web_pos_manager = WebPosManager(self.writer_manager, False)
        self.device_manager = DeviceManager(self.web_pos_manager)
        self.server_controller = AsyncMock()

    async def test_handle_messages1(self):
        with patch(
            "nicett6.emulator.controller.line_handler.LineHandler.handle_line"
        ) as handle_line:
            reader = AsyncMock(spec_set=asyncio.StreamReader)
            reader.readuntil.side_effect = [self.CMD1, self.CMD2, b""]
            writer = AsyncMock(spec_set=asyncio.StreamWriter)
            await handle_messages(
                self.writer_manager,
                self.web_pos_manager,
                self.device_manager,
                self.server_controller,
                reader,
                writer,
            )
            self.assertEqual(handle_line.await_count, 2)
            handle_line.assert_has_awaits([call(self.CMD1), call(self.CMD2)])
            writer.close.assert_called_once()

    async def test_handle_messages_with_newlines(self):
        ex = asyncio.IncompleteReadError(b"\n", None)
        with patch(
            "nicett6.emulator.controller.line_handler.LineHandler.handle_line"
        ) as handle_line:
            reader = AsyncMock(spec_set=asyncio.StreamReader)
            reader.readuntil.side_effect = [self.CMD1, self.CMD2, ex]
            writer = AsyncMock(spec_set=asyncio.StreamWriter)
            await handle_messages(
                self.writer_manager,
                self.web_pos_manager,
                self.device_manager,
                self.server_controller,
                reader,
                writer,
            )
            self.assertEqual(handle_line.await_count, 2)
            handle_line.assert_has_awaits([call(self.CMD1), call(self.CMD2)])
            writer.close.assert_called_once()

    async def test_handle_messages_with_trailing_junk(self):
        ex = asyncio.IncompleteReadError(b"\njunk", None)
        with patch(
            "nicett6.emulator.controller.line_handler.LineHandler.handle_line"
        ) as handle_line:
            reader = AsyncMock(spec_set=asyncio.StreamReader)
            reader.readuntil.side_effect = [self.CMD1, self.CMD2, ex]
            writer = AsyncMock(spec_set=asyncio.StreamWriter)
            with self.assertRaises(asyncio.IncompleteReadError):
                await handle_messages(
                    self.writer_manager,
                    self.web_pos_manager,
                    self.device_manager,
                    self.server_controller,
                    reader,
                    writer,
                )
            self.assertEqual(handle_line.await_count, 2)
            handle_line.assert_has_awaits([call(self.CMD1), call(self.CMD2)])
            writer.close.assert_called_once()
