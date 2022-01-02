import unittest
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.encode import Encode


class TestEncoding(unittest.TestCase):

    TEST_EOL = Encode.EOL

    def setUp(self):
        self.mask_motor = TTBusDeviceAddress(0x03, 0x04)

    def test_encode_web_on(self):
        self.assertEqual(
            Encode.web_on(),
            b"WEB_ON" + self.TEST_EOL,
        )

    def test_encode_web_off(self):
        self.assertEqual(
            Encode.web_off(),
            b"WEB_OFF" + self.TEST_EOL,
        )

    def test_encode_cmd_move_pos_6(self):
        self.assertEqual(
            Encode.simple_command(self.mask_motor, "MOVE_POS_6"),
            b"CMD 03 04 11" + self.TEST_EOL,
        )

    def test_encode_cmd_move_pos(self):
        self.assertEqual(
            Encode.simple_command_with_data(self.mask_motor, "MOVE_POS", 0x99),
            b"CMD 03 04 40 99" + self.TEST_EOL,
        )

    def test_encode_cmd_move_pos_range_check(self):
        with self.assertRaises(ValueError):
            Encode.simple_command_with_data(self.mask_motor, "MOVE_POS", 256)
        with self.assertRaises(ValueError):
            Encode.simple_command_with_data(self.mask_motor, "MOVE_POS", -1)

    def test_encode_web_move_command(self):
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, 0.0),
            b"POS > 03 04 0000 FFFF FF" + self.TEST_EOL,
        )
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, 0.6),
            b"POS > 03 04 0600 FFFF FF" + self.TEST_EOL,
        )
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, 0.60049),
            b"POS > 03 04 0600 FFFF FF" + self.TEST_EOL,
        )
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, 0.60051),
            b"POS > 03 04 0601 FFFF FF" + self.TEST_EOL,
        )
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, 1.0),
            b"POS > 03 04 1000 FFFF FF" + self.TEST_EOL,
        )

    def test_encode_web_move_command_range_check(self):
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, 5.0),
            b"POS > 03 04 1000 FFFF FF" + self.TEST_EOL,
        )
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, 1.00051),
            b"POS > 03 04 1000 FFFF FF" + self.TEST_EOL,
        )
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, 1.00049),
            b"POS > 03 04 1000 FFFF FF" + self.TEST_EOL,
        )
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, -5),
            b"POS > 03 04 0000 FFFF FF" + self.TEST_EOL,
        )
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, -0.00051),
            b"POS > 03 04 0000 FFFF FF" + self.TEST_EOL,
        )
        self.assertEqual(
            Encode.web_move_command(self.mask_motor, -0.00049),
            b"POS > 03 04 0000 FFFF FF" + self.TEST_EOL,
        )

    def test_encode_web_pos_request(self):
        self.assertEqual(
            Encode.web_pos_request(self.mask_motor),
            b"POS < 03 04 FFFF FFFF FF" + self.TEST_EOL,
        )


if __name__ == "__main__":
    unittest.main()