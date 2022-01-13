import argparse
import asyncio
from datetime import datetime, timedelta
import logging
from nicett6.connection import TT6Reader
from nicett6.cover import Cover, wait_for_motion_to_complete
from nicett6.cover_manager import CoverManager
from nicett6.decode import PctAckResponse, PctPosResponse
from nicett6.ttbus_device import TTBusDeviceAddress

_LOGGER = logging.getLogger(__name__)


class TimeTracker:
    def __init__(self):
        self.start = datetime.now()
        self.prior = self.start
        _LOGGER.info("TimeTracker Started")

    def update(self):
        current = datetime.now()
        delta_start = current - self.start
        delta_prior = current - self.prior
        _LOGGER.info(f"Delta Start: {delta_start}, Delta Prior: {delta_prior}")
        self.prior = current


class MessageHandler:
    THRESHOLD = timedelta(seconds=5.0)

    def __init__(self):
        self.tt = None
        self.prev_movement = None

    def handle(self, msg):
        if isinstance(msg, PctAckResponse):
            self.tt = TimeTracker()
        elif isinstance(msg, PctPosResponse):
            self.prev_movement = datetime.now()
            if self.tt is not None:
                self.tt.update()
            else:
                _LOGGER.warning(f"Pos message received without initial Ack: {msg!r}")

    async def wait_for_motion_to_complete(self):
        self.prev_movement = datetime.now()
        while True:
            await asyncio.sleep(0.2)
            if datetime.now() - self.prev_movement > self.THRESHOLD:
                self.tt = None
                return


async def read_messages(reader: TT6Reader, handler: MessageHandler):
    async for msg in reader:
        handler.handle(msg)
    _LOGGER.info(f"read_messages finished")


async def log_movement_timing(serial_port, address):
    tt_addr = TTBusDeviceAddress(address, 0x04)
    max_drop = 2.0
    async with CoverManager(serial_port) as mgr:
        handler: MessageHandler = MessageHandler()
        reader: TT6Reader = mgr._conn.add_reader()
        read_messages_task = asyncio.create_task(read_messages(reader, handler))
        message_tracker_task = asyncio.create_task(mgr.message_tracker())

        tt6_cover = await mgr.add_cover(tt_addr, Cover("Cover", max_drop))
        await tt6_cover.send_drop_pct_command(0.0)  # Fully down
        await handler.wait_for_motion_to_complete()

        await tt6_cover.send_drop_pct_command(1.0)  # Fully up
        await handler.wait_for_motion_to_complete()

    await read_messages_task
    await message_tracker_task


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--serial_port",
        type=str,
        default="socket://localhost:50200",
        help="serial port",
    )
    parser.add_argument(
        "-a",
        "--address",
        type=int,
        choices=[2, 3],
        default=2,
        help="device address",
    )
    args = parser.parse_args()
    asyncio.run(log_movement_timing(args.serial_port, args.address))
