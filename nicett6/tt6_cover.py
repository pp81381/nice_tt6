import logging
from dataclasses import dataclass

from nicett6.command_code import CommandCode
from nicett6.connection import TT6Writer
from nicett6.cover import Cover
from nicett6.decode import (
    AckResponse,
    HexPosResponse,
    PctAckResponse,
    PctPosResponse,
    ResponseMessageType,
)
from nicett6.ttbus_device import TTBusDeviceAddress

_LOGGER = logging.getLogger(__name__)


@dataclass
class TT6Cover:
    """Class that sends commands to a `Cover` that is connected to the TTBus"""

    tt_addr: TTBusDeviceAddress
    cover: Cover
    writer: TT6Writer

    async def stop_notifier(self) -> None:
        await self.cover.stop_notifier()

    async def send_pos_request(self) -> None:
        await self.writer.send_web_pos_request(self.tt_addr)

    async def send_simple_command(self, cmd_name: str) -> None:
        _LOGGER.debug(f"sending {cmd_name} to {self.cover.name}")
        await self.writer.send_simple_command(self.tt_addr, cmd_name)

    async def send_drop_pct_command(self, drop_pct: float) -> None:
        _LOGGER.debug(f"moving {self.cover.name} to {drop_pct}")
        await self.writer.send_web_move_command(self.tt_addr, drop_pct)

    async def send_hex_move_command(self, hex_pos: int) -> None:
        _LOGGER.debug(f"moving {self.cover.name} to hex pos {hex_pos}")
        await self.writer.send_hex_move_command(self.tt_addr, hex_pos)

    async def send_close_command(self) -> None:
        _LOGGER.debug(f"sending MOVE_UP to {self.cover.name}")
        await self.writer.send_simple_command(self.tt_addr, "MOVE_UP")

    async def handle_response_message(self, msg: ResponseMessageType) -> None:
        if isinstance(msg, PctPosResponse):
            await self.cover.set_drop_pct(msg.pct_pos / 1000.0)
        elif isinstance(msg, PctAckResponse):
            await self.cover.set_target_drop_pct_hint(msg.pct_pos / 1000.0)
        elif isinstance(msg, AckResponse):
            if (
                msg.cmd_code == CommandCode.MOVE_UP
                or msg.cmd_code == CommandCode.MOVE_UP_STEP
            ):
                await self.cover.set_going_up()
            elif (
                msg.cmd_code == CommandCode.MOVE_DOWN
                or msg.cmd_code == CommandCode.MOVE_DOWN_STEP
            ):
                await self.cover.set_going_down()
            elif msg.cmd_code == CommandCode.STOP:
                # Can't call set_idle() here as a final pos
                # response will come from the controller up to
                # 2.5 secs after the Ack, which will call moved()
                # again and initiate another idle delay check
                pass
            elif msg.cmd_code in {
                CommandCode.MOVE_POS_1,
                CommandCode.MOVE_POS_2,
                CommandCode.MOVE_POS_3,
                CommandCode.MOVE_POS_4,
                CommandCode.MOVE_POS_5,
                CommandCode.MOVE_POS_6,
            }:
                # We can't know the direction until we've received a PctPosResponse
                await self.cover.moved()
        elif isinstance(msg, HexPosResponse):
            if msg.cmd_code == CommandCode.MOVE_POS:
                await self.cover.set_target_drop_pct_hint(msg.hex_pos / 255.0)
