import unittest
from nicett6.buffer import MessageBuffer


class TestBuffer(unittest.TestCase):
    def test_one_chunk(self):
        tests = [
            (
                "One whole message",
                b"\r",
                b"RSP 2 4 11\r",
                [b"RSP 2 4 11\r"],
                b"",
            ),
            (
                "Two whole messages",
                b"\r",
                b"RSP 2 4 11\rRSP 3 4 11\r",
                [b"RSP 2 4 11\r", b"RSP 3 4 11\r"],
                b"",
            ),
            (
                "Two whole messages with a bit on the end",
                b"\r",
                b"RSP 2 4 11\rRSP 3 4 11\rRSP 3",
                [b"RSP 2 4 11\r", b"RSP 3 4 11\r"],
                b"RSP 3",
            ),
            (
                "A zero length message embedded",
                b"\r",
                b"RSP 2 4 11\r\rRSP 3 4 11\rRSP 3",
                [b"RSP 2 4 11\r", b"\r", b"RSP 3 4 11\r"],
                b"RSP 3",
            ),
            (
                "A zero length message at start",
                b"\r",
                b"\rRSP 2 4 11\rRSP 3 4 11\rRSP 3",
                [b"\r", b"RSP 2 4 11\r", b"RSP 3 4 11\r"],
                b"RSP 3",
            ),
            (
                "Blank message",
                b"\r",
                b"",
                [],
                b"",
            ),
            (
                "Partial message",
                b"\r",
                b"RSP 3",
                [],
                b"RSP 3",
            ),
            (
                "One whole message crlf eol",
                b"\r\n",
                b"RSP 2 4 11\r\n",
                [b"RSP 2 4 11\r\n"],
                b"",
            ),
            (
                "Message inc cr crlf eol",
                b"\r\n",
                b"RSP 2\r 4 11\r\n",
                [b"RSP 2\r 4 11\r\n"],
                b"",
            ),
        ]
        for description, eol, chunk, expected_messages, expected_tail in tests:
            with self.subTest(description):
                b = MessageBuffer(eol)
                messages = b.append_chunk(chunk)
                self.assertEqual(messages, expected_messages)
                self.assertEqual(b.buf, expected_tail)

    def test_two_chunks(self):
        tests = [
            (
                "Add a partial message and then the rest",
                b"\r",
                b"RSP 3",
                b" 4 11\r",
                [],
                [b"RSP 3 4 11\r"],
                b"",
            ),
            (
                "Add a partial message and then the rest and another message and a bit",
                b"\r",
                b"RSP 2",
                b" 4 11\rRSP 3 4 11\rRSP 3",
                [],
                [b"RSP 2 4 11\r", b"RSP 3 4 11\r"],
                b"RSP 3",
            ),
            (
                "One whole message and then another whole message",
                b"\r",
                b"RSP 2 4 11\r",
                b"RSP 3 4 11\r",
                [b"RSP 2 4 11\r"],
                [b"RSP 3 4 11\r"],
                b"",
            ),
            (
                "Split multi-char eol",
                b"\r\n",
                b"RSP 2 4 11\r",
                b"\nRSP 3 4 11\r\nRSP 3",
                [],
                [b"RSP 2 4 11\r\n", b"RSP 3 4 11\r\n"],
                b"RSP 3",
            ),
        ]
        for (
            description,
            eol,
            chunk1,
            chunk2,
            expected_messages1,
            expected_messages2,
            expected_tail,
        ) in tests:
            with self.subTest(description):
                b = MessageBuffer(eol)
                messages1 = b.append_chunk(chunk1)
                messages2 = b.append_chunk(chunk2)
                self.assertEqual(messages1, expected_messages1)
                self.assertEqual(messages2, expected_messages2)
                self.assertEqual(b.buf, expected_tail)
