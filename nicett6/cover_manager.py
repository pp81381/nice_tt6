import asyncio
from nicett6.connection import TT6Connection, TT6Writer, TT6Reader
from nicett6.cover import Cover, TT6CoverWriter
from nicett6.decode import PctPosResponse
from nicett6.ttbus_device import TTBusDeviceAddress


class CoverManager:

    POLLING_INTERVAL = 0.2

    def __init__(
        self,
        serial_port: str,
        cover_tt_addr: TTBusDeviceAddress,
        cover_max_drop: float,
    ):
        self._serial_port = serial_port
        self._cover_tt_addr = cover_tt_addr
        self.cover = Cover("Cover", cover_max_drop)
        self._message_tracker_reader: TT6Reader = None
        self._writer: TT6Writer = None
        self._cover_writer: TT6CoverWriter = None

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        self.close()

    async def open(self):
        self._conn = TT6Connection()
        await self._conn.open(self._serial_port)
        # NOTE: reader is created here rather than in message_tracker
        # to ensure that all messages from this moment on are captured
        self._message_tracker_reader: TT6Reader = self._conn.add_reader()
        self._writer = self._conn.get_writer()
        self._cover_writer = TT6CoverWriter(
            self._cover_tt_addr, self.cover, self._writer
        )
        await self._start()

    def close(self):
        self._conn.close()
        self._conn = None
        self._message_tracker_reader = None
        self._writer = None
        self._cover_writer = None

    async def _start(self):
        await self._writer.send_web_on()
        await self.send_pos_request()

    async def message_tracker(self):
        async for msg in self._message_tracker_reader:
            if isinstance(msg, PctPosResponse):
                if msg.tt_addr == self._cover_writer.tt_addr:
                    await self.cover.set_drop_pct(msg.pct_pos / 1000.0)

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
