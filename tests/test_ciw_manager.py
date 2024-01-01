import asyncio
from logging import WARNING
from unittest import IsolatedAsyncioTestCase
from unittest.mock import call, patch

from nicett6.ciw_helper import CIWHelper
from nicett6.ciw_manager import CIWManager
from nicett6.cover import POLLING_INTERVAL, Cover
from nicett6.cover_manager import CoverManager
from nicett6.decode import PctPosResponse
from nicett6.image_def import ImageDef
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import run_coro_after_delay
from tests import make_mock_conn

TEST_READER_POS_RESPONSE = [
    PctPosResponse(TTBusDeviceAddress(0x02, 0x04), 110),
    PctPosResponse(TTBusDeviceAddress(0x03, 0x04), 539),
    PctPosResponse(TTBusDeviceAddress(0x04, 0x04), 750),  # Address 0x04 Ignored
]


async def cleanup_task(task):
    if not task.done():
        task.cancel()
    await task


class TestCIWManager(IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = make_mock_conn(TEST_READER_POS_RESPONSE)
        patcher = patch(
            "nicett6.cover_manager.open_tt6",
            return_value=self.conn,
        )
        self.addCleanup(patcher.stop)
        patcher.start()
        self.screen_tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.mask_tt_addr = TTBusDeviceAddress(0x03, 0x04)

    async def asyncSetUp(self):
        self.mgr = CoverManager("DUMMY_SERIAL_PORT")
        await self.mgr.open()
        screen_tt6_cover = await self.mgr.add_cover(
            self.screen_tt_addr,
            Cover("Screen", 2.0),
        )
        mask_tt6_cover = await self.mgr.add_cover(
            self.mask_tt_addr,
            Cover("Mask", 0.8),
        )
        self.ciw = CIWManager(
            screen_tt6_cover,
            mask_tt6_cover,
            ImageDef(0.05, 1.8, 16 / 9),
        )

    async def test1(self):
        writer = self.conn.get_writer.return_value
        writer.send_web_on.assert_awaited_once()
        writer.send_web_pos_request.assert_has_awaits(
            [call(self.screen_tt_addr), call(self.mask_tt_addr)]
        )

    async def test2(self):
        with self.assertLogs("nicett6.cover_manager", level=WARNING) as cm:
            await self.mgr.message_tracker()
        self.assertEqual(
            cm.output,
            [
                "WARNING:nicett6.cover_manager:response message addressed to unknown device: PctPosResponse(TTBusDeviceAddress(0x04, 0x04), 750)",
            ],
        )
        helper = CIWHelper(
            self.ciw.screen_tt6_cover.cover,
            self.ciw.mask_tt6_cover.cover,
            self.ciw.image_def,
        )
        self.assertIsNotNone(helper.aspect_ratio)
        if helper.aspect_ratio is not None:
            self.assertAlmostEqual(helper.aspect_ratio, 2.3508668821627974)

    async def test3(self):
        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, False)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        task = asyncio.create_task(self.ciw.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)
        self.assertEqual(task.done(), False)
        await asyncio.sleep(POLLING_INTERVAL + 0.1)
        self.assertEqual(task.done(), True)
        await task

    async def test4(self):
        await self.ciw.screen_tt6_cover.cover.moved()
        task = asyncio.create_task(self.ciw.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(POLLING_INTERVAL + 0.1)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, False)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), True)
        await task

    async def test5(self):
        await self.ciw.screen_tt6_cover.cover.moved()
        asyncio.create_task(
            run_coro_after_delay(
                self.ciw.mask_tt6_cover.cover.moved(), POLLING_INTERVAL + 0.2
            )
        )
        task = asyncio.create_task(self.ciw.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(POLLING_INTERVAL + 0.1)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(0.2)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL - 0.2)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, False)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(0.3)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, False)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), True)
        await task

    async def test7(self):
        await self.ciw.send_simple_command("MOVE_UP")
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_has_awaits(
            [
                call(self.screen_tt_addr, "MOVE_UP"),
                call(self.mask_tt_addr, "MOVE_UP"),
            ]
        )
