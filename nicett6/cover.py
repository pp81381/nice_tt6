import asyncio
import logging
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.connection import TT6Writer
from nicett6.utils import AsyncObservable, AsyncObserver, check_pct
import time

_LOGGER = logging.getLogger(__name__)

POLLING_INTERVAL = 0.2


class Cover(AsyncObservable):
    """A sensor class that can be used to monitor the position of a cover"""

    MOVEMENT_THRESHOLD_INTERVAL = 2.7
    IS_CLOSED_PCT = 0.95

    def __init__(self, name, max_drop):
        super().__init__()
        self.name = name
        self.max_drop = max_drop
        self._drop_pct = 1.0
        self._prev_movement = time.perf_counter() - self.MOVEMENT_THRESHOLD_INTERVAL
        self._prev_drop_pct = self._drop_pct

    def __repr__(self):
        return (
            f"Cover: {self.name}, {self.max_drop}, "
            f"{self._drop_pct}, {self._prev_drop_pct}, "
            f"{self._prev_movement}"
        )

    def log(self, msg, loglevel=logging.DEBUG):
        _LOGGER.log(
            loglevel,
            f"{msg}; "
            f"name: {self.name}; "
            f"max_drop: {self.max_drop}; "
            f"drop_pct: {self.drop_pct}; "
            f"_prev_drop_pct: {self._prev_drop_pct}; "
            f"is_moving: {self.is_moving}; "
            f"is_opening: {self.is_opening}; "
            f"is_closing: {self.is_closing}; "
            f"is_closed: {self.is_closed}; ",
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

    async def set_idle(self):
        """Called to indicate that movement has finished"""
        self._prev_drop_pct = self._drop_pct
        self._prev_movement = time.perf_counter() - self.MOVEMENT_THRESHOLD_INTERVAL
        await self.notify_observers()

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

    async def set_closing(self):
        """Force the state to is_closing"""
        self._prev_drop_pct = self._drop_pct - 0.0001
        await self.moved()

    async def set_opening(self):
        """Force the state to is_opening"""
        self._prev_drop_pct = self._drop_pct + 0.0001
        await self.moved()

    async def set_target_drop_pct_hint(self, target_drop_pct):
        """"Force the state to is_opening/closing based on target drop_pct"""
        if target_drop_pct < self._drop_pct:
            await self.set_opening()
        elif target_drop_pct > self._drop_pct:
            await self.set_closing()


class TT6Cover:
    """Class that sends commands to a `Cover` that is connected to the TTBus"""

    def __init__(self, tt_addr, cover, writer):
        self.tt_addr: TTBusDeviceAddress = tt_addr
        self.cover: Cover = cover
        self.writer: TT6Writer = writer
        self._notifier = PostMovementNotifier()

    def enable_notifier(self):
        self.cover.attach(self._notifier)

    async def disable_notifier(self):
        self.cover.detach(self._notifier)
        await self._notifier.cleanup()

    async def send_pos_request(self):
        await self.writer.send_web_pos_request(self.tt_addr)

    async def send_drop_pct_command(self, drop_pct):
        _LOGGER.debug(f"moving {self.cover.name} to {drop_pct}")
        await self.writer.send_web_move_command(self.tt_addr, drop_pct)

    async def send_close_command(self):
        _LOGGER.debug(f"sending MOVE_UP to {self.cover.name}")
        await self.writer.send_simple_command(self.tt_addr, "MOVE_UP")

    async def send_open_command(self):
        _LOGGER.debug(f"sending MOVE_DOWN to {self.cover.name}")
        await self.writer.send_simple_command(self.tt_addr, "MOVE_DOWN")

    async def send_preset_command(self, preset_num: int):
        preset_command = f"MOVE_POS_{preset_num:d}"
        _LOGGER.debug(f"sending {preset_command} to {self.cover.name}")
        await self.writer.send_simple_command(self.tt_addr, preset_command)

    async def send_stop_command(self):
        _LOGGER.debug(f"sending STOP to {self.cover.name}")
        await self.writer.send_simple_command(self.tt_addr, "STOP")


async def wait_for_motion_to_complete(covers):
    """
    Poll for motion to complete

    Make sure that Cover.moving() is called when movement
    is initiated for this method to work reliably
    (see CoverManager._handle_response_message_for_cover)
    Has the side effect of notifying observers of the idle state
    """
    while True:
        await asyncio.sleep(POLLING_INTERVAL)
        if all([not cover.is_moving for cover in covers]):
            return


class PostMovementNotifier(AsyncObserver):
    """Invokes notify_observers one last time after movement stops"""

    POST_MOVEMENT_ALLOWANCE = 0.05

    def __init__(self):
        super().__init__()
        self._task_lock = asyncio.Lock()
        self._task = None

    async def update(self, cover: Cover) -> None:
        """Reset the task if the state of the Cover changes"""
        async with self._task_lock:
            await self._cancel_task()
            if cover.is_moving:  # Only need a new task if moving, plus avoid recursion
                self._task = asyncio.create_task(self._set_idle_after_delay(cover))
                cover.log("PostMovementNotifier task started", logging.DEBUG)

    async def _set_idle_after_delay(self, cover: Cover):
        await asyncio.sleep(
            cover.MOVEMENT_THRESHOLD_INTERVAL + self.POST_MOVEMENT_ALLOWANCE
        )
        await cover.set_idle()
        cover.log("PostMovementNotifier sent idle", logging.DEBUG)

    async def cleanup(self):
        _LOGGER.debug(f"PostMovementNotifier cleanup")
        async with self._task_lock:
            await self._cancel_task()

    async def _cancel_task(self):
        """Cancel task - make sure you have acquired the lock first"""
        if self._task is not None:
            if not self._task.done():
                _LOGGER.debug(f"PostMovementNotifier cancelling an active task")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None