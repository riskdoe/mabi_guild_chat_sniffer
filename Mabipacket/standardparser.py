from dataclasses import dataclass, field
import struct

@dataclass
class Parameter:
    type: int
    content: bytearray
    name: str = field(init=False)

    def __post_init__(self) -> None:
        match self.type:
            case 0:
                self.name = "none"
            case 1:
                self.name = "byte"
            case 2:
                self.name = "short"
            case 3:
                self.name = "int"
            case 4:
                self.name = "long"
            case 5:
                self.name = "float"
            case 6:
                self.name = "string"
            case 7:
                self.name = "bin"


def decode_varint(data, offset):
    """Decode varint and return (value, bytes_read)"""
    result = 0
    shift = 0
    bytes_read = 0
    
    while bytes_read < 5:  # Max 5 bytes for uint32
        if offset + bytes_read >= len(data):
            raise ValueError("Unexpected end of data while reading varint")
        
        byte = data[offset + bytes_read]
        bytes_read += 1
        
        result |= (byte & 0x7F) << shift
        shift += 7
        
        if not (byte & 0x80):  # High bit not set = end of varint
            break
    
    return result, bytes_read


@dataclass
class Packet:
    debug: bool
    source: str
    data: bytes
    header: bytes = field(init=False)
    opCode: bytes = field(init=False)
    ID: bytes = field(init=False)
    paramCount: int = field(init=False)
    parameters: list[Parameter] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.data) < 18:
            raise ValueError("Packet too short")
        
        # Header structure (first 6 bytes - not used much)
        self.header = self.data[0:6]
        
        # OpCode (4 bytes, big endian)
        self.opCode = self.data[6:10]
        
        # ID/CID (8 bytes, big endian)
        self.ID = self.data[10:18]
        
        offset = 18
        
        # Body length (varint)
        try:
            body_length, varint_len = decode_varint(self.data, offset)
            offset += varint_len
            
            # Parameter count (varint)
            self.paramCount, varint_len = decode_varint(self.data, offset)
            offset += varint_len
            
            # Skip the 0x00 separator
            offset += 1
            
        except (ValueError, IndexError) as e:
            if self.debug:
                print(f"Failed to decode varints: {e}")
            self.paramCount = 0
            return
        
        # Parse parameters
        if self.paramCount > 0:
            # Sanity check
            if self.paramCount > 1000:
                if self.debug:
                    print(f"Suspicious param count: {self.paramCount}, skipping parse")
                self.paramCount = 0
                return
            
            for i in range(self.paramCount):
                if offset >= len(self.data):
                    if self.debug:
                        print(f"Ran out of data at parameter {i}")
                    break
                
                param_type = self.data[offset]
                
                try:
                    if param_type == 0:  # None
                        self.parameters.append(Parameter(0, bytearray()))
                        offset += 1
                    
                    elif param_type == 1:  # Byte
                        self.parameters.append(Parameter(1, bytearray(self.data[offset+1:offset+2])))
                        offset += 2
                    
                    elif param_type == 2:  # Short (2 bytes, big endian)
                        self.parameters.append(Parameter(2, bytearray(self.data[offset+1:offset+3])))
                        offset += 3
                    
                    elif param_type == 3:  # Int (4 bytes, big endian)
                        self.parameters.append(Parameter(3, bytearray(self.data[offset+1:offset+5])))
                        offset += 5
                    
                    elif param_type == 4:  # Long (8 bytes, big endian)
                        self.parameters.append(Parameter(4, bytearray(self.data[offset+1:offset+9])))
                        offset += 9
                    
                    elif param_type == 5:  # Float (4 bytes)
                        self.parameters.append(Parameter(5, bytearray(self.data[offset+1:offset+5])))
                        offset += 5
                    
                    elif param_type == 6:  # String
                        # Length is 2 bytes, big endian
                        str_len = struct.unpack('>H', self.data[offset+1:offset+3])[0]
                        self.parameters.append(Parameter(6, bytearray(self.data[offset+3:offset+3+str_len])))
                        offset += 3 + str_len
                    
                    elif param_type == 7:  # Binary
                        # Length is 2 bytes, big endian
                        bin_len = struct.unpack('>H', self.data[offset+1:offset+3])[0]
                        self.parameters.append(Parameter(7, bytearray(self.data[offset+3:offset+3+bin_len])))
                        offset += 3 + bin_len
                    
                    else:
                        if self.debug:
                            print(f"Unknown param type: {param_type} at offset {offset}")
                        break
                
                except (struct.error, IndexError) as e:
                    if self.debug:
                        print(f"Error parsing parameter {i}: {e}")
                    break


def parse(data, debug):
    if len(data) > 0 and data[0] == 0x88:
        if debug:
            print(f"Encrypted Packet: {direction} {data.hex()}")
        return None
    
    try:
        packet = Packet(source=direction, data=data, debug=debug)
    except Exception as e:
        if debug:
            print(f"Failed to create packet: {e}")
        return None
    
    # Filter out NGS packets
    if packet.opCode.hex() == '0001d4c3':
        return None
    
    if debug:
        print(f"[{direction}({port})] {data.hex()}")
        print(f"{direction} - header: {packet.header.hex()} OpCode: {packet.opCode.hex()} ID: {packet.ID.hex()}")
        print(f"Total parameters: {packet.paramCount}")
        for i, param in enumerate(packet.parameters):
            print(f"Parameter{i}: [Type: '{param.type}' Data(hex): '{param.content.hex()}' Name: '{param.name}']")
    
    return packet