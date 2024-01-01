from typing import Set
from unittest import TestCase

from nicett6.command_code import command_code_names, simple_command_code_names

SIMPLE_COMMAND_NAMES: Set[str] = {
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
    "READ_POS",
}

PARAMETERISED_COMMAND_NAMES: Set[str] = {"MOVE_POS"}

ALL_COMMAND_NAMES: Set[str] = SIMPLE_COMMAND_NAMES.union(PARAMETERISED_COMMAND_NAMES)


class TestCommandCode(TestCase):
    def test_all(self):
        names = command_code_names()
        self.assertSetEqual(names, ALL_COMMAND_NAMES)

    def test_simple(self):
        names = simple_command_code_names()
        self.assertSetEqual(names, SIMPLE_COMMAND_NAMES)
