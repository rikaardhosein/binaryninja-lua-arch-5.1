import struct
import traceback

from binaryninja import Architecture, BinaryView, SegmentFlag, log_error

header_sig_const = bytearray([0x1b, 0x4c, 0x75, 0x61])
header_block_len = 12  #Header block is always 12 bytes in size

#Helper functions


def parse_header_block(data):
    # Implement this another time
    # For now, just skip past it.
    # We need to return the length, because
    # This is going to be added to the length
    # of the "instruction" parsed so that
    # it will skip over this amount
    # of memory when processing the next
    # instruction.
    return None, header_block_len


def parse_function_block(start, reader):
    #String source name
    #Integer line defined
    #Integer last line defined
    #1 byte number of upvalues
    #1 byte number of parameters
    #1 byte is_vararg flag (see explanation further below)
    #• 1=VARARG_HASARG
    #• 2=VARARG_ISVARARG
    #• 4=VARARG_NEEDSARG
    #1 byte maximum stack size (number of registers used)
    #List list of instructions (code)
    #List list of constants
    #List list of function prototypes
    #List source line positions (optional debug data)
    #List list of locals (optional debug data)
    #List list of upvalues (optional debug data)

    instruction_size = 4

    addr = start
    source_name_len = struct.unpack('<L', reader.read(addr, 4))[0]
    addr += 4
    source_name = reader.read(addr, source_name_len)[0]
    addr += source_name_len
    line_defined, last_line_defined = struct.unpack('<2L', reader.read(
        addr, 8))
    addr += 8
    num_upvalues, num_params, is_vararg, max_stack_size = struct.unpack(
        '<4B', reader.read(addr, 4))
    addr += 4

    code_size = struct.unpack('<L'.reader.read(addr, 4))[0]
    addr += 4

    func_object = {}
    code = func_object['code'] = {}
    code['start'] = addr
    code['size'] = code_size * instruction_size

    return func_object


class LuaBytecodeView(BinaryView):
    name = "LuaByteCode"
    long_name = "LuaBytecode"

    def __init__(self, data):
        BinaryView.__init__(self, file_metadata=data.file, parent_view=data)
        self.raw = data

    @classmethod
    def is_valid_for_data(self, data):
        return True

    def init(self):
        try:
            self.platform = Architecture['luabytecode'].standalone_platform
            self.arch = Architecture['luabytecode']

            top_level_func = parse_function_block(header_block_len)
            self.entry_addr = top_level_func['code']['start']

            self.add_entry_point(self.entry_addr)

            self.add_auto_segment(
                self.entry_addr, top_level_func['code']['size'],
                self.entry_addr, top_level_func['code']['size'],
                SegmentFlag.SegmentExecutable | SegmentFlag.SegmentReadable)
        except:
            log_error(traceback.format_exc())
            return False

        return True

    def perform_is_executable(self):
        return True

    def perform_get_entry_point(self):
        return self.entry_addr


LuaBytecodeView.register()
