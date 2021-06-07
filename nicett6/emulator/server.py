import asyncio
from nicett6.emulator.config import build_config
from nicett6.emulator.controller import make_tt6controller


async def main():
    await asyncio.sleep(0)
    config = build_config()
    with make_tt6controller(config["web_on"], config["covers"]) as controller:
        await controller.run_server(config["port"])
