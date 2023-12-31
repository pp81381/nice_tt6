from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from nicett6.emulator.controller.device_manager import (
    DeviceManager,
    DuplicateDeviceError,
)
from nicett6.emulator.controller.web_pos_manager import WebPosManager
from nicett6.emulator.cover_emulator import TT6CoverEmulator
from nicett6.ttbus_device import TTBusDeviceAddress


class TestRegistration(IsolatedAsyncioTestCase):
    """Test the DeviceManager cover registration"""

    async def asyncSetUp(self):
        self.device = TT6CoverEmulator(
            "screen", TTBusDeviceAddress(0x02, 0x04), 0.01, 1.77, 0.08, 1.0
        )
        writer_manager = AsyncMock()
        self.web_pos_manager = WebPosManager(writer_manager, False)
        self.device_manager = DeviceManager(self.web_pos_manager)

    async def test_register_cover(self):
        self.device_manager.register_device(self.device)
        device = self.device_manager.lookup_device(self.device.tt_addr)
        self.assertIs(self.device, device)

    async def test_register_duplicate_cover(self):
        self.device_manager.register_device(self.device)
        with self.assertRaises(DuplicateDeviceError):
            self.device_manager.register_device(self.device)

    async def test_deregister_cover(self):
        self.assertEqual(len(self.device.observers), 0)
        self.device_manager.register_device(self.device)
        self.assertEqual(len(self.device.observers), 1)
        self.assertIn(self.web_pos_manager, self.device.observers)
        self.device_manager.deregister_device(self.device.tt_addr)
        self.assertEqual(len(self.device.observers), 0)
        with self.assertRaises(KeyError):
            self.device_manager.lookup_device(self.device.tt_addr)
