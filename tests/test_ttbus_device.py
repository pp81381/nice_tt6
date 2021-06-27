import unittest
from nicett6.ttbus_device import TTBusDeviceAddress


class TestDevice(unittest.TestCase):
    def test1(self):
        tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.assertEqual(str(tt_addr), "TTBusDeviceAddress(0x02, 0x04)")
        self.assertEqual(f"{tt_addr}", "TTBusDeviceAddress(0x02, 0x04)")
        self.assertEqual(tt_addr.id, "02_04")

    def test2(self):
        tt_addr1 = TTBusDeviceAddress(0x02, 0x04)
        tt_addr2 = TTBusDeviceAddress(0x02, 0x04)
        tt_addr3 = TTBusDeviceAddress(0x03, 0x04)
        self.assertEqual(tt_addr1, tt_addr2)
        self.assertEqual(hash(tt_addr1), hash(tt_addr2))
        self.assertNotEqual(tt_addr1, tt_addr3)
        self.assertNotEqual(hash(tt_addr1), hash(tt_addr3))

    def test3(self):
        tt_addr1 = TTBusDeviceAddress(0x02, 0x04)
        tt_addr2 = TTBusDeviceAddress(0x02, 0x04)
        s = set()
        s.add(tt_addr1)
        self.assertIn(tt_addr2, s)
        s.add(tt_addr2)
        self.assertEqual(len(s), 1)