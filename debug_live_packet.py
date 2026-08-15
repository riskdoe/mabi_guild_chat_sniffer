#!/usr/bin/env python3
"""Test actual captured packet payloads from the game."""

import sys
sys.path.insert(0, '/home/risk/Projects/mabi_guild_chat_sniffer')

from Mabipacket.guildparser import parse

# Paste a raw packet hex here from your logs/tcpdump
# Example: "8800..." or "000000000000c36f0000..."
test_hex = input("Paste packet hex (or press Enter to skip): ").strip()

if test_hex:
    payload_bytes = bytes.fromhex(test_hex.replace(":", "").replace(" ", ""))
    print(f"\nPacket length: {len(payload_bytes)}")
    print(f"First byte: {hex(payload_bytes[0])}")
    print(f"Opcode (6-10): {payload_bytes[6:10].hex()}")
    print(f"Byte at offset 18: {payload_bytes[18] if len(payload_bytes) > 18 else 'N/A'}")
    
    result = parse(payload_bytes, debug=True)
    if result is False:
        print("PARSE FAILED")
    else:
        print(f"Parsed OK: paramCount={result.paramCount}")
        for i, p in enumerate(result.parameters):
            print(f"  Param{i}: type={p.type}, value='{p.value}'")
else:
    print("No packet provided. Run with a hex string to test.")

# Also test: what does a 96-char message look like in hex?
print("\n--- Expected 96-char message structure ---")
# header(6) + opcode(4) + id(8) + varint(1) + name_param + msg_param
# name="User" (4 chars) = 1+2+4 = 7 bytes
# msg="a"*96 = 1+2+96 = 99 bytes
# varint encodes 7+99=106 = 0x6a (1 byte)
# Total: 6+4+8+1+7+99 = 125 bytes
print("Packet should be ~125 bytes for 96-char message with 4-char name")
print("Varint at offset 18 should be 0x6a (106 decimal)")
print("If offset 18 is >= 0x80, varint is 2+ bytes - parser needs to handle that")