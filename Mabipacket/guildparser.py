# thanks kohu for this https://github.com/kohupallintrax
# <3 https://github.com/kohupallintrax/mabiproxy

from dataclasses import dataclass, field
import struct
import Mabipacket.varint as varint
import binascii

@dataclass
class Parameter:
    type: int
    content: bytes  # now always bytes
    name: str = field(init=False)
    value: any = field(init=False)  # type: ignore # the decoded real value

    def __post_init__(self) -> None:
        match self.type:
            case 0:
                self.name = "none"
                self.value = None
            case 1:
                self.name = "byte"
                self.value = int.from_bytes(self.content, "big", signed=False)
            case 2:
                self.name = "short"
                self.value = int.from_bytes(self.content, "big", signed=True)
            case 3:
                self.name = "int"
                self.value = int.from_bytes(self.content, "big", signed=True)
            case 4:
                self.name = "long"
                self.value = int.from_bytes(self.content, "big", signed=True)
            case 5:
                self.name = "float"
                # float assumed 4 bytes little-endian
                self.value = struct.unpack("<f", self.content)[0]
            case 6:
                self.name = "string"
                self.value = self.content.decode("utf-8", errors="replace")
            case 7:
                self.name = "bin"
                self.value = bytes(self.content)  # keep as raw bytes
            case _:
                self.name = "unknown"
                self.value = self.content


@dataclass
class Packet:
    debug: bool
    data: bytes
    header: bytes = field(init=False)
    opCode: bytes = field(init=False)
    ID: bytes = field(init=False)
    parametersCount: int = field(init=False)
    parameters: list[Parameter] = field(default_factory=list)
    _too_short: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        # Need at least 5 bytes to read packet length (bytes 3-4)
        if len(self.data) < 5:
            self.paramCount = 0
            self.header = b""
            self.opCode = b""
            self.ID = b""
            self._too_short = True
            return
            
        # Header: bytes 0-2 = magic, bytes 3-4 = packet length (LE), byte 5 = flags
        # When packet length > 255, there's an extra byte at offset 6 (7-byte header)
        pkt_len = int.from_bytes(self.data[3:5], "little")
        header_len = 7 if pkt_len > 255 else 6
        
        # Need enough data for header + opcode + ID
        if len(self.data) < header_len + 12:
            self.paramCount = 0
            self.header = self.data[0:min(header_len, len(self.data))]
            self.opCode = b""
            self.ID = b""
            self._too_short = True
            return
        
        self.header = self.data[0:header_len]
        self.opCode = self.data[header_len:header_len+4]
        self.ID = self.data[header_len+4:header_len+12]

        # After ID, there's a variable gap before parameters:
        # - 6-byte header: 1 extra byte (gap = 1)
        # - 7-byte header: 2 extra bytes (gap = 2)
        # Pattern: gap = header_len - 5
        gap = header_len - 5
        param_start = header_len + 12 + gap  # header + opcode(4) + ID(8) + gap
        
        if self.debug:
            print(f"Packet length: {pkt_len}, header_len: {header_len}, gap: {gap}, param_start: {param_start}")

        if binascii.hexlify(self.opCode).decode("ascii") == "c36f0000":
            # Guild packet - always 2 parameters (name, message)
            self.paramCount = 2
        else: 
            self.paramCount = 0


        if self.paramCount > 0:
            self.paramIndex = param_start
            for i in range(self.paramCount):
                match self.data[self.paramIndex]:
                        case 0: #None
                            self.parameters.append(Parameter(0,self.data[self.paramIndex])) # type: ignore
                            self.paramIndex += 1
                        case 1: #Byte
                            self.parameters.append(Parameter(self.data[self.paramIndex],self.data[self.paramIndex+1:self.paramIndex+2]))
                            self.paramIndex += 2
                            #print("appended byte")
                        case 2: #Short
                            self.parameters.append(Parameter(self.data[self.paramIndex],self.data[self.paramIndex+1:self.paramIndex+3]))
                            self.paramIndex += 3
                        case 3 | 5: #Int and Float
                            self.parameters.append(Parameter(self.data[self.paramIndex],self.data[self.paramIndex+1:self.paramIndex+5]))
                            self.paramIndex += 5
                        case 4: #Long
                            self.parameters.append(Parameter(self.data[self.paramIndex],self.data[self.paramIndex+1:self.paramIndex+9]))
                            self.paramIndex += 9
                        case 6 :# String
                            #string and bin have an extra byte to designate how much data is in the paramete
                            contentLength = int(self.data[self.paramIndex+1:self.paramIndex+3].hex(),16)
                            self.parameters.append(Parameter(self.data[self.paramIndex],self.data[self.paramIndex+3:self.paramIndex+contentLength+3]))
                            self.paramIndex += (contentLength + 3)
                        case 7 :# bin
                            #string and bin have an extra byte to designate how much data is in the paramete
                            contentLength = int(self.data[self.paramIndex+1:self.paramIndex+3].hex(),16)
                            #if the content length is 0 then we only have 1 byte of info tacked on the end? might just be null too. 
                            if contentLength == 0:
                                self.parameters.append(Parameter(self.data[self.paramIndex],self.data[self.paramIndex+2:self.paramIndex+3]))
                                self.paramIndex += 4
                            else:
                                self.parameters.append(Parameter(self.data[self.paramIndex],self.data[self.paramIndex+3:self.paramIndex+contentLength+3]))
                                self.paramIndex += (contentLength + 3)
                        case _:
                           if self.debug:
                            print("param match not found")

def parse(data, debug) -> Packet | bool:

    if hex(data[0]) == hex(0x88): 
        if debug:
            print(f"Encrypted Packet:{data.hex()}")
        return False
    
    #hopefully this will fix issues of failed packets
    try: 
        packet : Packet = Packet( data = data, debug = debug)
    except Exception as e:
        if debug:
            print(f"Packet construction failed: {e}")
        return False
    
    if packet.opCode.hex()=='0001d4c3': #NGS recv 7045000000000001d4c3
        return False
    
    # Too short/invalid packet - return False
    if packet._too_short:
        return False
    
    #check all parameters make sure they bytes, if not return false cause for some reason we failed to parse it
    for i in range(len(packet.parameters)):
        if type(packet.parameters[i].content) != bytes:
            if debug:
                print(f"Parameter {i} content is not bytes: {type(packet.parameters[i].content)}")
            return False
   
    if debug:
        print(f"\nheader: {packet.header.hex()} OPCode: {packet.opCode.hex()} ID: {packet.ID.hex()}")
        print(f"Total parameters: {packet.paramCount}")
        for i in range(len(packet.parameters)):
            print(f"Parameter{i} : [Type: '{packet.parameters[i].type}' Data(hex): '{''.join(f'/x{x:02x}' for x in packet.parameters[i].content)}' Name: '{packet.parameters[i].name}']")

    return packet
