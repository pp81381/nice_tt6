import asyncio
import logging
from contextlib import AsyncExitStack
from nicett6.utils import AsyncObservable

_LOGGER = logging.getLogger(__name__)


def percent_pos_to_step_num(percent_pos, max_steps):
    """ Calculate step number from percentage position.   Note that 100% means fully up."""
    return round((1 - percent_pos) * max_steps)


def step_num_to_percent_pos(step_num, max_steps):
    """ Calculate percentage position from step number.   Note that 100% means fully up."""
    return (max_steps - step_num) / max_steps


class MoverManager:
    """
    Helper class to manage cover movement

    The cover can only be moving to one position at a time.
    If a second request is made while the Cover is already moving then the
    current mover_coro is stopped by sending it a stop event and then the
    new mover_coro is initiated.
    The holder of current_mover_lock is the current mover and is supposed to
    periodically wait on stop_event (see self._sleep)
    The holder of next_mover_lock is the next mover and this routine will send a
    stop event to the current mover on its behalf
    The next_mover_lock is released as soon as the next mover aquires the
    current_mover_lock and becomes the current mover

    Note that the __init__ method creates asyncio objects that require the
    event loop to be running - you can get obscure errors in non-asyncio
    unittests if you construct an object of this type in them
    """

    def __init__(self):
        self.next_mover_lock = asyncio.Lock()
        self.current_mover_lock = asyncio.Lock()
        self.stop_event = asyncio.Event()

    async def mover_manager(self, mover_coro):
        """Make sure that only one mover_coro is active at any time"""
        async with AsyncExitStack() as next_mover_cm:
            await next_mover_cm.enter_async_context(self.next_mover_lock)
            if self.current_mover_lock.locked():
                self.stop_event.set()
            async with self.current_mover_lock:
                if self.stop_event.is_set():
                    self.stop_event.clear()
                await next_mover_cm.aclose()
                await mover_coro

    async def sleep(self, delay):
        """Sleep for delay unless interrupted by a stop_event.  Return False if stopped."""
        try:
            await asyncio.wait_for(self.stop_event.wait(), delay)
            return False
        except asyncio.TimeoutError:
            return True


class TT6CoverEmulator(AsyncObservable):
    """
    Emulate a Cover with a stepper motor that moves at a constant rate

    The step is the unit of movement and is specified in metres
    The max_drop is specified in metres (the actual drop will be rounded down to a fixed number of steps)
    The speed is specified in metres/sec
    The percent_pos is specified in percent
    1.0 = 100% = fully up; 0 = 0% = fully down

    As an example, a screen might have a 2.0m drop and the mask might have a 0.5m drop
    Both covers might move at 0.05 metres/sec in steps of 0.01 metres
    The mask would drop in 10 secs
    The screen would drop in 40 secs
    """

    def __init__(
        self, name, tt_addr, step_len, unadjusted_max_drop, speed, percent_pos
    ):
        super().__init__()
        self.name = name
        self.tt_addr = tt_addr
        if percent_pos < 0.0 or percent_pos > 1.0:
            raise ValueError(
                f"Invalid percent_pos specified for {self.name} (range is 0.0 for fully down to 1.0 for fully up)"
            )
        self.step_len = step_len
        self.unadjusted_max_drop = unadjusted_max_drop
        self.max_steps = int(self.unadjusted_max_drop // self.step_len)
        self.speed = speed
        self.step_increment = 5
        self.step_num = percent_pos_to_step_num(percent_pos, self.max_steps)
        self._mover_manager = None
        self.presets = {}

    @property
    def drop(self):
        return self.step_num * self.step_len

    @property
    def max_drop(self):
        return self.max_steps * self.step_len

    @property
    def steps_per_sec(self):
        return self.speed / self.step_len

    @property
    def percent_per_sec(self):
        return self.steps_per_sec / self.max_steps

    @property
    def percent_pos(self):
        return step_num_to_percent_pos(self.step_num, self.max_steps)

    def _get_mover_manager(self) -> MoverManager:
        if self._mover_manager is None:
            self._mover_manager = MoverManager()
        return self._mover_manager

    def log_position(self, message):
        _LOGGER.info(
            f"Pos for {self.name}: {self.percent_pos:%}, step_num {self.step_num} ({message})"
        )

    async def _move_increment(self, num_steps, notify):
        """Move an increment of num_steps.  Return False if stop event received."""
        delay = abs(self.step_len / self.speed * num_steps)
        if await self._get_mover_manager().sleep(delay):
            self.step_num += num_steps
            self.log_position(f"moved {num_steps} steps")
            if notify:
                await self.notify_observers()
            return True
        else:
            self.log_position(f"stopped")
            # TODO: Calculate partial move?   Otherwise this isn't needed.
            if notify:
                await self.notify_observers()
            return False

    async def _move_to_step_num(self, to_step_num, notify):
        if to_step_num < 0 or to_step_num > self.max_steps:
            raise ValueError(
                f"Invalid to_step_num specified for {self.name} (range is 0 for fully up to {self.max_steps} for fully down)"
            )

        if self.step_num == to_step_num:
            self.log_position("movement not needed")
            return

        self.log_position(f"movement initiated to step {to_step_num}")

        steps_to_move = to_step_num - self.step_num
        step_increment = self.step_increment * (1 if steps_to_move >= 0 else -1)
        num_whole_increments = steps_to_move // step_increment

        for _ in range(num_whole_increments):
            if not await self._move_increment(step_increment, notify):
                return

        residual_steps = steps_to_move - (num_whole_increments * step_increment)
        if not await self._move_increment(residual_steps, notify):
            return

        self.log_position(f"movement complete")

    async def move_to_step_num(self, to_step_num):
        """Move the Cover to a specific step number"""
        await self._get_mover_manager().mover_manager(
            self._move_to_step_num(to_step_num, True)
        )

    async def _move_num_steps(self, requested_steps, notify):
        """Move a relative number of steps."""
        to_step_num = self.step_num + requested_steps
        if to_step_num < 0:
            to_step_num = 0
        elif to_step_num > self.max_steps:
            to_step_num = self.max_steps
        num_steps = to_step_num - self.step_num
        if num_steps != requested_steps:
            self.log_position(
                f"requested relative movement of {requested_steps} steps limited to {num_steps} steps"
            )
        if num_steps == 0:
            self.log_position(f"relative move not needed - already at {to_step_num}")
        else:
            self.log_position(
                f"relative movement of {num_steps} steps initiated to step {to_step_num}"
            )
            await self._get_mover_manager().mover_manager(
                self._move_to_step_num(to_step_num, notify)
            )

    async def stop(self):
        """Stop any movement in progress"""
        self.log_position("stop movement requested")
        await self._get_mover_manager().mover_manager(asyncio.sleep(0))

    async def move_up(self):
        """Move to upper limit"""
        await self.move_to_step_num(0)

    async def move_down(self):
        """Move to lower limit"""
        await self.move_to_step_num(self.max_steps)

    async def move_to_percent_pos(self, to_percent_pos):
        """Move the Cover to a specific percentage position"""
        if to_percent_pos < 0.0 or to_percent_pos > 1.0:
            raise ValueError(
                f"Invalid to_percent_position specified for {self.name} (range is 0.0 for fully down to 1.0 for fully up)"
            )

        to_step_num = percent_pos_to_step_num(to_percent_pos, self.max_steps)
        self.log_position(
            f"movement initiated to {to_percent_pos} (step {to_step_num})"
        )
        await self.move_to_step_num(to_step_num)

    async def move_num_steps(self, requested_steps):
        await self._move_num_steps(requested_steps, True)

    async def move_down_step(self):
        await self._move_num_steps(1, False)

    async def move_up_step(self):
        await self._move_num_steps(-1, False)

    def init_preset(self, preset_name, pct_pos):
        self.presets[preset_name] = percent_pos_to_step_num(pct_pos, self.max_steps)

    async def move_preset(self, preset_name):
        if preset_name in self.presets:
            await self.move_to_step_num(self.presets[preset_name])

    def store_preset(self, preset_name):
        self.presets[preset_name] = self.step_num

    def del_preset(self, preset_name):
        if preset_name in self.presets:
            del self.presets[preset_name]

    def store_upper_limit(self):
        raise NotImplementedError()  # Cover will require some refactoring to support this

    def del_upper_limit(self):
        raise NotImplementedError()  # Cover will require some refactoring to support this

    def store_lower_limit(self):
        raise NotImplementedError()  # Cover will require some refactoring to support this

    def del_lower_limit(self):
        raise NotImplementedError()  # Cover will require some refactoring to support this
