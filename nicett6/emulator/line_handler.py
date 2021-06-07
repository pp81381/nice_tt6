import logging
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import hex_arg_to_int, pct_arg_to_int

_LOGGER = logging.getLogger(__name__)

CMD_STOP = 0x03
CMD_MOVE_DOWN = 0x04
CMD_MOVE_UP = 0x05
CMD_MOVE_POS_1 = 0x06
CMD_MOVE_POS_2 = 0x07
CMD_MOVE_POS_3 = 0x08
CMD_MOVE_POS_4 = 0x09
CMD_MOVE_POS_5 = 0x10
CMD_MOVE_POS_6 = 0x11
CMD_MOVE_UP_STEP = 0x12
CMD_MOVE_DOWN_STEP = 0x13
CMD_STORE_UPPER_LIMIT = 0x20
CMD_STORE_LOWER_LIMIT = 0x21
CMD_STORE_POS_1 = 0x22
CMD_STORE_POS_2 = 0x23
CMD_STORE_POS_3 = 0x24
CMD_STORE_POS_4 = 0x25
CMD_STORE_POS_5 = 0x26
CMD_STORE_POS_6 = 0x27
CMD_DEL_UPPER_LIMIT = 0x30
CMD_DEL_LOWER_LIMIT = 0x31
CMD_DEL_POS_1 = 0x32
CMD_DEL_POS_2 = 0x33
CMD_DEL_POS_3 = 0x34
CMD_DEL_POS_4 = 0x35
CMD_DEL_POS_5 = 0x36
CMD_DEL_POS_6 = 0x37
CMD_MOVE_POS = 0x40
CMD_READ_POS = 0x45

PRESET_POS_1 = "POS_1"
PRESET_POS_2 = "POS_2"
PRESET_POS_3 = "POS_3"
PRESET_POS_4 = "POS_4"
PRESET_POS_5 = "POS_5"
PRESET_POS_6 = "POS_6"


class InvalidCommandError(Exception):
    pass


def make_simple_command_coro(cover, cmd_code):
    if cmd_code == CMD_STOP:
        coro = cover.stop()
    elif cmd_code == CMD_MOVE_DOWN:
        coro = cover.move_down()
    elif cmd_code == CMD_MOVE_UP:
        coro = cover.move_up()
    elif cmd_code == CMD_MOVE_POS_1:
        coro = cover.move_preset(PRESET_POS_1)
    elif cmd_code == CMD_MOVE_POS_2:
        coro = cover.move_preset(PRESET_POS_2)
    elif cmd_code == CMD_MOVE_POS_3:
        coro = cover.move_preset(PRESET_POS_3)
    elif cmd_code == CMD_MOVE_POS_4:
        coro = cover.move_preset(PRESET_POS_4)
    elif cmd_code == CMD_MOVE_POS_5:
        coro = cover.move_preset(PRESET_POS_5)
    elif cmd_code == CMD_MOVE_POS_6:
        coro = cover.move_preset(PRESET_POS_6)
    elif cmd_code == CMD_MOVE_DOWN_STEP:
        coro = cover.move_down_step()
    elif cmd_code == CMD_MOVE_UP_STEP:
        coro = cover.move_up_step()
    elif cmd_code == CMD_STORE_UPPER_LIMIT:
        coro = cover.store_upper_limit()
    elif cmd_code == CMD_STORE_LOWER_LIMIT:
        coro = cover.store_lower_limit()
    elif cmd_code == CMD_STORE_POS_1:
        coro = cover.store_preset(PRESET_POS_1)
    elif cmd_code == CMD_STORE_POS_2:
        coro = cover.store_preset(PRESET_POS_2)
    elif cmd_code == CMD_STORE_POS_3:
        coro = cover.store_preset(PRESET_POS_3)
    elif cmd_code == CMD_STORE_POS_4:
        coro = cover.store_preset(PRESET_POS_4)
    elif cmd_code == CMD_STORE_POS_5:
        coro = cover.store_preset(PRESET_POS_5)
    elif cmd_code == CMD_STORE_POS_6:
        coro = cover.store_preset(PRESET_POS_6)
    elif cmd_code == CMD_DEL_UPPER_LIMIT:
        coro = cover.del_upper_limit()
    elif cmd_code == CMD_DEL_LOWER_LIMIT:
        coro = cover.del_lower_limit()
    elif cmd_code == CMD_DEL_POS_1:
        coro = cover.del_preset(PRESET_POS_1)
    elif cmd_code == CMD_DEL_POS_2:
        coro = cover.del_preset(PRESET_POS_2)
    elif cmd_code == CMD_DEL_POS_3:
        coro = cover.del_preset(PRESET_POS_3)
    elif cmd_code == CMD_DEL_POS_4:
        coro = cover.del_preset(PRESET_POS_4)
    elif cmd_code == CMD_DEL_POS_5:
        coro = cover.del_preset(PRESET_POS_5)
    elif cmd_code == CMD_DEL_POS_6:
        coro = cover.del_preset(PRESET_POS_6)
    else:
        raise InvalidCommandError()
    return coro


class LineHandler:

    MSG_WEB_COMMANDS_ON = "WEB COMMANDS ON"
    MSG_WEB_COMMANDS_OFF = "WEB COMMANDS OFF"
    MSG_INVALID_COMMAND_ERROR = "ERROR - NOT VALID COMMAND"

    def __init__(self, wrapped_writer, controller):
        self.wrapped_writer = wrapped_writer
        self.controller = controller

    async def write_msg(self, msg: str):
        await self.wrapped_writer.write_msg(msg)

    @classmethod
    def fmt_pos_msg(cls, cover):
        scaled_pct_pos = round(cover.percent_pos * 1000)
        return f"POS * {cover.tt_addr.address:02X} {cover.tt_addr.node:02X} {scaled_pct_pos:04d} FFFF FF"

    async def handle_line(self, line_bytes):
        try:
            _LOGGER.info(f"handling cmd: {line_bytes!r}")
            line = line_bytes.decode("utf-8")
            args = line.split()
            if len(args) < 1:
                raise InvalidCommandError()
            cmd = args.pop(0)
            if cmd == "CMD":
                await self._handle_cmd(args)
            elif cmd == "POS":
                await self._handle_web_cmd(args)
            elif cmd == "WEB_ON":
                if len(args) != 0:
                    raise InvalidCommandError()
                await self._handle_web_on()
            elif cmd == "WEB_OFF":
                if len(args) != 0:
                    raise InvalidCommandError()
                await self._handle_web_off()
            elif cmd == "QUIT":
                self.controller.stop_server()
            else:
                raise InvalidCommandError()
        except (InvalidCommandError, ValueError):
            await self.write_msg(self.MSG_INVALID_COMMAND_ERROR)

    async def _handle_cmd(self, args):
        if len(args) < 3:
            raise InvalidCommandError()
        address = hex_arg_to_int(args[0])
        node = hex_arg_to_int(args[1])
        cover = self.controller.lookup_device(TTBusDeviceAddress(address, node))
        cmd_code = hex_arg_to_int(args[2])
        if cmd_code == CMD_MOVE_POS:
            if len(args) != 4:
                raise InvalidCommandError()
            target_hex_pos = hex_arg_to_int(args[3])
            # Message is written before movement completes
            msg = f"RSP {address:X} {node:X} {cmd_code:X} {target_hex_pos:X}"
            await self.write_msg(msg)
            target_pct_pos = target_hex_pos / 0xFF
            await cover.move_to_percent_pos(target_pct_pos)
        elif cmd_code == CMD_READ_POS:
            if len(args) != 3:
                raise InvalidCommandError()
            hex_pos = round(cover.percent_pos * 0xFF)
            msg = f"RSP {address:X} {node:X} {cmd_code:X} {hex_pos:X}"
            await self.write_msg(msg)
        else:
            if len(args) != 3:
                raise InvalidCommandError()
            coro = make_simple_command_coro(cover, cmd_code)
            msg = f"RSP {address:X} {node:X} {cmd_code:X}"
            await self.write_msg(msg)
            await coro

    async def _handle_web_cmd(self, args):
        if len(args) != 6:
            raise InvalidCommandError()
        if args[4] != "FFFF" or args[5] != "FF":
            raise ValueError("Web command args 4 and 5 must be FFFF FF")
        if not self.controller.web_on:
            raise InvalidCommandError()
        cmd_char = args[0]
        address = hex_arg_to_int(args[1])
        node = hex_arg_to_int(args[2])
        cover = self.controller.lookup_device(TTBusDeviceAddress(address, node))
        # TODO - POS-specific ERRORs
        if cmd_char == "<":
            if args[3] != "FFFF":
                raise ValueError(
                    "Web command arg 3 must be FFFF when requesting position"
                )
            await self.write_msg(self.fmt_pos_msg(cover))
        elif cmd_char == ">":
            target_pct_pos = pct_arg_to_int(args[3]) / 1000
            await cover.move_to_percent_pos(target_pct_pos)
        else:
            raise ValueError(f"Invalid command character in web command: {cmd_char!r}")

    async def _handle_web_on(self):
        self.controller.web_on = True
        await self.write_msg(self.MSG_WEB_COMMANDS_ON)

    async def _handle_web_off(self):
        self.controller.web_on = False
        await self.write_msg(self.MSG_WEB_COMMANDS_OFF)