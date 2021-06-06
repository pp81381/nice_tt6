import asyncio
import logging
from nice_tt6.emulator.server import main

logging.basicConfig(level=logging.INFO)
asyncio.run(main())