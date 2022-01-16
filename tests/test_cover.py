import asyncio
from unittest.mock import AsyncMock
from nicett6.ttbus_device import TTBusDeviceAddress
from unittest import IsolatedAsyncioTestCase
from nicett6.cover import Cover, TT6Cover, wait_for_motion_to_complete


class TestCover(IsolatedAsyncioTestCase):
    def setUp(self):
        self.cover = Cover("Test", 0.8)

    def tearDown(self) -> None:
        self.cover = None

    async def test1(self):
        self.assertAlmostEqual(self.cover.drop_pct, 1.0)
        self.assertAlmostEqual(self.cover.drop, 0)

    async def test2(self):
        await self.cover.set_drop_pct(0.0)
        self.assertAlmostEqual(self.cover.drop, 0.8)

    async def test3(self):
        await self.cover.set_drop_pct(0.5)
        self.assertAlmostEqual(self.cover.drop, 0.4)

    async def test4(self):
        with self.assertRaises(ValueError):
            await self.cover.set_drop_pct(-0.1)

    async def test5(self):
        with self.assertRaises(ValueError):
            await self.cover.set_drop_pct(1.1)

    async def test6(self):
        self.assertEqual(self.cover.is_moving, False)
        self.assertEqual(self.cover.is_closed, True)

    async def test7(self):
        await self.cover.set_drop_pct(0.5)
        self.assertEqual(self.cover.is_closed, False)
        self.assertEqual(self.cover.is_moving, True)
        self.assertEqual(self.cover.is_opening, True)
        self.assertEqual(self.cover.is_closing, False)
        await asyncio.sleep(self.cover.MOVEMENT_THRESHOLD_INTERVAL + 0.1)
        self.assertEqual(self.cover.is_closed, False)
        self.assertEqual(self.cover.is_moving, False)
        self.assertEqual(self.cover.is_opening, False)
        self.assertEqual(self.cover.is_closing, False)
        await self.cover.set_drop_pct(0.5)
        # Not really a movement but we don't know whether
        # it's the first of a sequence of pos messages
        self.assertEqual(self.cover.is_moving, True)
        await self.cover.set_drop_pct(1.0)
        self.assertEqual(self.cover.is_closed, False)
        self.assertEqual(self.cover.is_moving, True)
        self.assertEqual(self.cover.is_opening, False)
        self.assertEqual(self.cover.is_closing, True)
        await asyncio.sleep(self.cover.MOVEMENT_THRESHOLD_INTERVAL + 0.1)
        self.assertEqual(self.cover.is_closed, True)
        self.assertEqual(self.cover.is_moving, False)
        self.assertEqual(self.cover.is_opening, False)
        self.assertEqual(self.cover.is_closing, False)

    async def test8(self):
        """Emulate a sequence of movement messages coming in"""

        tests = [
            ("Init state", None, 0.0, 1.0, True, False, False, False),
            ("After down web cmd", 1.0, 0.0, 1.0, False, True, False, False),
            ("Down step 1", 0.9, 0.0, 0.9, False, True, True, False),
            ("Down step 2", 0.8, 0.0, 0.8, False, True, True, False),
            ("Final step down", 0.7, 0.0, 0.7, False, True, True, False),
            (
                "Idle after down",
                None,
                self.cover.MOVEMENT_THRESHOLD_INTERVAL + 0.1,
                0.7,
                False,
                False,
                False,
                False,
            ),
            ("After up web cmd", 0.7, 0.0, 0.7, False, True, False, False),
            ("Up step 1", 0.8, 0.0, 0.8, False, True, False, True),
            ("Up step 2", 0.9, 0.0, 0.9, False, True, False, True),
            ("Final step up", 1.0, 0.0, 1.0, False, True, False, True),
            (
                "Idle after up",
                None,
                self.cover.MOVEMENT_THRESHOLD_INTERVAL + 0.1,
                1.0,
                True,
                False,
                False,
                False,
            ),
        ]

        for (
            name,
            drop_pct_to_set,
            sleep_before_check,
            drop_pct,
            is_closed,
            is_moving,
            is_opening,
            is_closing,
        ) in tests:
            with self.subTest(name):
                if drop_pct_to_set is not None:
                    await self.cover.set_drop_pct(drop_pct_to_set)
                await asyncio.sleep(sleep_before_check)
                self.assertAlmostEqual(self.cover.drop_pct, drop_pct)
                self.assertEqual(self.cover.is_closed, is_closed)
                self.assertEqual(self.cover.is_moving, is_moving)
                self.assertEqual(self.cover.is_opening, is_opening)
                self.assertEqual(self.cover.is_closing, is_closing)

    async def test_wait_for_motion_to_complete(self):
        self.assertFalse(self.cover.is_moving)
        await self.cover.moved()
        self.assertTrue(self.cover.is_moving)
        await wait_for_motion_to_complete([self.cover])
        self.assertFalse(self.cover.is_moving)

    async def test10(self):
        self.assertTrue(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        await self.cover.set_drop_pct(0.8)
        self.assertAlmostEqual(self.cover._prev_drop_pct, 1.0)
        self.assertFalse(self.cover.is_closed)
        self.assertTrue(self.cover.is_moving)
        self.assertTrue(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        await asyncio.sleep(self.cover.MOVEMENT_THRESHOLD_INTERVAL + 0.01)
        self.assertAlmostEqual(self.cover._prev_drop_pct, 1.0)  #!!
        self.assertFalse(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        await self.cover.set_idle()
        self.assertAlmostEqual(self.cover._prev_drop_pct, 0.8)  # !!
        self.assertFalse(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        await self.cover.moved()  # We are moving but we don't know the direction yet
        self.assertAlmostEqual(self.cover._prev_drop_pct, 0.8)
        self.assertFalse(self.cover.is_closed)
        self.assertTrue(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)

    async def test11(self):
        self.assertTrue(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        await self.cover.set_closing()
        self.assertFalse(self.cover.is_closed)
        self.assertTrue(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertTrue(self.cover.is_closing)

    async def test12(self):
        self.assertTrue(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        await self.cover.set_opening()
        self.assertFalse(self.cover.is_closed)
        self.assertTrue(self.cover.is_moving)
        self.assertTrue(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)

    async def test13(self):
        self.assertTrue(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        await self.cover.set_target_drop_pct_hint(0.5)
        self.assertFalse(self.cover.is_closed)
        self.assertTrue(self.cover.is_moving)
        self.assertTrue(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)

    async def test14(self):
        await self.cover.set_drop_pct(0.0)
        await asyncio.sleep(self.cover.MOVEMENT_THRESHOLD_INTERVAL + 0.01)
        self.assertFalse(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        await self.cover.set_target_drop_pct_hint(0.5)
        self.assertFalse(self.cover.is_closed)
        self.assertTrue(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertTrue(self.cover.is_closing)
