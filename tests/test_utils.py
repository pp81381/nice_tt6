from unittest import TestCase
from nice_tt6.utils import hex_arg_to_int, pct_arg_to_int


class TestValidationAndConversion(TestCase):
    def test_hex_arg(self):
        self.assertEqual(hex_arg_to_int("00"), 0)
        self.assertEqual(hex_arg_to_int("10"), 16)
        self.assertEqual(hex_arg_to_int("1A"), 26)
        self.assertEqual(hex_arg_to_int("FF"), 255)
        with self.assertRaises(ValueError):
            hex_arg_to_int("")
        with self.assertRaises(ValueError):
            hex_arg_to_int("2")
        with self.assertRaises(ValueError):
            hex_arg_to_int("YY")
        with self.assertRaises(ValueError):
            hex_arg_to_int("100")

    def test_pct_arg(self):
        self.assertEqual(pct_arg_to_int("0000"), 0)
        self.assertEqual(pct_arg_to_int("0500"), 500)
        self.assertEqual(pct_arg_to_int("1000"), 1000)
        self.assertEqual(pct_arg_to_int("0999"), 999)
        with self.assertRaises(ValueError):
            pct_arg_to_int("")
        with self.assertRaises(ValueError):
            pct_arg_to_int("FFFF")
        with self.assertRaises(ValueError):
            pct_arg_to_int("01000")
