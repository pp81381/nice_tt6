from unittest import TestCase

from nicett6.command_code import command_code_names

ALL_NAMES = [
    "STOP",
    "MOVE_DOWN",
    "MOVE_UP",
    "MOVE_POS_1",
    "MOVE_POS_2",
    "MOVE_POS_3",
    "MOVE_POS_4",
    "MOVE_POS_5",
    "MOVE_POS_6",
    "MOVE_UP_STEP",
    "MOVE_DOWN_STEP",
    "STORE_POS_1",
    "STORE_POS_2",
    "STORE_POS_3",
    "STORE_POS_4",
    "STORE_POS_5",
    "STORE_POS_6",
    "DEL_POS_1",
    "DEL_POS_2",
    "DEL_POS_3",
    "DEL_POS_4",
    "DEL_POS_5",
    "DEL_POS_6",
    "MOVE_POS",
    "READ_POS",
]


class TestCommandCode(TestCase):
    def test1(self):
        names = command_code_names()
        self.assertListEqual(names, ALL_NAMES)
