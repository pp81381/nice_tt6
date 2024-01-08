import logging
from typing import List

from nicett6.command_code import CommandCode
from nicett6.emulator.controller.device_manager import DeviceRegistry
from nicett6.emulator.controller.server_controller import ServerController
from nicett6.emulator.controller.web_pos_manager import WebPosManager
from nicett6.emulator.controller.writer_wrapper import WriterWrapper
from nicett6.emulator.cover_emulator import TT6CoverEmulator
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import hex_arg_to_int, pct_arg_to_int

_LOGGER = logging.getLogger(__name__)

PRESET_POS_1 = "POS_1"
PRESET_POS_2 = "POS_2"
PRESET_POS_3 = "POS_3"
PRESET_POS_4 = "POS_4"
PRESET_POS_5 = "POS_5"
PRESET_POS_6 = "POS_6"


class InvalidCommandError(Exception):
    pass


class LineHandler:
    MSG_WEB_COMMANDS_ON = "WEB COMMANDS ON"
    MSG_WEB_COMMANDS_OFF = "WEB COMMANDS OFF"
    MSG_INVALID_COMMAND_ERROR = "ERROR - NOT VALID COMMAND"

    def __init__(
        self,
        wrapped_writer: WriterWrapper,
        web_pos_manager: WebPosManager,
        device_registry: DeviceRegistry,
        server_controller: ServerController,
    ) -> None:
        self.wrapped_writer = wrapped_writer
        self.web_pos_manager = web_pos_manager
        self.device_registry = device_registry
        self.server_controller = server_controller

    async def write_msg(self, msg: str) -> None:
        await self.wrapped_writer.write_msg(msg)

    async def handle_line(self, line_bytes: bytes) -> None:
        try:
            _LOGGER.info(f"handling cmd: {line_bytes!r}")
            line: str = line_bytes.decode("utf-8")
            args: List[str] = line.split()
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
                await self.server_controller.stop_server()
            else:
                raise InvalidCommandError()
        except (InvalidCommandError, ValueError):
            await self.write_msg(self.MSG_INVALID_COMMAND_ERROR)

    async def _handle_cmd(self, args: List[str]) -> None:
        if len(args) < 3:
            raise InvalidCommandError()
        address = hex_arg_to_int(args[0])
        node = hex_arg_to_int(args[1])
        cover = self.device_registry.lookup_device(TTBusDeviceAddress(address, node))
        cmd_code: CommandCode = CommandCode(hex_arg_to_int(args[2]))
        if cmd_code == CommandCode.MOVE_POS:
            if len(args) != 4:
                raise InvalidCommandError()
            target_hex_pos = hex_arg_to_int(args[3])
            # Message is written before movement completes
            msg = f"RSP {address:X} {node:X} {cmd_code.value:X} {target_hex_pos:X}"
            await self.write_msg(msg)
            await cover.move_to_hex_pos(target_hex_pos)
        elif cmd_code == CommandCode.READ_POS:
            if len(args) != 3:
                raise InvalidCommandError()
            hex_pos = round(cover.pos * 0xFF / 1000)
            msg = f"RSP {address:X} {node:X} {cmd_code.value:X} {hex_pos:X}"
            await self.write_msg(msg)
        else:
            if len(args) != 3:
                raise InvalidCommandError()
            msg = f"RSP {address:X} {node:X} {cmd_code.value:X}"
            await self.write_msg(msg)
            await self.do_simple_command(cover, cmd_code)

    async def _handle_web_cmd(self, args: List[str]) -> None:
        if len(args) != 6:
            raise InvalidCommandError()
        if args[4] != "FFFF" or args[5] != "FF":
            raise ValueError("Web command args 4 and 5 must be FFFF FF")
        if not self.web_pos_manager.web_on:
            raise InvalidCommandError()
        cmd_char = args[0]
        address = hex_arg_to_int(args[1])
        node = hex_arg_to_int(args[2])
        cover = self.device_registry.lookup_device(TTBusDeviceAddress(address, node))
        # TODO - POS-specific ERRORs
        if cmd_char == "<":
            if args[3] != "FFFF":
                raise ValueError(
                    "Web command arg 3 must be FFFF when requesting position"
                )
            await self.write_msg(cover.fmt_pos_msg())
        elif cmd_char == ">":
            target_pos = pct_arg_to_int(args[3])
            await self.write_msg(cover.fmt_ack_msg(target_pos))
            await cover.move_to_pos(target_pos)
        else:
            raise ValueError(f"Invalid command character in web command: {cmd_char!r}")

    async def _handle_web_on(self) -> None:
        self.web_pos_manager.web_on = True
        await self.write_msg(self.MSG_WEB_COMMANDS_ON)

    async def _handle_web_off(self) -> None:
        self.web_pos_manager.web_on = False
        await self.write_msg(self.MSG_WEB_COMMANDS_OFF)

    @staticmethod
    async def do_simple_command(cover: TT6CoverEmulator, cmd_code: CommandCode) -> None:
        if cmd_code == CommandCode.STOP:
            await cover.stop()
        elif cmd_code == CommandCode.MOVE_DOWN:
            await cover.move_down()
        elif cmd_code == CommandCode.MOVE_UP:
            await cover.move_up()
        elif cmd_code == CommandCode.MOVE_POS_1:
            await cover.move_preset(PRESET_POS_1)
        elif cmd_code == CommandCode.MOVE_POS_2:
            await cover.move_preset(PRESET_POS_2)
        elif cmd_code == CommandCode.MOVE_POS_3:
            await cover.move_preset(PRESET_POS_3)
        elif cmd_code == CommandCode.MOVE_POS_4:
            await cover.move_preset(PRESET_POS_4)
        elif cmd_code == CommandCode.MOVE_POS_5:
            await cover.move_preset(PRESET_POS_5)
        elif cmd_code == CommandCode.MOVE_POS_6:
            await cover.move_preset(PRESET_POS_6)
        elif cmd_code == CommandCode.MOVE_DOWN_STEP:
            await cover.move_down_step()
        elif cmd_code == CommandCode.MOVE_UP_STEP:
            await cover.move_up_step()
        elif cmd_code == CommandCode.STORE_POS_1:
            await cover.store_preset(PRESET_POS_1)
        elif cmd_code == CommandCode.STORE_POS_2:
            await cover.store_preset(PRESET_POS_2)
        elif cmd_code == CommandCode.STORE_POS_3:
            await cover.store_preset(PRESET_POS_3)
        elif cmd_code == CommandCode.STORE_POS_4:
            await cover.store_preset(PRESET_POS_4)
        elif cmd_code == CommandCode.STORE_POS_5:
            await cover.store_preset(PRESET_POS_5)
        elif cmd_code == CommandCode.STORE_POS_6:
            await cover.store_preset(PRESET_POS_6)
        elif cmd_code == CommandCode.DEL_POS_1:
            await cover.del_preset(PRESET_POS_1)
        elif cmd_code == CommandCode.DEL_POS_2:
            await cover.del_preset(PRESET_POS_2)
        elif cmd_code == CommandCode.DEL_POS_3:
            await cover.del_preset(PRESET_POS_3)
        elif cmd_code == CommandCode.DEL_POS_4:
            await cover.del_preset(PRESET_POS_4)
        elif cmd_code == CommandCode.DEL_POS_5:
            await cover.del_preset(PRESET_POS_5)
        elif cmd_code == CommandCode.DEL_POS_6:
            await cover.del_preset(PRESET_POS_6)
        else:
            raise InvalidCommandError()
