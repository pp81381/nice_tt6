class MessageBuffer:
    """Buffer that accumulates chunks of bytes and emits messages"""

    def __init__(self, eol):
        self.buf = bytearray()
        self.eol = eol

    def append_chunk(self, chunk):
        self.buf += chunk
        messages = []
        while True:
            iX = self.buf.find(self.eol)
            if iX == -1:
                break
            messages.append(self.buf[: iX + len(self.eol)])
            del self.buf[: iX + len(self.eol)]
        return messages
