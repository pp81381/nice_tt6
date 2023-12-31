import asyncio
import logging

from nicett6.emulator.main import main

logging.basicConfig(level=logging.INFO)
asyncio.run(main())
