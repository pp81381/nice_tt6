import re
import logging
from nicett6.emulator.line_handler import CMD_READ_POS, CMD_MOVE_POS
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import hex_arg_to_int, pct_arg_to_int

_LOGGER = logging.getLogger(__name__)


class InvalidResponseError(Exception):
    pass


class AckResponse:
    def __init__(self, tt_addr, cmd_code):
        self.tt_addr = tt_addr
        self.cmd_code = cmd_code

    def __repr__(self):
        return f"{type(self).__name__}({self.tt_addr}, {self.cmd_code:02X})"


class HexPosResponse:
    def __init__(self, tt_addr, cmd_code, hex_pos):
        self.tt_addr = tt_addr
        self.cmd_code = cmd_code
        self.hex_pos = hex_pos

    def __repr__(self):
        return f"{type(self).__name__}({self.tt_addr}, {self.cmd_code:02X}, {self.hex_pos:02X})"


class PctPosResponse:
    def __init__(self, tt_addr, pct_pos):
        self.tt_addr = tt_addr
        self.pct_pos = pct_pos

    def __repr__(self):
        return f"{type(self).__name__}({self.tt_addr}, {self.pct_pos})"


class InformationalResponse:
    def __init__(self, line):
        self.info = line

    def __repr__(self):
        return f"{type(self).__name__}({self.info})"


class ErrorResponse:
    def __init__(self, line):
        self.error = line

    def __repr__(self):
        return f"{type(self).__name__}({self.error})"


def _decode_cmd_response(args):
    if len(args) < 3:
        raise InvalidResponseError()
    tt_addr = TTBusDeviceAddress(
        hex_arg_to_int(args[0], False), hex_arg_to_int(args[1], False)
    )
    cmd_code = hex_arg_to_int(args[2], False)
    if len(args) == 3:
        return AckResponse(tt_addr, cmd_code)
    elif len(args) == 4 and cmd_code in {CMD_READ_POS, CMD_MOVE_POS}:
        hex_pos = hex_arg_to_int(args[3], False)
        return HexPosResponse(tt_addr, cmd_code, hex_pos)
    else:
        raise InvalidResponseError()


def _decode_web_response(args, line):
    if len(args) < 1:
        raise InvalidResponseError()
    cmd_char = args[0]
    if cmd_char == "*":
        if len(args) != 6:
            raise InvalidResponseError()
        if args[4] != "FFFF" or args[5] != "FF":
            raise InvalidResponseError()
        tt_addr = TTBusDeviceAddress(hex_arg_to_int(args[1]), hex_arg_to_int(args[2]))
        pct_pos = pct_arg_to_int(args[3])
        return PctPosResponse(tt_addr, pct_pos)
    elif cmd_char == "!":
        # TODO: Attach to specific cover if possible
        return ErrorResponse(line)
    else:
        raise InvalidResponseError()


class Decode:

    EOL = b"\r"

    @classmethod
    def decode_line_bytes(cls, line_bytes):
        _LOGGER.debug(f"handling response: {line_bytes!r}")

        if line_bytes.find(cls.EOL) != len(line_bytes) - len(cls.EOL):
            raise InvalidResponseError()

        line = line_bytes.decode("utf-8")
        args = line.split()
        if len(args) < 1:
            raise InvalidResponseError()
        response_code = args.pop(0)
        if response_code == "RSP":
            return _decode_cmd_response(args)
        elif response_code == "POS":
            return _decode_web_response(args, line)
        elif response_code == "WEB":
            return InformationalResponse(line)
        elif response_code == "ERROR":
            return ErrorResponse(line)
        else:
            raise InvalidResponseError()
