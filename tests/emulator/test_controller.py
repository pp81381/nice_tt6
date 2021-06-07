import asyncio
from asyncio.streams import StreamWriter
from nicett6.emulator.controller import (
    TT6Controller,
    DuplicateDeviceError,
    SEND_EOL,
)
from nicett6.emulator.line_handler import (
    CMD_MOVE_DOWN_STEP,
    CMD_MOVE_POS,
    CMD_MOVE_UP,
    CMD_MOVE_UP_STEP,
    CMD_READ_POS,
)
from nicett6.emulator.cover_emulator import TT6CoverEmulator
from nicett6.ttbus_device import TTBusDeviceAddress
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, call


def EOL(msg: bytes):
    return msg + SEND_EOL


class TestControllerRegistration(IsolatedAsyncioTestCase):
    """Test the controller cover registration"""

    async def asyncSetUp(self):
        self.device = TT6CoverEmulator(
            "screen", TTBusDeviceAddress(0x02, 0x04), 0.01, 1.77, 0.08, 1.0
        )
        self.controller = TT6Controller(False)

    async def test_register_cover(self):
        self.controller.register_device(self.device)
        device = self.controller.lookup_device(self.device.tt_addr)
        self.assertIs(self.device, device)

    async def test_register_duplicate_cover(self):
        self.controller.register_device(self.device)
        with self.assertRaises(DuplicateDeviceError):
            self.controller.register_device(self.device)

    async def test_deregister_cover(self):
        self.assertEqual(len(self.device.observers), 0)
        self.controller.register_device(self.device)
        self.assertEqual(len(self.device.observers), 1)
        self.assertIn(self.controller, self.device.observers)
        self.controller.deregister_device(self.device.tt_addr)
        self.assertEqual(len(self.device.observers), 0)
        with self.assertRaises(KeyError):
            self.controller.lookup_device(self.device.tt_addr)


class TestControllerDownMovement(IsolatedAsyncioTestCase):
    """Test Controller downward movement"""

    async def asyncSetUp(self):
        self.cover = TT6CoverEmulator(
            "screen", TTBusDeviceAddress(0x02, 0x04), 0.01, 1.77, 0.08, 1.0
        )
        self.controller = TT6Controller(False)
        self.controller.register_device(self.cover)

    async def asyncTearDown(self):
        self.controller.deregister_device(self.cover.tt_addr)

    async def test_move_down_to_pos(self):
        reader = AsyncMock(spec_set=asyncio.StreamReader)
        reader.readuntil.side_effect = [
            EOL(f"CMD 02 04 {CMD_MOVE_POS:02X} EF".encode("utf-8")),
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
            EOL(f"CMD 02 04 {CMD_MOVE_DOWN_STEP:02X}".encode("utf-8")),
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
        self.controller = TT6Controller(False)
        self.controller.register_device(self.cover)

    async def asyncTearDown(self):
        self.controller.deregister_device(self.cover.tt_addr)

    async def test_move_up(self):
        reader = AsyncMock(spec_set=asyncio.StreamReader)
        reader.readuntil.side_effect = [
            EOL(f"CMD 02 04 {CMD_MOVE_UP:02X}".encode("utf-8")),
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
            EOL(f"CMD 02 04 {CMD_READ_POS:02X}".encode("utf-8")),
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
            EOL(f"CMD 02 04 {CMD_MOVE_UP_STEP:02X}".encode("utf-8")),
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
        self.controller = TT6Controller(False)
        self.controller.register_device(self.cover)

    async def asyncTearDown(self):
        self.controller.deregister_device(self.cover.tt_addr)

    async def test_web_notifications(self):
        reader1 = AsyncMock(spec_set=asyncio.StreamReader)
        reader1.readuntil.side_effect = [EOL(b"WEB_ON"), b""]
        writer1 = AsyncMock(spec_set=StreamWriter)
        self.assertFalse(self.controller.web_on)
        await self.controller.handle_messages(reader1, writer1)
        writer1.write.assert_called_once_with(EOL(b"WEB COMMANDS ON"))
        writer1.drain.assert_awaited_once()
        self.assertTrue(self.controller.web_on)
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
                call(EOL(b"POS * 02 04 0972 FFFF FF")),
                call(EOL(b"POS * 02 04 0949 FFFF FF")),
            ]
        )
        self.assertEqual(writer2.drain.await_count, 2)
        writer2.close.assert_called_once()
