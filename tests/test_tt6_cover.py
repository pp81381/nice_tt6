from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from nicett6.command_code import CommandCode
from nicett6.decode import AckResponse, HexPosResponse, PctAckResponse, PctPosResponse
from nicett6.tt6_cover import TT6Cover
from nicett6.ttbus_device import TTBusDeviceAddress


class TestHandleResponsesMessage(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.cover = AsyncMock()
        self.writer = AsyncMock()
        self.tt6_cover = TT6Cover(self.tt_addr, self.cover, self.writer)

    async def test1(self):
        await self.tt6_cover.handle_response_message(PctPosResponse(self.tt_addr, 250))
        self.cover.set_drop_pct.assert_awaited_once_with(0.25)

    async def test2(self):
        await self.tt6_cover.handle_response_message(PctAckResponse(self.tt_addr, 500))
        self.cover.set_target_drop_pct_hint.assert_awaited_once_with(0.5)

    async def test3(self):
        await self.tt6_cover.handle_response_message(
            AckResponse(self.tt_addr, CommandCode.MOVE_UP)
        )
        self.cover.set_going_up.assert_awaited_once_with()

    async def test4(self):
        await self.tt6_cover.handle_response_message(
            AckResponse(self.tt_addr, CommandCode.MOVE_DOWN)
        )
        self.cover.set_going_down.assert_awaited_once_with()

    async def test5(self):
        await self.tt6_cover.handle_response_message(
            HexPosResponse(self.tt_addr, CommandCode.MOVE_POS, 0x00)
        )
        self.cover.set_target_drop_pct_hint.assert_awaited_once_with(0.0)

    async def test6(self):
        await self.tt6_cover.handle_response_message(
            HexPosResponse(self.tt_addr, CommandCode.MOVE_POS, 0xFF)
        )
        self.cover.set_target_drop_pct_hint.assert_awaited_once_with(1.0)

    async def test7(self):
        await self.tt6_cover.handle_response_message(
            AckResponse(self.tt_addr, CommandCode.MOVE_POS_1)
        )
        self.cover.moved.assert_awaited_once_with()


class TestHandleSendingMessage(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.cover = AsyncMock()
        self.writer = AsyncMock()
        self.tt6_cover = TT6Cover(self.tt_addr, self.cover, self.writer)

    async def test1(self):
        await self.tt6_cover.send_drop_pct_command(0.5)
        self.writer.send_web_move_command.assert_awaited_with(self.tt_addr, 0.5)

    async def test2(self):
        await self.tt6_cover.send_simple_command("MOVE_UP")
        self.writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_UP")
