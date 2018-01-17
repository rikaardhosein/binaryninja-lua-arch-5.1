#!/usr/bin/env python
from struct import unpack

from binaryninja import *

opcodes = {
    0: 'MOVE',  #Copy a value between registers
    1: 'LOADK',  #Load a constant into a register
    2: 'LOADBOOL',  #Load a boolean into a register
    3: 'LOADNIL',  #Load nil values into a range of registers
    4: 'GETUPVAL',  #Read an upvalue into a register
    5: 'GETGLOBAL',  #Read a global variable into a register
    6: 'GETTABLE',  #Read a table element into a register
    7: 'SETGLOBAL',  #Write a register value into a global variable
    8: 'SETUPVAL',  #Write a register value into an upvalue
    9: 'SETTABLE',  #Write a register value into a table element
    10: 'NEWTABLE',  #Create a new table
    11: 'SELF',  #Prepare an object method for calling
    12: 'ADD',  #Addition operator
    13: 'SUB',  #Subtraction operator
    14: 'MUL',  #Multiplication operator
    15: 'DIV',  #Division operator
    16: 'MOD',  #Modulus (remainder) operator
    17: 'POW',  #Exponentiation operator
    18: 'UNM',  #Unary minus operator
    19: 'NOT',  #Logical NOT operator
    20: 'LEN',  #Length operator
    21: 'CONCAT',  #Concatenate a range of registers
    22: 'JMP',  #Unconditional jump
    23: 'EQ',  #Equality test
    24: 'LT',  #Less than test
    25: 'LE',  #Less than or equal to test
    26: 'TEST',  #Boolean test, with conditional jump
    27: 'TESTSET',  #Boolean test, with conditional jump and assignment
    28: 'CALL',  #Call a closure
    29: 'TAILCALL',  #Perform a tail call
    30: 'RETURN',  #Return from function call
    31: 'FORLOOP',  #Iterate a numeric for loop
    32: 'FORPREP',  #Initialization for a numeric for loop
    33: 'TFORLOOP',  #Iterate a generic for loop
    34: 'SETLIST',  #Set a range of array elements for a table
    35: 'CLOSE',  #Close a range of locals being used as upvalues
    36: 'CLOSURE',  #Create a closure of a function prototype
    37: 'VARARG'  #Assign vararg function arguments to registers
}

#instruction_types
iABC = 0
iA = 5
iAB = 1
iAC = 2
iABx = 3
iAsBx = 4
isBx = 6


def get_var(s, l, data):
    val = 0L
    mask = long((2**l) - 1) << s
    val = ((data & mask) >> s)
    return val


operand_decode_func = {
    iABC: lambda x: (get_var(6, 8, x), get_var(23, 9, x), get_var(14, 9, x)),
    iA: lambda x: (get_var(6, 8, x)),
    iAB: lambda x: (get_var(6, 8, x), get_var(23, 9, x)),
    iAC: lambda x: (get_var(6, 8, x), get_var(14, 9, x)),
    iABx: lambda x: (get_var(6, 8, x), get_var(14, 18, x)),
    iAsBx: lambda x: (get_var(6, 8, x), (get_var(14, 18, x)) - 131071),
    isBx: lambda x: ((get_var(14, 18, x)) - 131071, )
}

operand_types = {
    'MOVE': iAB,
    'LOADK': iABx,
    'LOADBOOL': iABC,
    'LOADNIL': iAB,
    'GETUPVAL': iAB,
    'GETGLOBAL': iABx,
    'GETTABLE': iABC,
    'SETGLOBAL': iABx,
    'SETUPVAL': iAB,
    'SETTABLE': iABC,
    'NEWTABLE': iABC,
    'SELF': iABC,
    'ADD': iABC,
    'SUB': iABC,
    'MUL': iABC,
    'DIV': iABC,
    'MOD': iABC,
    'POW': iABC,
    'UNM': iAB,
    'NOT': iAB,
    'LEN': iAB,
    'CONCAT': iABC,
    'JMP': isBx,
    'EQ': iABC,
    'LT': iABC,
    'LE': iABC,
    'TEST': iAC,
    'TESTSET': iABC,
    'CALL': iABC,
    'TAILCALL': iABC,
    'RETURN': iAB,
    'FORLOOP': iAsBx,
    'FORPREP': iAsBx,
    'TFORLOOP': iAC,
    'SETLIST': iABC,
    'CLOSE': iA,
    'CLOSURE': iABx,
    'VARARG': iAB
}


def get_opcode(b):
    return b & 0x3f


#Returns instruction, size, operands
class LuaBytecode(Architecture):
    name = 'luabytecodearch'
    opcode_display_length = 10
    instruction_length = 4
    max_instruction_length = 4
    default_int_size = 4

    def decode_instruction(self, data, addr):
        if len(data) < self.instruction_length:
            return None, None, None

        instruction_bytes = unpack('<L', data[0:self.instruction_length])[0]
        opcode = get_opcode(instruction_bytes)
        assert (opcode >= 0 and opcode <= 37), 'Invalid opcode @ %x' % addr
        opcode = opcodes[opcode]
        print "Opcode: %s" % opcode

        #Need to get operands now
        operand_type = operand_types[opcode]
        operands = operand_decode_func[operand_type](instruction_bytes)

        return opcode, self.instruction_length, operands

    def perform_get_instruction_info(self, data, addr):
        instruction, length, operands = self.decode_instruction(data, addr)

        result = InstructionInfo()

        result.length = length

        if instruction == 'CALL':
            result.add_branch(BranchType.CallDestination, 0)
        elif instruction == 'JMP':
            result.add_branch(BranchType.UnconditionalBranch, addr + operands[0])
        elif instruction == 'RETURN':
            result.add_branch(BranchType.FunctionReturn, 0)

        return result

    def perform_get_instruction_text(self, data, addr):
        instruction, length, operands = self.decode_instruction(data, addr)

        InstructionToken = InstructionTextTokenType.InstructionToken
        OperandSeparatorToken = InstructionTextTokenType.OperandSeparatorToken
        TextToken = InstructionTextTokenType.TextToken
        IntegerToken = InstructionTextTokenType.IntegerToken

        tokens = []

        tokens.append(
            InstructionTextToken(InstructionToken, '%-10s' % instruction))

        first_iteration = True
        for operand in operands:
            if not first_iteration:
                tokens.append(
                    InstructionTextToken(OperandSeparatorToken, ', '))

            tokens.append(
                InstructionTextToken(IntegerToken, '%d' % operand, operand))
            first_iteration = False

        print tokens
        return tokens, length

    def perform_get_instruction_low_level_il(self, data, addr, il):
        return None


LuaBytecode.register()
