#!/usr/bin/env python3
"""Debug script to test guild parser with various message lengths."""

import sys
sys.path.insert(0, '/home/risk/Projects/mabi_guild_chat_sniffer')

from Mabipacket.guildparser import parse, Packet, Parameter
import struct

def make_guild_packet(name: str, message: str) -> bytes:
    """Construct a guild packet (opcode c36f0000) with two string params."""
    # Header (6 bytes) + OpCode (4) + ID (8) = 18 bytes
    header = b"\x00" * 6
    op_code = b"\xc3\x6f\x00\x00"
    id_data = b"\x00" * 8
    
    # Build parameter data - two strings (type 6)
    name_bytes = name.encode("utf-8")
    msg_bytes = message.encode("utf-8")
    
    # String format: type(1) + length(2, big-endian) + data
    param_data = bytearray()
    # Name param
    param_data.append(6)  # string type
    param_data.extend(struct.pack(">H", len(name_bytes)))
    param_data.extend(name_bytes)
    # Message param
    param_data.append(6)  # string type
    param_data.extend(struct.pack(">H", len(msg_bytes)))
    param_data.extend(msg_bytes)
    
    # Varint for message length (at offset 18)
    # This is the total parameter data length
    from Mabipacket.varint import encode
    msg_len_varint = encode(len(param_data))
    
    packet = header + op_code + id_data + msg_len_varint + param_data
    return packet

# Test various lengths
test_cases = [
    ("User", "a" * 90),    # 94 total
    ("User", "a" * 91),    # 95 total  
    ("User", "a" * 92),    # 96 total
    ("User", "a" * 95),    # 99 total
    ("User", "a" * 100),   # 104 total
    ("User", "a" * 120),   # 124 total
    ("User", "a" * 127),   # 131 total - varint still 1 byte
    ("User", "a" * 128),   # 132 total - varint becomes 2 bytes
    ("User", "a" * 200),   # 204 total
    ("LongUsername123", "a" * 200),  # >255 total - varint 2 bytes
]

print("Testing guild parser with various message lengths:\n")
for name, msg in test_cases:
    packet = make_guild_packet(name, msg)
    result = parse(packet, debug=True)
    print(f"\n{'='*60}")
    print(f"Name: '{name}' ({len(name)}), Msg: {len(msg)} chars, Total: {len(name)+len(msg)}")
    print(f"Packet len: {len(packet)}, Varint at offset 18: {packet[18]}")
    if result is False:
        print("RESULT: PARSE FAILED (returned False)")
    elif hasattr(result, 'paramCount'):
        print(f"RESULT: Parsed OK, paramCount={result.paramCount}")
        if result.parameters:
            print(f"  Param0 (name): '{result.parameters[0].value}'")
            print(f"  Param1 (msg):  '{result.parameters[1].value[:50]}...' ({len(result.parameters[1].value)} chars)")
    print(f"{'='*60}\n")