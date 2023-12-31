import logging

from nicett6.command_code import CommandCode
from nicett6.ttbus_device import TTBusDeviceAddress

_LOGGER = logging.getLogger(__name__)


class Encode:
    """Helper class to encode commands"""

    EOL = b"\r"

    @classmethod
    def fmt_msg(cls, msg: str) -> bytes:
        return msg.encode("utf-8") + cls.EOL

    @classmethod
    def web_on(cls) -> bytes:
        return cls.fmt_msg("WEB_ON")

    @classmethod
    def web_off(cls) -> bytes:
        return cls.fmt_msg("WEB_OFF")

    @classmethod
    def simple_command(cls, tt_addr: TTBusDeviceAddress, cmd_name: str) -> bytes:
        return cls.fmt_msg(
            f"CMD {tt_addr.address:02X} {tt_addr.node:02X} "
            f"{CommandCode[cmd_name].value:02X}"
        )

    @classmethod
    def simple_command_with_data(
        cls, tt_addr: TTBusDeviceAddress, cmd_name: str, data: int
    ) -> bytes:
        """
        Encode a command that takes an integer data parameter

        data should be between 0x00 and 0xFF
        """
        if data < 0x00 or data > 0xFF:
            raise ValueError(f"data out of range 0x00 to 0xFF: {data}")
        return cls.fmt_msg(
            f"CMD {tt_addr.address:02X} {tt_addr.node:02X} "
            f"{CommandCode[cmd_name].value:02X} {data:02X}"
        )

    @classmethod
    def web_move_command(cls, tt_addr: TTBusDeviceAddress, pct: float) -> bytes:
        """Set position to the percentage given"""
        thousandths: int = round(pct * 1000.0)
        if thousandths < 0:
            _LOGGER.info(
                f"Requested percentage position for {tt_addr} of {pct}% floored at 0%"
            )
            thousandths = 0
        elif thousandths > 1000:
            _LOGGER.info(
                f"Requested percentage position for {tt_addr} of {pct}% capped at 100%"
            )
            thousandths = 1000
        return cls.fmt_msg(
            f"POS > {tt_addr.address:02X} {tt_addr.node:02X} "
            f"{thousandths:04d} FFFF FF"
        )

    @classmethod
    def web_pos_request(cls, tt_addr: TTBusDeviceAddress) -> bytes:
        """Request the position"""
        return cls.fmt_msg(
            f"POS < {tt_addr.address:02X} {tt_addr.node:02X} " "FFFF FFFF FF"
        )
