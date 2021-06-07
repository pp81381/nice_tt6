import asyncio
import logging
from nicett6.emulator.server import main

logging.basicConfig(level=logging.INFO)
asyncio.run(main())