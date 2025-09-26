# thanks kohu for this https://github.com/kohupallintrax
# <3 https://github.com/kohupallintrax/mabiproxy
# edits: bunch of type ignores


"""Varint encoder/decoder

varints are a common encoding for variable length integer data, used in
libraries such as sqlite, protobuf, v8, and more.

Here's a quick and dirty module to help avoid reimplementing the same thing
over and over again.
"""

from io import BytesIO
from math import ceil, log

import sys

if sys.version > '3':
    def _byte(b): # type: ignore
        return bytes((b, ))
else:
    def _byte(b):
        return chr(b)


def encode(number):
    """Pack `number` into varint bytes"""
    buf = b''
    while True:
        towrite = number & 0x7f
        number >>= 7
        if number:
            buf += _byte(towrite | 0x80) # type: ignore
        else:
            buf += _byte(towrite) # type: ignore
            break
    return buf

def decode_stream(stream):
    """Read a varint from `stream`"""
    shift = 0
    result = 0
    while True:
        i = _read_one(stream)
        result |= (i & 0x7f) << shift
        shift += 7
        if not (i & 0x80):
            break

    return result

def decode_bytes(buf):
    """Read a varint from from `buf` bytes"""
    return decode_stream(BytesIO(buf))


def _read_one(stream):
    """Read a byte from the file (as an integer)

    raises EOFError if the stream ends while reading bytes.
    """
    c = stream.read(1)
    if c == b'':
        raise EOFError("Unexpected EOF while reading bytes")
    return ord(c)

def varint_len(varint):
    len = ceil(log(varint,128))
    return len

