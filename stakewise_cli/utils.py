import collections
from base64 import b64decode, b64encode
from typing import List


def is_lists_equal(x: List, y: List) -> bool:
    return collections.Counter(x) == collections.Counter(y)


def bytes_to_str(value: bytes) -> str:
    return b64encode(value).decode("ascii")


def str_to_bytes(value: str) -> bytes:
    return b64decode(value)
