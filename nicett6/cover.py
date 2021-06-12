import logging
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.connection import TT6Writer
from nicett6.utils import AsyncObservable, check_pct
import time

_LOGGER = logging.getLogger(__name__)


class Cover(AsyncObservable):
    """A sensor class that can be used to monitor the position of a cover"""

    MOVEMENT_THRESHOLD_INTERVAL = 2.0
    IS_CLOSED_PCT = 0.95

    def __init__(self, name, max_drop):
        super().__init__()
        self.name = name
        self.max_drop = max_drop
        self._drop_pct = 1.0
        self._prev_movement = time.perf_counter() - self.MOVEMENT_THRESHOLD_INTERVAL
        self._was_moving = False
        self._prev_drop_pct = self._drop_pct

    def __repr__(self):
        return (
            f"Cover: {self.name}, {self.max_drop}, "
            f"{self._drop_pct}, {self._prev_drop_pct}, "
            f"{self._prev_movement}"
        )

    @property
    def drop_pct(self):
        return self._drop_pct

    async def set_drop_pct(self, value):
        """Drop as a percentage (0.0 fully down to 1.0 fully up)"""
        prev_drop_pct = self._drop_pct  # Preserve state in case of exception
        self._drop_pct = check_pct(f"{self.name} drop", value)
        self._prev_drop_pct = prev_drop_pct
        await self.moved()

    @property
    def drop(self):
        return (1.0 - self._drop_pct) * self.max_drop

    async def moved(self):
        """Called to indicate movement"""
        self._prev_movement = time.perf_counter()
        await self.notify_observers()

    async def check_for_idle(self):
        """Used to notify observers that movement has completed"""
        if self.is_moving:
            self._was_moving = True
        elif self._was_moving:
            self._was_moving = False
            await self.notify_observers()
        return not self._was_moving

    @property
    def is_moving(self):
        """
        Returns True if the cover has moved recently

        When initiating movement, call self.moved() so that self.is_moving
        will be meaningful before the first POS message comes back from the cover
        """
        return (
            time.perf_counter() - self._prev_movement
            <= self.MOVEMENT_THRESHOLD_INTERVAL
        )

    @property
    def is_closed(self):
        """Returns True if the cover is fully up (opposite of a blind)"""
        return not self.is_moving and self.drop_pct > self.IS_CLOSED_PCT

    @property
    def is_closing(self):
        """
        Returns True if the cover is going up (opposite of a blind)

        Will only be meaningful after drop_pct has been set by the first
        POS message coming back from the cover for a movement
        """
        return self.is_moving and self._drop_pct > self._prev_drop_pct

    @property
    def is_opening(self):
        """
        Returns True if the cover is going down (opposite of a blind)

        Will only be meaningful after drop_pct has been set by the first
        POS message coming back from the cover for a movement
        """
        return self.is_moving and self._drop_pct < self._prev_drop_pct


class TT6Cover:
    """Class that sends commands to a `Cover` that is connected to the TTBus"""

    def __init__(self, tt_addr, cover, writer):
        self.tt_addr: TTBusDeviceAddress = tt_addr
        self.cover: Cover = cover
        self.writer: TT6Writer = writer

    async def send_pos_request(self):
        await self.writer.send_web_pos_request(self.tt_addr)

    async def send_drop_pct_command(self, drop_pct):
        _LOGGER.debug(f"moving {self.cover.name} to {drop_pct}")
        await self.writer.send_web_move_command(self.tt_addr, drop_pct)
        await self.cover.moved()

    async def send_close_command(self):
        _LOGGER.debug(f"sending MOVE_UP to {self.cover.name}")
        # Could also be implemented by setting drop_pct to 1.0
        await self.writer.send_simple_command(self.tt_addr, "MOVE_UP")
        await self.cover.moved()

    async def send_open_command(self):
        _LOGGER.debug(f"sending MOVE_DOWN to {self.cover.name}")
        # Could also be implemented by setting drop_pct to 0.0
        await self.writer.send_simple_command(self.tt_addr, "MOVE_DOWN")
        await self.cover.moved()

    async def send_preset_command(self, preset_num: int):
        preset_command = f"MOVE_POS_{preset_num:d}"
        _LOGGER.debug(f"sending {preset_command} to {self.cover.name}")
        await self.writer.send_simple_command(self.tt_addr, preset_command)
        await self.cover.moved()

    async def send_stop_command(self):
        _LOGGER.debug(f"sending STOP to {self.cover.name}")
        await self.writer.send_simple_command(self.tt_addr, "STOP")
        await self.cover.moved()