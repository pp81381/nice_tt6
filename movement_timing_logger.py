import argparse
import asyncio
from datetime import datetime, timedelta
import logging
from nicett6.connection import TT6Reader
from nicett6.cover import Cover
from nicett6.cover_manager import CoverManager
from nicett6.decode import PctAckResponse, PctPosResponse
from nicett6.ttbus_device import TTBusDeviceAddress

_LOGGER = logging.getLogger(__name__)


class TimeTracker:
    def __init__(self):
        self.start_time = datetime.now()
        self.prior_time = self.start_time
        self.prior_pct_pos = None
        _LOGGER.info("TimeTracker Started")

    def update(self, current_pct_pos: float):
        current_time = datetime.now()
        delta_start_time = current_time - self.start_time
        delta_prior_time = current_time - self.prior_time
        if self.prior_pct_pos is not None:
            delta_prior_pct_pos = current_pct_pos - self.prior_pct_pos
            period_pct_per_sec = delta_prior_pct_pos / delta_prior_time.total_seconds()
        else:
            delta_prior_pct_pos = None
            period_pct_per_sec = None
        _LOGGER.info(
            f"Delta Start Time: {delta_start_time}, "
            f"Delta Prior Time: {delta_prior_time}, "
            f"Delta Prior Pct Pos: {delta_prior_pct_pos}, "
            f"Period Pct Per Sec: {period_pct_per_sec}"
        )
        self.prior_time = current_time
        self.prior_pct_pos = current_pct_pos


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
                self.tt.update(msg.pct_pos)
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
