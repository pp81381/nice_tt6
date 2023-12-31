import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from nicett6.command_code import CommandCode
from nicett6.consts import RCV_EOL
from nicett6.emulator.controller.line_handler import LineHandler
from nicett6.emulator.cover_emulator import TT6CoverEmulator
from nicett6.ttbus_device import TTBusDeviceAddress


class TestHandleWebOnCommands(IsolatedAsyncioTestCase):
    """Test the behaviour of handle_line for web_on commands with mock controller"""

    async def test_handle_web_on(self):
        line_bytes = b"WEB_ON" + RCV_EOL
        wrapped_writer = AsyncMock()
        web_pos_manager = AsyncMock()
        web_pos_manager.web_on = False
        device_manager = AsyncMock()
        server_controller = AsyncMock()
        line_handler = LineHandler(
            wrapped_writer,
            web_pos_manager,
            device_manager,
            server_controller,
        )
        await line_handler.handle_line(line_bytes)
        self.assertTrue(web_pos_manager.web_on)
        wrapped_writer.write_msg.assert_awaited_once_with(
            LineHandler.MSG_WEB_COMMANDS_ON
        )

    async def test_handle_web_on_err(self):
        line_bytes = b"WEB_ON BAD" + RCV_EOL
        wrapped_writer = AsyncMock()
        web_pos_manager = AsyncMock()
        web_pos_manager.web_on = False
        device_manager = AsyncMock()
        server_controller = AsyncMock()
        line_handler = LineHandler(
            wrapped_writer,
            web_pos_manager,
            device_manager,
            server_controller,
        )
        await line_handler.handle_line(line_bytes)
        self.assertFalse(web_pos_manager.web_on)
        wrapped_writer.write_msg.assert_awaited_once_with(
            LineHandler.MSG_INVALID_COMMAND_ERROR
        )

    async def test_handle_web_off(self):
        line_bytes = b"WEB_OFF" + RCV_EOL
        wrapped_writer = AsyncMock()
        web_pos_manager = AsyncMock()
        web_pos_manager.web_on = True
        device_manager = AsyncMock()
        server_controller = AsyncMock()
        line_handler = LineHandler(
            wrapped_writer,
            web_pos_manager,
            device_manager,
            server_controller,
        )
        await line_handler.handle_line(line_bytes)
        self.assertFalse(web_pos_manager.web_on)
        wrapped_writer.write_msg.assert_awaited_once_with(
            LineHandler.MSG_WEB_COMMANDS_OFF
        )

    async def test_handle_web_off_whitespace(self):
        line_bytes = b"\n WEB_OFF  " + RCV_EOL
        wrapped_writer = AsyncMock()
        web_pos_manager = AsyncMock()
        web_pos_manager.web_on = True
        device_manager = AsyncMock()
        server_controller = AsyncMock()
        line_handler = LineHandler(
            wrapped_writer,
            web_pos_manager,
            device_manager,
            server_controller,
        )
        await line_handler.handle_line(line_bytes)
        self.assertFalse(web_pos_manager.web_on)
        wrapped_writer.write_msg.assert_awaited_once_with(
            LineHandler.MSG_WEB_COMMANDS_OFF
        )

    async def test_handle_web_cmd_while_web_off(self):
        line_bytes = b"POS < 02 04 FFFF FFFF FF" + RCV_EOL
        wrapped_writer = AsyncMock()
        web_pos_manager = AsyncMock()
        web_pos_manager.web_on = False
        device_manager = AsyncMock()
        server_controller = AsyncMock()
        line_handler = LineHandler(
            wrapped_writer,
            web_pos_manager,
            device_manager,
            server_controller,
        )
        await line_handler.handle_line(line_bytes)
        wrapped_writer.write_msg.assert_awaited_once_with(
            LineHandler.MSG_INVALID_COMMAND_ERROR
        )

    async def test_handle_quit(self):
        line_bytes = b"QUIT" + RCV_EOL
        wrapped_writer = AsyncMock()
        web_pos_manager = AsyncMock()
        device_manager = AsyncMock()
        server_controller = AsyncMock()
        line_handler = LineHandler(
            wrapped_writer,
            web_pos_manager,
            device_manager,
            server_controller,
        )
        await line_handler.handle_line(line_bytes)
        server_controller.stop_server.assert_awaited_once_with()
        wrapped_writer.write_msg.assert_not_awaited()


class TestHandleMovementCommands(IsolatedAsyncioTestCase):
    """Test the behaviour of handle_line for movement commands using mock cover"""

    async def asyncSetUp(self):
        self.cover = AsyncMock(spec=TT6CoverEmulator)
        self.cover.tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.cover.name = "test_cover"
        self.wrapped_writer = AsyncMock()
        self.web_pos_manager = AsyncMock()
        self.web_pos_manager.web_on = False
        self.device_manager = AsyncMock()
        self.device_manager.lookup_device = MagicMock(return_value=self.cover)
        self.server_controller = AsyncMock()
        self.line_handler = LineHandler(
            self.wrapped_writer,
            self.web_pos_manager,
            self.device_manager,
            self.server_controller,
        )

    async def test_handle_move_up(self):
        line_bytes = b"CMD 02 04 05" + RCV_EOL
        await self.line_handler.handle_line(line_bytes)
        self.cover.move_up.assert_awaited_once_with()
        self.wrapped_writer.write_msg.assert_awaited_once_with("RSP 2 4 5")

    async def test_handle_read_hex_pos(self):
        line_bytes = b"CMD 02 04 45" + RCV_EOL
        percent_pos = PropertyMock(return_value=0xAB / 0xFF)
        type(self.cover).percent_pos = percent_pos
        await self.line_handler.handle_line(line_bytes)
        percent_pos.assert_called_once_with()
        self.wrapped_writer.write_msg.assert_awaited_once_with("RSP 2 4 45 AB")

    async def test_handle_move_hex_pos(self):
        line_bytes = b"CMD 02 04 40 AB" + RCV_EOL
        await self.line_handler.handle_line(line_bytes)
        self.cover.move_to_percent_pos.assert_awaited_once_with(0xAB / 0xFF)
        self.wrapped_writer.write_msg.assert_awaited_once_with("RSP 2 4 40 AB")

    async def test_handle_read_pct_pos(self):
        line_bytes = b"POS < 02 04 FFFF FFFF FF" + RCV_EOL
        self.web_pos_manager.web_on = True
        self.cover.fmt_pos_msg = MagicMock(return_value="POS * 02 04 0500 FFFF FF")
        await self.line_handler.handle_line(line_bytes)
        self.cover.fmt_pos_msg.assert_called_once_with()
        self.wrapped_writer.write_msg.assert_awaited_once_with(
            "POS * 02 04 0500 FFFF FF"
        )

    async def test_handle_move_pct_pos(self):
        line_bytes = b"POS > 02 04 0500 FFFF FF" + RCV_EOL
        self.web_pos_manager.web_on = True
        await self.line_handler.handle_line(line_bytes)
        self.cover.move_to_percent_pos.assert_awaited_once_with(0.5)


class TestMovementCommands(IsolatedAsyncioTestCase):
    """Test the behaviour of handle_line for movement commands using a cover emulator"""

    async def asyncSetUp(self):
        self.cover = TT6CoverEmulator(
            "test_cover", TTBusDeviceAddress(0x02, 0x04), 0.01, 1.77, 0.08, 1.0
        )
        self.wrapped_writer = AsyncMock()
        self.web_pos_manager = AsyncMock()
        self.web_pos_manager.web_on = False
        self.device_manager = AsyncMock()
        self.device_manager.lookup_device = MagicMock(return_value=self.cover)
        self.server_controller = AsyncMock()
        self.line_handler = LineHandler(
            self.wrapped_writer,
            self.web_pos_manager,
            self.device_manager,
            self.server_controller,
        )

    async def test_stop(self):
        mover = asyncio.create_task(
            self.line_handler.handle_line(
                f"CMD 02 04 {CommandCode.MOVE_DOWN.value:02X}".encode("utf-8") + RCV_EOL
            )
        )
        delay = 3
        await asyncio.sleep(delay)
        await self.line_handler.handle_line(
            f"CMD 02 04 {CommandCode.STOP.value:02X}".encode("utf-8") + RCV_EOL
        )
        await mover
        self.assertGreater(self.cover.drop, 0.19)
        self.assertLess(self.cover.drop, 0.24)

    async def test_move_while_moving(self):
        mover = asyncio.create_task(
            self.line_handler.handle_line(
                f"CMD 02 04 {CommandCode.MOVE_DOWN.value:02X}".encode("utf-8") + RCV_EOL
            )
        )
        delay = 3
        await asyncio.sleep(delay)
        self.assertGreater(self.cover.drop, 0.19)
        self.assertLess(self.cover.drop, 0.24)
        await self.line_handler.handle_line(
            f"CMD 02 04 {CommandCode.MOVE_UP.value:02X}".encode("utf-8") + RCV_EOL
        )
        await mover
        self.assertEqual(self.cover.drop, 0)
