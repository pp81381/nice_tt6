import unittest
from nicett6.decode import (
    Decode,
    AckResponse,
    ErrorResponse,
    HexPosResponse,
    InformationalResponse,
    InvalidResponseError,
    PctAckResponse,
    PctPosResponse,
)
from nicett6.ttbus_device import TTBusDeviceAddress


class TestDecoding(unittest.TestCase):

    TEST_EOL = Decode.EOL

    def test_decode_cmd_response1(self):
        """Simple Ack"""
        res = Decode.decode_line_bytes(b"RSP 3 4 11" + self.TEST_EOL)
        self.assertIsInstance(res, AckResponse)
        self.assertEqual(res.tt_addr, TTBusDeviceAddress(0x03, 0x04))
        self.assertEqual(res.cmd_code, 0x11)

    def test_decode_cmd_response2(self):
        """CMD_MOVE_POS response with hex_pos"""
        res = Decode.decode_line_bytes(b"RSP 3 4 40 7E" + self.TEST_EOL)
        self.assertIsInstance(res, HexPosResponse)
        self.assertEqual(res.tt_addr, TTBusDeviceAddress(0x03, 0x04))
        self.assertEqual(res.cmd_code, 0x40)
        self.assertEqual(res.hex_pos, 0x7E)

    def test_decode_cmd_response3(self):
        """CMD_READ_POS response with hex_pos"""
        res = Decode.decode_line_bytes(b"RSP 3 4 45 7E" + self.TEST_EOL)
        self.assertIsInstance(res, HexPosResponse)
        self.assertEqual(res.tt_addr, TTBusDeviceAddress(0x03, 0x04))
        self.assertEqual(res.cmd_code, 0x45)
        self.assertEqual(res.hex_pos, 0x7E)

    def test_decode_cmd_response_err1(self):
        """Address wrong length"""
        with self.assertRaises(ValueError):
            Decode.decode_line_bytes(b"RSP 113 4 11" + self.TEST_EOL)

    def test_decode_cmd_response_err2(self):
        """Response for command not expecting fourth arg"""
        with self.assertRaises(InvalidResponseError):
            Decode.decode_line_bytes(b"RSP 3 4 4 7E" + self.TEST_EOL)

    def test_decode_web_ack1(self):
        """Web ack"""
        res = Decode.decode_line_bytes(b"POS # 03 04 0500 FFFF FF" + self.TEST_EOL)
        self.assertIsInstance(res, PctAckResponse)
        self.assertEqual(res.tt_addr, TTBusDeviceAddress(0x03, 0x04))
        self.assertEqual(res.pct_pos, 500)

    def test_decode_web_response1(self):
        """Web response"""
        res = Decode.decode_line_bytes(b"POS * 03 04 0500 FFFF FF" + self.TEST_EOL)
        self.assertIsInstance(res, PctPosResponse)
        self.assertEqual(res.tt_addr, TTBusDeviceAddress(0x03, 0x04))
        self.assertEqual(res.pct_pos, 500)

    def test_decode_web_response_err1(self):
        """Bad cmd_char"""
        with self.assertRaises(InvalidResponseError):
            Decode.decode_line_bytes(b"POS x 03 04 0500 FFFF FF" + self.TEST_EOL)

    def test_decode_web_response_err2(self):
        """Percent wrong length"""
        with self.assertRaises(ValueError):
            Decode.decode_line_bytes(b"POS * 03 04 500 FFFF FF" + self.TEST_EOL)

    def test_decode_info_response1(self):
        res = Decode.decode_line_bytes(b"WEB COMMANDS ON" + self.TEST_EOL)
        self.assertIsInstance(res, InformationalResponse)
        self.assertEqual(res.info, "WEB COMMANDS ON" + self.TEST_EOL.decode("utf-8"))

    def test_decode_error_response1(self):
        res = Decode.decode_line_bytes(b"ERROR - NOT INVALID COMMAND" + self.TEST_EOL)
        self.assertIsInstance(res, ErrorResponse)
        self.assertEqual(
            res.error, "ERROR - NOT INVALID COMMAND" + self.TEST_EOL.decode("utf-8")
        )

    def test_decode_error_response2(self):
        res = Decode.decode_line_bytes(b"POS ! FF FF FFFF FFFF FF 01" + self.TEST_EOL)
        self.assertIsInstance(res, ErrorResponse)
        self.assertEqual(
            res.error, "POS ! FF FF FFFF FFFF FF 01" + self.TEST_EOL.decode("utf-8")
        )


if __name__ == "__main__":
    unittest.main()