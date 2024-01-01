from enum import Enum
from typing import Set


class CommandCode(Enum):
    STOP = 0x03
    MOVE_DOWN = 0x04
    MOVE_UP = 0x05
    MOVE_POS_1 = 0x06
    MOVE_POS_2 = 0x07
    MOVE_POS_3 = 0x08
    MOVE_POS_4 = 0x09
    MOVE_POS_5 = 0x10
    MOVE_POS_6 = 0x11
    MOVE_UP_STEP = 0x12
    MOVE_DOWN_STEP = 0x13
    STORE_POS_1 = 0x22
    STORE_POS_2 = 0x23
    STORE_POS_3 = 0x24
    STORE_POS_4 = 0x25
    STORE_POS_5 = 0x26
    STORE_POS_6 = 0x27
    DEL_POS_1 = 0x32
    DEL_POS_2 = 0x33
    DEL_POS_3 = 0x34
    DEL_POS_4 = 0x35
    DEL_POS_5 = 0x36
    DEL_POS_6 = 0x37
    MOVE_POS = 0x40
    READ_POS = 0x45


SIMPLE_COMMANDS: Set[CommandCode] = {
    CommandCode.STOP,
    CommandCode.MOVE_DOWN,
    CommandCode.MOVE_UP,
    CommandCode.MOVE_POS_1,
    CommandCode.MOVE_POS_2,
    CommandCode.MOVE_POS_3,
    CommandCode.MOVE_POS_4,
    CommandCode.MOVE_POS_5,
    CommandCode.MOVE_POS_6,
    CommandCode.MOVE_UP_STEP,
    CommandCode.MOVE_DOWN_STEP,
    CommandCode.STORE_POS_1,
    CommandCode.STORE_POS_2,
    CommandCode.STORE_POS_3,
    CommandCode.STORE_POS_4,
    CommandCode.STORE_POS_5,
    CommandCode.STORE_POS_6,
    CommandCode.DEL_POS_1,
    CommandCode.DEL_POS_2,
    CommandCode.DEL_POS_3,
    CommandCode.DEL_POS_4,
    CommandCode.DEL_POS_5,
    CommandCode.DEL_POS_6,
    CommandCode.READ_POS,
}


def command_code_names() -> Set[str]:
    return {code.name for code in CommandCode}


def simple_command_code_names() -> Set[str]:
    return {code.name for code in SIMPLE_COMMANDS}
