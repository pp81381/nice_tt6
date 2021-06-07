import asyncio
from nicett6.emulator.cover_emulator import TT6CoverEmulator
from unittest import IsolatedAsyncioTestCase


class TestCoverMovement(IsolatedAsyncioTestCase):
    """Test Cover movement"""

    def setUp(self):
        self.cover = TT6CoverEmulator("screen", None, 0.01, 1.77, 0.08, 1.0)

    async def test_step_movements(self):
        self.assertEqual(self.cover.step_num, 0)
        await self.cover.move_to_step_num(10)
        self.assertEqual(self.cover.step_num, 10)
        self.assertAlmostEqual(
            self.cover.percent_pos,
            (self.cover.max_steps - 10) / self.cover.max_steps,
            2,
        )
        await self.cover.move_up()
        self.assertEqual(self.cover.percent_pos, 1.0)
        self.assertEqual(self.cover.step_num, 0)
        await self.cover.move_down_step()
        self.assertEqual(self.cover.step_num, 1)
        self.assertEqual(self.cover.drop, 0.01)
        await self.cover.move_up_step()
        self.assertEqual(self.cover.step_num, 0)
        self.assertEqual(self.cover.drop, 0.0)

    async def test_pct_movements(self):
        await self.cover.move_to_percent_pos(0.95)
        self.assertAlmostEqual(self.cover.percent_pos, 0.95, 2)

    async def test_stop(self):
        mover = asyncio.create_task(self.cover.move_down())
        delay = 3
        await asyncio.sleep(delay)
        await self.cover.stop()
        await mover
        self.assertGreater(self.cover.drop, 0.19)
        self.assertLess(self.cover.drop, 0.24)

    async def test_move_while_moving(self):
        mover = asyncio.create_task(self.cover.move_down())
        delay = 3
        await asyncio.sleep(delay)
        self.assertGreater(self.cover.drop, 0.19)
        self.assertLess(self.cover.drop, 0.24)
        await self.cover.move_up()
        await mover
        self.assertEqual(self.cover.drop, 0)
