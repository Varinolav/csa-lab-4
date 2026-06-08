from dataclasses import dataclass
from enum import IntEnum
from typing import Final


class Opcode(IntEnum):
    PUSH = 0x00
    DUP = 0x01
    DROP = 0x02
    SWAP = 0x03
    OVER = 0x04
    ADD = 0x05
    SUB = 0x06
    MUL = 0x07
    DIV = 0x08
    MOD = 0x09
    EQ = 0x0A
    LT = 0x0B
    GT = 0x0C
    LOAD = 0x0D
    STORE = 0x0E
    JMP = 0x0F
    JZ = 0x10
    CALL = 0x11
    RET = 0x12
    EXECUTE = 0x13
    IN = 0x14
    OUT = 0x15
    HALT = 0x16
    CARRY = 0x17


WITH_ARG: Final[frozenset[Opcode]] = frozenset(
    {
        Opcode.PUSH,
        Opcode.JMP,
        Opcode.JZ,
        Opcode.CALL,
        Opcode.IN,
        Opcode.OUT,
    }
)

WORD_SIZE: Final[int] = 4
IMM_BITS: Final[int] = 24
IMM_MAX: Final[int] = (1 << (IMM_BITS - 1)) - 1  # 0x7FFFFF
IMM_MIN: Final[int] = -(1 << (IMM_BITS - 1))  # -0x800000
IMM_MASK: Final[int] = (1 << IMM_BITS) - 1  # 0x00FFFFFF

HEADER_LEN: Final[int] = 4 + 4


@dataclass
class Instr:
    opcode: Opcode
    arg: int = 0
    line: int | None = None
    pos: int | None = None
    source: str | None = None


def _encode_imm(value: int) -> int:
    if not (IMM_MIN <= value <= IMM_MAX):
        raise ValueError(f"immediate {value} вне диапазона [{IMM_MIN}, {IMM_MAX}]")
    return value & IMM_MASK


def _decode_imm(raw: int) -> int:
    raw &= IMM_MASK
    if raw & (1 << (IMM_BITS - 1)):
        return raw - (1 << IMM_BITS)
    return raw


def encode_instr(ins: Instr) -> int:
    arg = _encode_imm(ins.arg) if ins.opcode in WITH_ARG else 0
    return ((int(ins.opcode) & 0xFF) << IMM_BITS) | arg


def decode_word(word: int) -> Instr:
    opcode = Opcode((word >> IMM_BITS) & 0xFF)
    arg = _decode_imm(word) if opcode in WITH_ARG else 0
    return Instr(opcode, arg)


def mnemonic(ins: Instr) -> str:
    if ins.opcode in WITH_ARG:
        return f"{ins.opcode.name} {ins.arg}"
    return ins.opcode.name


def pack_program(code, data) -> bytes:
    code_list = list(code)
    data_list = list(data)

    buf = bytearray()
    buf.extend(len(code_list).to_bytes(4, "big"))
    buf.extend(len(data_list).to_bytes(4, "big"))

    for ins in code_list:
        buf.extend(encode_instr(ins).to_bytes(4, "big"))

    for word in data_list:
        if not (-(1 << 31) <= word < (1 << 32)):
            raise ValueError(f"data word {word} не помещается в 32 бита")
        buf.extend((word & 0xFFFFFFFF).to_bytes(4, "big"))

    return bytes(buf)


def unpack_program(blob: bytes) -> tuple[list[Instr], list[int]]:
    if len(blob) < HEADER_LEN:
        raise ValueError("бинарный файл короче заголовка")

    code_len = int.from_bytes(blob[0:4], "big")
    data_len = int.from_bytes(blob[4:8], "big")
    expected = HEADER_LEN + (code_len + data_len) * WORD_SIZE
    if len(blob) != expected:
        raise ValueError(f"размер бинарного файла {len(blob)} не совпадает с ожидаемым {expected}")

    off = HEADER_LEN
    code: list[Instr] = []
    for _ in range(code_len):
        word = int.from_bytes(blob[off : off + WORD_SIZE], "big")
        code.append(decode_word(word))
        off += WORD_SIZE

    data: list[int] = []
    for _ in range(data_len):
        word = int.from_bytes(blob[off : off + WORD_SIZE], "big", signed=True)
        data.append(word)
        off += WORD_SIZE

    return code, data


def to_hex_dump(code, data) -> str:

    code_list = list(code)
    data_list = list(data)

    lines: list[str] = []
    lines.append("; CODE SECTION")
    for addr, ins in enumerate(code_list):
        word = encode_instr(ins)
        lines.append(f"{addr * 4} - {word:08X} - {mnemonic(ins)}")

    lines.append("")
    lines.append("; DATA SECTION")
    for addr, word in enumerate(data_list):
        unsigned = word & 0xFFFFFFFF
        line = f"{addr * 4} - {unsigned:08X} - {word}"
        if 32 <= word < 127:
            line += f"   ; {chr(word)!r}"
        lines.append(line)

    return "\n".join(lines) + "\n"
