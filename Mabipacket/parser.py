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

    def __post_init__(self) -> None:
        self.header = self.data[0:6]
        self.opCode = self.data[6:10]
        self.ID = self.data[10:18]

    #parse data into parameters
    #so this will ONLY parse guild packets cause for some reason
    #nexon just doesnt bother with adding the varints with it. likely because they are old packets

        self.msglenbytes = varint.decode_bytes(self.data[18:])

        if binascii.hexlify(self.opCode).decode("ascii") == "c36f0000":
            #we need do different processing cause fuck
            self.paramCount = 2
            print("guild packet")
        else: 
            #yea this isnt a guild packet lets just leave
            self.paramCount = 0


        if self.paramCount > 0:
            self.paramIndex = 19
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
                            #if the content length is 0 then we only hve 1 byte of info tacked on the end? might just be null too. 
                            if contentLength == 0:
                                self.parameters.append(Parameter(self.data[self.paramIndex],self.data[self.paramIndex+2:self.paramIndex+3]))
                                self.paramIndex += 4
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
    except:
        return False
    
    if packet.opCode.hex()=='0001d4c3': #NGS recv 7045000000000001d4c3
        return False
    
    #check all parameters make sure they bytes, if not return false cause for some reason we failed to parse it
    for i in range(len(packet.parameters)):
        if type(packet.parameters[i].content) != bytes:
            print("we failed the check dawg")
            return False
   
    if debug:
        print(f"\nheader: {packet.header.hex()} OPCode: {packet.opCode.hex()} ID: {packet.ID.hex()}")
        print(f"Total parameters: {packet.paramCount}")
        for i in range(len(packet.parameters)):
            print(f"Parameter{i} : [Type: '{packet.parameters[i].type}' Data(hex): '{''.join(f'/x{x:02x}' for x in packet.parameters[i].content)}' Name: '{packet.parameters[i].name}']")

    return packet
