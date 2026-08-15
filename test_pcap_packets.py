#!/usr/bin/env python3
"""Test parser with actual captured packets from pcap."""

import sys
sys.path.insert(0, '/home/risk/Projects/mabi_guild_chat_sniffer')

from Mabipacket.guildparser import parse

# Actual packets from capture.pcap (TCP payload only)
packets = [
    # Packet 1 - short message (91 chars) - WORKS
    bytes.fromhex("555e007a0000c36f00000000000000007a02000600055269736b0006005b6161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161"),
    
    # Packet 3 - medium message (96 chars) - WORKS  
    bytes.fromhex("55e0007f0000c36f00000000000000007f02000600055269736b00060060616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161613636363636"),
    
    # Packet 4 - long message (128+ chars) - WAS BROKEN (shifted by 1 byte)
    bytes.fromhex("55ad0080010000c36f0000000000000000800102000600055269736b0006006161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161363636363636"),
]

print("Testing actual captured packets:\n")
for i, pkt in enumerate(packets, 1):
    print(f"{'='*60}")
    print(f"Packet {i} (len={len(pkt)})")
    print(f"Header bytes 3-4 (LE length): {int.from_bytes(pkt[3:5], 'little')}")
    print(f"Header byte 5: {pkt[5]:02x}")
    print(f"Byte at offset 6: {pkt[6]:02x}")
    print(f"Opcode at offset 6: {pkt[6:10].hex()}")
    print(f"Opcode at offset 7: {pkt[7:11].hex()}")
    
    result = parse(pkt, debug=True)
    
    if result is False:
        print("RESULT: PARSE FAILED (returned False)")
    elif hasattr(result, 'paramCount'):
        print(f"RESULT: Parsed OK, paramCount={result.paramCount}")
        if result.parameters:
            print(f"  Param0 (name): '{result.parameters[0].value}'")
            print(f"  Param1 (msg):  '{result.parameters[1].value[:60]}...' ({len(result.parameters[1].value)} chars)")
    print(f"{'='*60}\n")