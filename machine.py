import argparse
import logging
import sys
from pathlib import Path

from isa import Instr, Opcode, unpack_program
from microcode import (
    DISPATCH,
    MICRO_PROGRAM,
    AluOp,
    DsOp,
    JumpType,
    RsOp,
    SelMpc,
    SelPc,
    SelRightAlu,
    SelTodsIn,
)

logger = logging.getLogger("machine")

STDIN_PORT = 0
STDOUT_PORT = 1


class HaltSignal(Exception):
    pass


class DataPath:
    def __init__(self, data_mem, inputs=None, outputs=None):
        self.data_mem = data_mem
        self.inputs = inputs or {}
        self.outputs = outputs or {}
        self.ds = []
        self.c_flag = False

    def alu(self, op, left, right):
        if op == AluOp.NOP:
            return 0, True
        lu, ru = left & 0xFFFFFFFF, right & 0xFFFFFFFF
        if op == AluOp.ADD:
            r = left + right
            self.c_flag = (lu + ru) >= (1 << 32)
        elif op == AluOp.SUB:
            r = right - left
            self.c_flag = ru < lu
        elif op == AluOp.MUL:
            r = left * right
            self.c_flag = False
        elif op == AluOp.DIV:
            if left == 0:
                raise RuntimeError("деление на ноль")
            r = int(right / left) if (right < 0) ^ (left < 0) and right % left else right // left
            self.c_flag = False
        elif op == AluOp.MOD:
            if left == 0:
                raise RuntimeError("остаток от деления на ноль")
            q = int(right / left) if (right < 0) ^ (left < 0) and right % left else right // left
            r = right - q * left
            self.c_flag = False
        elif op == AluOp.EQ:
            r = 1 if left == right else 0
            self.c_flag = False
        elif op == AluOp.LT:
            r = 1 if right < left else 0
            self.c_flag = False
        elif op == AluOp.GT:
            r = 1 if right > left else 0
            self.c_flag = False
        else:
            raise RuntimeError(f"неизвестная ALU {op}")
        return r, r == 0

    def ds_push(self, value):
        self.ds.append(value)

    def ds_pop(self):
        if not self.ds:
            raise RuntimeError("POP при пустом стеке данных")
        return self.ds.pop()

    def ds_dup(self):
        if not self.ds:
            raise RuntimeError("DUP при пустом стеке данных")
        self.ds.append(self.ds[-1])

    def ds_swap(self):
        if len(self.ds) < 2:
            raise RuntimeError("SWAP при коротком стеке данных")
        self.ds[-1], self.ds[-2] = self.ds[-2], self.ds[-1]

    def ds_over(self):
        if len(self.ds) < 2:
            raise RuntimeError("OVER при коротком стеке данных")
        self.ds.append(self.ds[-2])

    def ds_replace_top(self, value):
        if not self.ds:
            raise RuntimeError("REPLACE при пустом стеке данных")
        self.ds[-1] = value

    def ds_alu_binary(self, result):
        if len(self.ds) < 2:
            raise RuntimeError(f"ALU при стеке данных глубиной {len(self.ds)}")
        self.ds.pop()
        self.ds[-1] = result

    def ds_drop2(self):
        if len(self.ds) < 2:
            raise RuntimeError("DROP2 при коротком стеке данных")
        self.ds.pop()
        self.ds.pop()

    def mem_read(self, addr):
        if not 0 <= addr < len(self.data_mem):
            raise RuntimeError(f"LOAD по адресу {addr} вне памяти данных")
        return self.data_mem[addr]

    def mem_write(self, addr, value):
        if not 0 <= addr < len(self.data_mem):
            raise RuntimeError(f"STORE по адресу {addr} вне памяти данных")
        word = value & 0xFFFFFFFF
        if word >= (1 << 31):
            word -= 1 << 32
        self.data_mem[addr] = word

    def tos(self):
        return self.ds[-1] if self.ds else None

    def nos(self):
        return self.ds[-2] if len(self.ds) >= 2 else None


class ControlUnit:
    def __init__(self, dp, code_mem):
        self.dp = dp
        self.code_mem = code_mem
        self.pc = 0
        self.ir = Instr(Opcode.HALT)
        self.rs = []
        self.mpc = 0
        self.tick_no = 0

    def rs_push(self, value):
        self.rs.append(value)

    def rs_pop(self):
        if not self.rs:
            raise RuntimeError("RET при пустом стеке возвратов")
        return self.rs.pop()

    def tors(self):
        return self.rs[-1] if self.rs else None

    def tick(self):
        mi = MICRO_PROGRAM[self.mpc]
        mpc_before = self.mpc
        pc_before = self.pc

        new_ir = self._latch_ir(mi)
        alu_result, zero_flag = self._eval_alu(mi)
        mem_out = self._mem_out(mi)
        io_in, io_event = self._io_read(mi, new_ir)
        tods_in = self._tods_in(mi, new_ir, mem_out, io_in, alu_result)

        new_pc = self._next_pc(mi, new_ir, pc_before, zero_flag)
        new_mpc = self._next_mpc(mi, new_ir)

        self.ir = new_ir
        self._commit_mem(mi)
        io_event = self._commit_io(mi, new_ir) or io_event
        self._ds_op(mi.ds_op, tods_in)
        self._commit_rs(mi, pc_before)
        self.pc = new_pc
        self.mpc = new_mpc
        self.tick_no += 1

        report = {
            "tick": self.tick_no,
            "mpc_before": mpc_before,
            "micro_label": mi.label,
            "pc_before": pc_before,
            "pc_after": new_pc,
            "ir": new_ir,
            "tos": self.dp.tos(),
            "nos": self.dp.nos(),
            "tors": self.tors(),
            "ds_depth": len(self.dp.ds),
            "rs_depth": len(self.rs),
            "zero_flag": zero_flag,
            "c_flag": self.dp.c_flag,
            "io_event": io_event,
        }

        if mi.halt:
            raise HaltSignal()
        return report

    def _latch_ir(self, mi):
        return self.code_mem[self.pc] if mi.latch_ir else self.ir

    def _eval_alu(self, mi):
        if mi.alu_op == AluOp.NOP:
            return 0, True
        dp = self.dp
        left = dp.tos()
        if left is None:
            raise RuntimeError(f"ALU {mi.alu_op.name} при пустом стеке (PC={self.pc})")
        if mi.sel_right_alu == SelRightAlu.ZERO:
            right = 0
        else:
            right = dp.nos()
            if right is None:
                raise RuntimeError(f"ALU {mi.alu_op.name} при коротком стеке (PC={self.pc})")
        return dp.alu(mi.alu_op, left, right)

    def _mem_out(self, mi):
        return self.dp.mem_read(self.dp.tos()) if mi.mem_read else 0

    def _io_read(self, mi, ir):
        if not mi.io_read:
            return 0, ""
        port = ir.arg
        buf = self.dp.inputs.get(port, [])
        if not buf:
            raise EOFError(f"input buffer на порту {port} пуст (PC={self.pc})")
        io_in = buf[0]
        return io_in, f"IN[{port}]={_pretty_token(io_in)}"

    def _tods_in(self, mi, ir, mem_out, io_in, alu_result):
        alu_out = int(self.dp.c_flag) if mi.sel_carry else alu_result
        if mi.latch_tods:
            return {
                SelTodsIn.MEM: mem_out,
                SelTodsIn.IO: io_in,
                SelTodsIn.ALU: alu_out,
                SelTodsIn.IMM: ir.arg,
            }[mi.sel_tos]
        if mi.ds_op == DsOp.ALU_TO_TODS:
            return alu_out
        return None

    def _commit_mem(self, mi):
        if mi.mem_write:
            self.dp.mem_write(self.dp.tos(), self.dp.nos())

    def _commit_io(self, mi, ir):
        dp = self.dp
        if mi.io_write:
            port = ir.arg
            dp.outputs.setdefault(port, []).append(dp.tos())
            return f"OUT[{port}]={_pretty_token(dp.tos())}"
        if mi.io_read:
            dp.inputs[ir.arg].pop(0)
        return ""

    def _commit_rs(self, mi, pc_before):
        if mi.rs_op == RsOp.PUSH_PC_PLUS_1:
            self.rs_push(pc_before + 1)
        elif mi.rs_op == RsOp.POP:
            self.rs_pop()

    def _ds_op(self, op, mux):
        dp = self.dp
        if op == DsOp.NOP:
            return
        if op == DsOp.PUSH:
            dp.ds_push(mux)
        elif op == DsOp.LATCH_TODS:
            dp.ds_replace_top(mux)
        elif op == DsOp.ALU_TO_TODS:
            dp.ds_alu_binary(mux)
        elif op == DsOp.DROP:
            dp.ds_pop()
        elif op == DsOp.DROP2:
            dp.ds_drop2()
        elif op == DsOp.DUP:
            dp.ds_dup()
        elif op == DsOp.SWAP:
            dp.ds_swap()
        elif op == DsOp.OVER:
            dp.ds_over()

    def _next_pc(self, mi, ir, pc, zero_flag):
        if mi.jump_type == JumpType.UNCOND:
            return ir.arg
        if mi.jump_type == JumpType.COND_ZERO:
            return ir.arg if zero_flag else pc + 1

        sel = mi.sel_pc
        if sel == SelPc.KEEP:
            return pc
        if sel == SelPc.INC:
            return pc + 1
        if sel == SelPc.TODS:
            top = self.dp.tos()
            if top is None:
                raise RuntimeError(f"EXECUTE при пустом стеке (PC={pc})")
            return top
        if sel == SelPc.TORS:
            top = self.tors()
            if top is None:
                raise RuntimeError(f"RET при пустом стеке возвратов (PC={pc})")
            return top
        raise RuntimeError(f"неизвестный SelPc {sel}")

    def _next_mpc(self, mi, ir):
        sel = mi.sel_mpc
        if sel == SelMpc.FETCH:
            return 0
        if sel == SelMpc.DISPATCH:
            return DISPATCH[ir.opcode]
        raise RuntimeError(f"неизвестный SelMpc {sel}")


def _pretty_token(value):
    if 32 <= value < 127:
        return f"{value}({chr(value)!r})"
    return str(value)


def _format_log_line(rep):
    tos = "·" if rep["tos"] is None else _pretty_token(rep["tos"])
    nos = "·" if rep["nos"] is None else _pretty_token(rep["nos"])
    tors = "·" if rep["tors"] is None else str(rep["tors"])
    zf = "Z" if rep["zero_flag"] else " "
    cf = "C" if rep["c_flag"] else " "
    ir = rep["ir"]
    if ir.opcode in (Opcode.PUSH, Opcode.JZ, Opcode.JMP, Opcode.CALL, Opcode.IN, Opcode.OUT):
        ir_mn = f"{ir.opcode.name} {ir.arg}"
    else:
        ir_mn = ir.opcode.name
    extra = f"  {rep['io_event']}" if rep["io_event"] else ""
    return (
        f"TICK={rep['tick']:>4}  mPC={rep['mpc_before']:>2}({rep['micro_label']:<12})"
        f"  PC={rep['pc_before']:>3}->{rep['pc_after']:<3}  IR={ir_mn:<10}  "
        f"TOS={tos:<10} NOS={nos:<10} TORS={tors:<5} {zf}{cf}  "
        f"ds={rep['ds_depth']} rs={rep['rs_depth']}{extra}"
    )


def simulate(code_mem, data_mem, stdin_tokens, limit=100000):
    dp = DataPath(
        list(data_mem),
        inputs={STDIN_PORT: list(stdin_tokens)},
        outputs={STDOUT_PORT: []},
    )
    cu = ControlUnit(dp, list(code_mem))
    halted = False
    eof = False
    limit_hit = False

    while cu.tick_no < limit:
        try:
            rep = cu.tick()
        except HaltSignal:
            halted = True
            break
        except EOFError as exc:
            eof = True
            logger.warning(f"EOF: {exc}")
            break
        logger.debug(_format_log_line(rep))
    else:
        limit_hit = True
        logger.warning(f"превышен лимит {limit} тактов")

    return {
        "output": list(dp.outputs.get(STDOUT_PORT, [])),
        "ticks": cu.tick_no,
        "halted": halted,
        "eof": eof,
        "limit_hit": limit_hit,
    }


def main(code_file, input_file, limit):
    code, data = unpack_program(Path(code_file).read_bytes())

    if input_file in (None, "-"):
        inp = list(sys.stdin.buffer.read())
    else:
        inp = list(Path(input_file).read_bytes())

    result = simulate(code, data, inp, limit=limit)

    print("".join(chr(v) for v in result["output"]), end="")
    sys.stderr.write(
        f"\n--- ticks={result['ticks']} halted={result['halted']} eof={result['eof']} "
        f"limit_hit={result['limit_hit']} output_len={len(result['output'])} ---\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("code_file")
    parser.add_argument("input_file", nargs="?", default=None)
    parser.add_argument("--limit", type=int, default=100000)
    parser.add_argument("--log", choices=("debug", "info", "warning", "off"), default="warning")
    args = parser.parse_args()

    if args.log != "off":
        logging.basicConfig(
            level=getattr(logging, args.log.upper()), format="%(message)s", stream=sys.stderr
        )

    main(args.code_file, args.input_file, args.limit)
