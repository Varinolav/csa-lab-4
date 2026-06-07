from enum import IntEnum

from isa import Opcode


class AluOp(IntEnum):
    NOP = 0
    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4
    MOD = 5
    EQ = 6
    LT = 7
    GT = 8


class SelRightAlu(IntEnum):
    NEXT = 0
    ZERO = 1


class SelTodsIn(IntEnum):
    MEM = 0
    IO = 1
    ALU = 2
    IMM = 3


class DsOp(IntEnum):
    NOP = 0
    PUSH = 1
    LATCH_TODS = 2
    ALU_TO_TODS = 3
    DROP = 4
    DROP2 = 5
    DUP = 6
    SWAP = 7
    OVER = 8


class RsOp(IntEnum):
    NOP = 0
    PUSH_PC_PLUS_1 = 1
    POP = 2


class SelPc(IntEnum):
    KEEP = 0
    INC = 1
    TODS = 2
    TORS = 3


class JumpType(IntEnum):
    NONE = 0
    UNCOND = 1
    COND_ZERO = 2


class SelMpc(IntEnum):
    FETCH = 0
    DISPATCH = 1


class MicroInstr:
    def __init__(
        self,
        label,
        alu_op=AluOp.NOP,
        sel_right_alu=SelRightAlu.NEXT,
        sel_tos=SelTodsIn.ALU,
        sel_carry=False,
        latch_tods=False,
        ds_op=DsOp.NOP,
        mem_read=False,
        mem_write=False,
        io_read=False,
        io_write=False,
        sel_pc=SelPc.KEEP,
        jump_type=JumpType.NONE,
        sel_mpc=SelMpc.FETCH,
        rs_op=RsOp.NOP,
        latch_ir=False,
        halt=False,
    ):
        self.label = label
        self.alu_op = alu_op
        self.sel_right_alu = sel_right_alu
        self.sel_tos = sel_tos
        self.sel_carry = sel_carry
        self.latch_tods = latch_tods
        self.ds_op = ds_op
        self.mem_read = mem_read
        self.mem_write = mem_write
        self.io_read = io_read
        self.io_write = io_write
        self.sel_pc = sel_pc
        self.jump_type = jump_type
        self.sel_mpc = sel_mpc
        self.rs_op = rs_op
        self.latch_ir = latch_ir
        self.halt = halt


MICRO_PROGRAM = (
    # 0 — FETCH
    MicroInstr(
        label="FETCH",
        latch_ir=True,
        sel_mpc=SelMpc.DISPATCH,
    ),
    # 1 — PUSH imm
    MicroInstr(
        label="EXEC_PUSH",
        sel_tos=SelTodsIn.IMM,
        latch_tods=True,
        ds_op=DsOp.PUSH,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 2 — DUP
    MicroInstr(
        label="EXEC_DUP",
        ds_op=DsOp.DUP,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 3 — DROP
    MicroInstr(
        label="EXEC_DROP",
        ds_op=DsOp.DROP,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 4 — SWAP
    MicroInstr(
        label="EXEC_SWAP",
        ds_op=DsOp.SWAP,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 5 — OVER
    MicroInstr(
        label="EXEC_OVER",
        ds_op=DsOp.OVER,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 6 — ADD
    MicroInstr(
        label="EXEC_ADD",
        alu_op=AluOp.ADD,
        ds_op=DsOp.ALU_TO_TODS,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 7 — SUB
    MicroInstr(
        label="EXEC_SUB",
        alu_op=AluOp.SUB,
        ds_op=DsOp.ALU_TO_TODS,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 8 — MUL
    MicroInstr(
        label="EXEC_MUL",
        alu_op=AluOp.MUL,
        ds_op=DsOp.ALU_TO_TODS,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 9 — DIV
    MicroInstr(
        label="EXEC_DIV",
        alu_op=AluOp.DIV,
        ds_op=DsOp.ALU_TO_TODS,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 10 — MOD
    MicroInstr(
        label="EXEC_MOD",
        alu_op=AluOp.MOD,
        ds_op=DsOp.ALU_TO_TODS,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 11 — EQ
    MicroInstr(
        label="EXEC_EQ",
        alu_op=AluOp.EQ,
        ds_op=DsOp.ALU_TO_TODS,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 12 — LT
    MicroInstr(
        label="EXEC_LT",
        alu_op=AluOp.LT,
        ds_op=DsOp.ALU_TO_TODS,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 13 — GT
    MicroInstr(
        label="EXEC_GT",
        alu_op=AluOp.GT,
        ds_op=DsOp.ALU_TO_TODS,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 14 — LOAD
    MicroInstr(
        label="EXEC_LOAD",
        sel_tos=SelTodsIn.MEM,
        latch_tods=True,
        mem_read=True,
        ds_op=DsOp.LATCH_TODS,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 15 — STORE
    MicroInstr(
        label="EXEC_STORE",
        mem_write=True,
        ds_op=DsOp.DROP2,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 16 — JMP imm
    MicroInstr(
        label="EXEC_JMP",
        jump_type=JumpType.UNCOND,
        sel_mpc=SelMpc.FETCH,
    ),
    # 17 — JZ imm
    MicroInstr(
        label="EXEC_JZ",
        alu_op=AluOp.ADD,
        sel_right_alu=SelRightAlu.ZERO,
        ds_op=DsOp.DROP,
        jump_type=JumpType.COND_ZERO,
        sel_mpc=SelMpc.FETCH,
    ),
    # 18 — CALL imm
    MicroInstr(
        label="EXEC_CALL",
        rs_op=RsOp.PUSH_PC_PLUS_1,
        jump_type=JumpType.UNCOND,
        sel_mpc=SelMpc.FETCH,
    ),
    # 19 — RET
    MicroInstr(
        label="EXEC_RET",
        rs_op=RsOp.POP,
        sel_pc=SelPc.TORS,
        sel_mpc=SelMpc.FETCH,
    ),
    # 20 — EXECUTE
    MicroInstr(
        label="EXEC_EXECUTE",
        rs_op=RsOp.PUSH_PC_PLUS_1,
        sel_pc=SelPc.TODS,
        ds_op=DsOp.DROP,
        sel_mpc=SelMpc.FETCH,
    ),
    # 21 — IN port
    MicroInstr(
        label="EXEC_IN",
        sel_tos=SelTodsIn.IO,
        latch_tods=True,
        io_read=True,
        ds_op=DsOp.PUSH,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 22 — OUT port
    MicroInstr(
        label="EXEC_OUT",
        io_write=True,
        ds_op=DsOp.DROP,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
    # 23 — HALT
    MicroInstr(
        label="EXEC_HALT",
        halt=True,
    ),
    # 24 — CARRY
    MicroInstr(
        label="EXEC_CARRY",
        sel_tos=SelTodsIn.ALU,
        sel_carry=True,
        latch_tods=True,
        ds_op=DsOp.PUSH,
        sel_pc=SelPc.INC,
        sel_mpc=SelMpc.FETCH,
    ),
)


DISPATCH = {
    Opcode.PUSH: 1,
    Opcode.DUP: 2,
    Opcode.DROP: 3,
    Opcode.SWAP: 4,
    Opcode.OVER: 5,
    Opcode.ADD: 6,
    Opcode.SUB: 7,
    Opcode.MUL: 8,
    Opcode.DIV: 9,
    Opcode.MOD: 10,
    Opcode.EQ: 11,
    Opcode.LT: 12,
    Opcode.GT: 13,
    Opcode.LOAD: 14,
    Opcode.STORE: 15,
    Opcode.JMP: 16,
    Opcode.JZ: 17,
    Opcode.CALL: 18,
    Opcode.RET: 19,
    Opcode.EXECUTE: 20,
    Opcode.IN: 21,
    Opcode.OUT: 22,
    Opcode.HALT: 23,
    Opcode.CARRY: 24,
}
