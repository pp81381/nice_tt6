import asyncio
from contextlib import asynccontextmanager
from nicett6.connection import TT6Writer, open_connection, TT6Reader
from nicett6.cover import Cover, TT6CoverWriter
from nicett6.decode import PctPosResponse
from nicett6.multiplexer import MultiplexerSerialConnection
from nicett6.ttbus_device import TTBusDeviceAddress


@asynccontextmanager
async def open_cover_manager(
    tt_addr,
    max_drop,
    serial_port=None,
):
    async with open_connection(serial_port) as conn:
        mgr = CoverManager(conn, tt_addr, max_drop)
        await mgr._start()
        yield mgr


class CoverManager:

    POLLING_INTERVAL = 0.2

    def __init__(
        self,
        conn: MultiplexerSerialConnection,
        cover_tt_addr: TTBusDeviceAddress,
        cover_max_drop: float,
    ):
        self._conn = conn
        self.cover = Cover("Cover", cover_max_drop)
        # NOTE: reader is created here rather than in message_tracker
        # to ensure that all messages from this moment on are captured
        self._message_tracker_reader: TT6Reader = self._conn.add_reader()
        self._writer: TT6Writer = self._conn.get_writer()
        self._cover_writer = TT6CoverWriter(cover_tt_addr, self.cover, self._writer)

    async def _start(self):
        await self._writer.send_web_on()
        await self.send_pos_request()

    async def message_tracker(self):
        async for msg in self._message_tracker_reader:
            if isinstance(msg, PctPosResponse):
                if msg.tt_addr == self._cover_writer.tt_addr:
                    self.cover.drop_pct = msg.pct_pos / 1000.0

    async def wait_for_motion_to_complete(self):
        """
        Poll for motion to complete

        Make sure that Cover.moving() is called when movement
        is initiated for this method to work reliably (see CoverWriter)
        """
        while True:
            await asyncio.sleep(self.POLLING_INTERVAL)
            if not self.cover.is_moving:
                return

    async def send_pos_request(self):
        await self._cover_writer.send_pos_request()

    async def send_close_command(self):
        await self._cover_writer.send_close_command()

    async def send_open_command(self):
        await self._cover_writer.send_open_command()

    async def send_stop_command(self):
        await self._cover_writer.send_stop_command()

    async def send_drop_pct_command(self, drop_pct):
        await self._cover_writer.send_drop_pct_command(drop_pct)

    async def send_preset_command(self, preset_num: int):
        await self._cover_writer.send_preset_command(preset_num)
