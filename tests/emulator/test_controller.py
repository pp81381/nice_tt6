import asyncio
from asyncio.streams import StreamWriter
from typing import List
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, call

from nicett6.command_code import CommandCode
from nicett6.consts import SEND_EOL
from nicett6.emulator.controller.controller import TT6Controller
from nicett6.emulator.controller.handle_messages import handle_messages
from nicett6.emulator.cover_emulator import TT6CoverEmulator
from nicett6.ttbus_device import TTBusDeviceAddress


def EOL(msg: bytes):
    return msg + SEND_EOL


def make_test_controller(
    web_on: bool, devices: List[TT6CoverEmulator]
) -> TT6Controller:
    controller = TT6Controller(web_on)
    controller._server = AsyncMock()
    controller._server.is_serving.return_value = True
    for device in devices:
        controller.device_manager.register_device(device)
    return controller


class TestControllerQuit(IsolatedAsyncioTestCase):
    """Test Controller stop"""

    async def asyncSetUp(self):
        self.controller = make_test_controller(False, [])

    async def test_quit(self):
        reader = AsyncMock(spec_set=asyncio.StreamReader)
        reader.readuntil.side_effect = [
            EOL(f"QUIT".encode("utf-8")),
            b"",
        ]
        writer = AsyncMock(spec_set=StreamWriter)
        await handle_messages(
            self.controller.writer_manager,
            self.controller.web_pos_manager,
            self.controller.device_manager,
            self.controller,
            reader,
            writer,
        )
        assert self.controller._server is not None
        self.controller._server.close.assert_called_once_with()
        self.controller._server.wait_closed.assert_awaited_once_with()
        writer.close.assert_called_once()


class TestControllerDownMovement(IsolatedAsyncioTestCase):
    """Test Controller downward movement"""

    async def asyncSetUp(self):
        self.cover = TT6CoverEmulator(
            "screen", TTBusDeviceAddress(0x02, 0x04), 0.01, 1.77, 0.08, 1.0
        )
        self.controller = make_test_controller(False, [self.cover])

    async def asyncTearDown(self):
        self.controller.device_manager.deregister_device(self.cover.tt_addr)

    async def test_move_down_to_pos(self):
        reader = AsyncMock(spec_set=asyncio.StreamReader)
        reader.readuntil.side_effect = [
            EOL(f"CMD 02 04 {CommandCode.MOVE_POS.value:02X} EF".encode("utf-8")),
            b"",
        ]
        writer = AsyncMock(spec_set=StreamWriter)
        await self.controller.handle_messages(reader, writer)
        self.assertAlmostEqual(self.cover.percent_pos, 0xEF / 0xFF, 2)
        writer.write.assert_called_once_with(EOL(b"RSP 2 4 40 EF"))
        writer.drain.assert_awaited_once()
        writer.close.assert_called_once()

    async def test_down_step(self):
        expected_step_num = 1
        expected_drop = self.cover.step_len
        reader = AsyncMock(spec_set=asyncio.StreamReader)
        reader.readuntil.side_effect = [
            EOL(f"CMD 02 04 {CommandCode.MOVE_DOWN_STEP.value:02X}".encode("utf-8")),
            b"",
        ]
        writer = AsyncMock(spec_set=StreamWriter)
        await self.controller.handle_messages(reader, writer)
        writer.write.assert_called_once_with(EOL(b"RSP 2 4 13"))
        writer.drain.assert_awaited_once()
        self.assertEqual(self.cover.step_num, expected_step_num)
        self.assertAlmostEqual(self.cover.drop, expected_drop)


class TestControllerUpMovement(IsolatedAsyncioTestCase):
    """Test Controller upward movement"""

    async def asyncSetUp(self):
        self.cover = TT6CoverEmulator(
            "screen", TTBusDeviceAddress(0x02, 0x04), 0.01, 1.77, 0.08, 0.95
        )
        self.controller = make_test_controller(False, [self.cover])

    async def asyncTearDown(self):
        self.controller.device_manager.deregister_device(self.cover.tt_addr)

    async def test_move_up(self):
        reader = AsyncMock(spec_set=asyncio.StreamReader)
        reader.readuntil.side_effect = [
            EOL(f"CMD 02 04 {CommandCode.MOVE_UP.value:02X}".encode("utf-8")),
            b"",
        ]
        writer = AsyncMock(spec_set=StreamWriter)
        await self.controller.handle_messages(reader, writer)
        writer.write.assert_called_once_with(EOL(b"RSP 2 4 5"))
        writer.drain.assert_awaited_once()
        self.assertAlmostEqual(self.cover.percent_pos, 1.0)

    async def test_read_pos(self):
        reader = AsyncMock(spec_set=asyncio.StreamReader)
        reader.readuntil.side_effect = [
            EOL(f"CMD 02 04 {CommandCode.READ_POS.value:02X}".encode("utf-8")),
            b"",
        ]
        writer = AsyncMock(spec_set=StreamWriter)
        await self.controller.handle_messages(reader, writer)
        writer.write.assert_called_once_with(EOL(b"RSP 2 4 45 F2"))
        writer.drain.assert_awaited_once()
        self.assertAlmostEqual(self.cover.percent_pos, 0xF2 / 0xFF, 2)

    async def test_up_step(self):
        expected_step_num = self.cover.step_num - 1
        expected_drop = self.cover.drop - self.cover.step_len
        reader = AsyncMock(spec_set=asyncio.StreamReader)
        reader.readuntil.side_effect = [
            EOL(f"CMD 02 04 {CommandCode.MOVE_UP_STEP.value:02X}".encode("utf-8")),
            b"",
        ]
        writer = AsyncMock(spec_set=StreamWriter)
        await self.controller.handle_messages(reader, writer)
        writer.write.assert_called_once_with(EOL(b"RSP 2 4 12"))
        writer.drain.assert_awaited_once()
        self.assertEqual(self.cover.step_num, expected_step_num)
        self.assertAlmostEqual(self.cover.drop, expected_drop)


class TestMovementSequences(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cover = TT6CoverEmulator(
            "test_cover", TTBusDeviceAddress(0x02, 0x04), 0.01, 1.77, 0.08, 1.0
        )
        self.controller = make_test_controller(False, [self.cover])

    async def asyncTearDown(self):
        self.controller.device_manager.deregister_device(self.cover.tt_addr)

    async def test_web_notifications(self):
        reader1 = AsyncMock(spec_set=asyncio.StreamReader)
        reader1.readuntil.side_effect = [EOL(b"WEB_ON"), b""]
        writer1 = AsyncMock(spec_set=StreamWriter)
        self.assertFalse(self.controller.web_pos_manager.web_on)
        await self.controller.handle_messages(reader1, writer1)
        writer1.write.assert_called_once_with(EOL(b"WEB COMMANDS ON"))
        writer1.drain.assert_awaited_once()
        self.assertTrue(self.controller.web_pos_manager.web_on)
        writer1.close.assert_called_once()

        reader2 = AsyncMock(spec_set=asyncio.StreamReader)
        reader2.readuntil.side_effect = [
            EOL(f"POS > 02 04 0950 FFFF FF".encode("utf-8")),
            b"",
        ]
        writer2 = AsyncMock(spec_set=StreamWriter)
        await self.controller.handle_messages(reader2, writer2)
        self.assertAlmostEqual(self.cover.percent_pos, 0.95, 2)
        scaled_pct_pos = round(self.cover.percent_pos * 1000)
        self.assertEqual(scaled_pct_pos, 949)
        writer2.write.assert_has_calls(
            [
                call(EOL(b"POS # 02 04 0950 FFFF FF")),
                call(EOL(b"POS * 02 04 0972 FFFF FF")),
                call(EOL(b"POS * 02 04 0949 FFFF FF")),
            ]
        )
        self.assertEqual(writer2.drain.await_count, 3)
        writer2.close.assert_called_once()
