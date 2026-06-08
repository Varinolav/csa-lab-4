import argparse
from dataclasses import dataclass, field
from pathlib import Path

from isa import (
    Instr,
    Opcode,
    pack_program,
    to_hex_dump,
)


@dataclass
class Token:
    kind: str
    value: str
    line: int
    col: int


class CompileError(Exception):
    pass


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    col = 1
    n = len(text)
    block_depth = 0

    def starts_word_here(j: int) -> bool:
        return j == 0 or text[j - 1].isspace()

    while i < n:
        ch = text[i]

        if ch == "\n":
            i += 1
            line += 1
            col = 1
            continue

        if block_depth > 0:
            if ch == "(":
                block_depth += 1
            elif ch == ")":
                block_depth -= 1
            i += 1
            col += 1
            continue

        if ch.isspace():
            i += 1
            col += 1
            continue

        if ch == "\\" and (i + 1 == n or text[i + 1].isspace()):
            while i < n and text[i] != "\n":
                i += 1
            continue

        if ch == "(" and starts_word_here(i) and (i + 1 < n and text[i + 1].isspace()):
            block_depth = 1
            i += 1
            col += 1
            continue

        if ch == "." and i + 1 < n and text[i + 1] == '"' and starts_word_here(i):
            start_line, start_col = line, col
            i += 2
            col += 2
            if i < n and text[i] == " ":
                i += 1
                col += 1
            buf: list[str] = []
            while i < n and text[i] != '"':
                if text[i] == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                buf.append(text[i])
                i += 1
            if i >= n:
                raise CompileError(f'незакрытая строка ." в строке {start_line}, col {start_col}')
            i += 1
            col += 1
            tokens.append(Token("PRINT_STR", "".join(buf), start_line, start_col))
            continue

        if ch == "s" and i + 1 < n and text[i + 1] == '"' and starts_word_here(i):
            start_line, start_col = line, col
            i += 2
            col += 2
            if i < n and text[i] == " ":
                i += 1
                col += 1
            buf = []
            while i < n and text[i] != '"':
                if text[i] == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                buf.append(text[i])
                i += 1
            if i >= n:
                raise CompileError(f'незакрытая строка s" в строке {start_line}, col {start_col}')
            i += 1
            col += 1
            tokens.append(Token("STR_LIT", "".join(buf), start_line, start_col))
            continue

        start_line, start_col = line, col
        buf = []
        while i < n and not text[i].isspace():
            buf.append(text[i])
            i += 1
            col += 1
        tokens.append(Token("WORD", "".join(buf), start_line, start_col))

    if block_depth > 0:
        raise CompileError("незакрытый блочный комментарий '(' ... ')'")

    return tokens


SIMPLE_WORDS: dict[str, list[Opcode]] = {
    "+": [Opcode.ADD],
    "-": [Opcode.SUB],
    "*": [Opcode.MUL],
    "/": [Opcode.DIV],
    "mod": [Opcode.MOD],
    "=": [Opcode.EQ],
    "<": [Opcode.LT],
    ">": [Opcode.GT],
    "dup": [Opcode.DUP],
    "drop": [Opcode.DROP],
    "swap": [Opcode.SWAP],
    "over": [Opcode.OVER],
    "load": [Opcode.LOAD],
    "store": [Opcode.STORE],
    "execute": [Opcode.EXECUTE],
    "carry": [Opcode.CARRY],
}

CONTROL_WORDS: frozenset[str] = frozenset(
    {
        "if",
        "else",
        "then",
        "begin",
        "while",
        "repeat",
        "again",
        "until",
        "in",
        "out",
        "'",
        ":",
        ";",
        "variable",
        "alloc",
    }
)

EMIT_STR_BUILTIN: str = "__emit_str__"


def _is_int_literal(s: str) -> bool:
    if not s:
        return False
    if s[0] in "+-":
        return len(s) > 1 and s[1:].isdigit()
    return s.isdigit()


@dataclass
class WordDef:
    name: str
    body: list[Token]
    decl_line: int


@dataclass
class Program:
    variables: dict[str, int] = field(default_factory=dict)
    words: dict[str, WordDef] = field(default_factory=dict)
    top_level: list[Token] = field(default_factory=list)
    data_init: list[int] = field(default_factory=list)


def first_pass(tokens: list[Token]) -> Program:
    prog = Program()
    i = 0
    n = len(tokens)

    while i < n:
        tok = tokens[i]
        if tok.kind != "WORD":
            prog.top_level.append(tok)
            i += 1
            continue

        w = tok.value.lower()
        if w == "variable":
            i = _decl_variable(prog, tokens, i)
            continue

        if _is_int_literal(tok.value) and i + 1 < n and _is_word(tokens[i + 1], "alloc"):
            count = _parse_int(tok.value)
            if count < 0:
                raise CompileError(f"alloc: отрицательный размер {count} (строка {tok.line})")
            prog.data_init.extend([0] * count)
            i += 2
            continue

        if w == "alloc":
            raise CompileError(f"'alloc' требует число-размер перед ним (строка {tok.line})")

        if w == ":":
            if i + 1 >= n or tokens[i + 1].kind != "WORD":
                raise CompileError(f"':' без имени слова (строка {tok.line}, col {tok.col})")
            name_tok = tokens[i + 1]
            name = name_tok.value.lower()
            _check_name_free(name, prog, name_tok)
            i += 2
            body: list[Token] = []
            while i < n and not (tokens[i].kind == "WORD" and tokens[i].value == ";"):
                body.append(tokens[i])
                i += 1
            if i >= n:
                raise CompileError(f"не закрыто определение слова '{name}' (строка {tok.line})")
            i += 1
            prog.words[name] = WordDef(name=name, body=body, decl_line=tok.line)
            continue

        if w == ";":
            raise CompileError(f"';' без открывающего ':' (строка {tok.line})")

        prog.top_level.append(tok)
        i += 1

    return prog


def _check_name_free(name: str, prog: Program, tok: Token) -> None:
    if name in SIMPLE_WORDS or name in CONTROL_WORDS:
        raise CompileError(f"имя '{name}' зарезервировано под встроенное слово (строка {tok.line})")
    if name == EMIT_STR_BUILTIN:
        raise CompileError(f"имя '{name}' зарезервировано транслятором (строка {tok.line})")
    if name in prog.variables:
        raise CompileError(f"переопределение переменной '{name}' (строка {tok.line})")
    if name in prog.words:
        raise CompileError(f"переопределение слова '{name}' (строка {tok.line})")


def _is_word(tok: Token, value: str) -> bool:
    return tok.kind == "WORD" and tok.value.lower() == value


def _decl_variable(prog: Program, tokens: list[Token], i: int) -> int:
    n = len(tokens)
    decl = tokens[i]
    if i + 1 >= n or tokens[i + 1].kind != "WORD":
        raise CompileError(f"variable без имени (строка {decl.line}, col {decl.col})")
    name_tok = tokens[i + 1]
    name = name_tok.value.lower()
    _check_name_free(name, prog, name_tok)

    word_idx = len(prog.data_init)
    addr = word_idx * 4  # byte address
    prog.variables[name] = addr
    prog.data_init.append(0)
    i += 2

    if i < n and _is_word(tokens[i], "="):
        if i + 1 >= n or not _is_int_literal(tokens[i + 1].value):
            msg = f"variable '{name}': ожидается целое после '=' (стр.{name_tok.line})"
            raise CompileError(msg)
        prog.data_init[word_idx] = _parse_int(tokens[i + 1].value)
        i += 2

    return i


@dataclass
class CodegenCtx:
    code: list[Instr] = field(default_factory=list)
    data: list[int] = field(default_factory=list)
    variables: dict[str, int] = field(default_factory=dict)
    words: dict[str, WordDef] = field(default_factory=dict)
    word_addr: dict[str, int] = field(default_factory=dict)
    forward_refs: list[tuple[int, str, Token]] = field(default_factory=list)
    uses_emit_str: bool = False

    def emit(self, opcode: Opcode, arg: int = 0, tok: Token | None = None) -> int:
        idx = len(self.code)
        self.code.append(
            Instr(
                opcode=opcode,
                arg=arg,
                line=tok.line if tok else None,
                pos=tok.col if tok else None,
                source=tok.value if tok else None,
            )
        )
        return idx

    def place_pstr(self, s: str) -> int:
        addr = len(self.data) * 4  # byte address
        self.data.append(len(s))
        for ch in s:
            self.data.append(ord(ch))
        return addr


def _parse_int(literal: str) -> int:
    if literal.startswith(("+", "-")):
        return int(literal[1:]) if literal[0] == "+" else -int(literal[1:])
    return int(literal)


def codegen(prog: Program) -> tuple[list[Instr], list[int]]:
    ctx = CodegenCtx(variables=prog.variables, words=prog.words)
    ctx.data = list(prog.data_init)

    _generate_block(ctx, prog.top_level, is_word_body=False)
    ctx.emit(Opcode.HALT)

    for name, wdef in prog.words.items():
        ctx.word_addr[name] = len(ctx.code) * 4
        _generate_block(ctx, wdef.body, is_word_body=True)
        ctx.emit(Opcode.RET)

    if ctx.uses_emit_str:
        ctx.word_addr[EMIT_STR_BUILTIN] = len(ctx.code) * 4
        _emit_print_pstr_helper(ctx)

    for idx, name, tok in ctx.forward_refs:
        if name not in ctx.word_addr:
            raise CompileError(f"неопределённое слово '{name}' (строка {tok.line})")
        ctx.code[idx].arg = ctx.word_addr[name]

    return ctx.code, ctx.data


def _generate_block(ctx: CodegenCtx, tokens: list[Token], *, is_word_body: bool) -> None:

    label_stack: list[tuple[str, int]] = []
    i = 0
    n = len(tokens)

    while i < n:
        tok = tokens[i]

        if tok.kind == "PRINT_STR":
            addr = ctx.place_pstr(tok.value)
            ctx.emit(Opcode.PUSH, addr, tok)
            call_idx = ctx.emit(Opcode.CALL, 0, tok)
            ctx.forward_refs.append((call_idx, EMIT_STR_BUILTIN, tok))
            ctx.uses_emit_str = True
            i += 1
            continue

        if tok.kind == "STR_LIT":
            addr = ctx.place_pstr(tok.value)
            ctx.emit(Opcode.PUSH, addr, tok)
            i += 1
            continue

        raw = tok.value
        w = raw.lower()

        if _is_int_literal(raw):
            num = _parse_int(raw)
            if i + 1 < n and tokens[i + 1].kind == "WORD":
                nxt = tokens[i + 1].value.lower()
                if nxt == "in":
                    ctx.emit(Opcode.IN, num, tok)
                    i += 2
                    continue
                if nxt == "out":
                    ctx.emit(Opcode.OUT, num, tok)
                    i += 2
                    continue
            ctx.emit(Opcode.PUSH, num, tok)
            i += 1
            continue

        if w in SIMPLE_WORDS:
            for op in SIMPLE_WORDS[w]:
                ctx.emit(op, 0, tok)
            i += 1
            continue

        if w in ("in", "out"):
            raise CompileError(f"'{raw}' требует литерал-порт перед ним (строка {tok.line})")

        if w == "alloc":
            raise CompileError(f"'alloc' допустим только на верхнем уровне (строка {tok.line})")

        if w == "'":
            if i + 1 >= n or tokens[i + 1].kind != "WORD":
                raise CompileError(f"' (tick) без имени слова (строка {tok.line})")
            target = tokens[i + 1].value.lower()
            idx = ctx.emit(Opcode.PUSH, 0, tok)
            ctx.forward_refs.append((idx, target, tok))
            i += 2
            continue

        if w == "if":
            jz_idx = ctx.emit(Opcode.JZ, 0, tok)
            label_stack.append(("if", jz_idx))
            i += 1
            continue

        if w == "else":
            if not label_stack or label_stack[-1][0] != "if":
                raise CompileError(f"'else' без 'if' (строка {tok.line})")
            _, jz_idx = label_stack.pop()
            jmp_idx = ctx.emit(Opcode.JMP, 0, tok)
            ctx.code[jz_idx].arg = len(ctx.code) * 4
            label_stack.append(("else", jmp_idx))
            i += 1
            continue

        if w == "then":
            if not label_stack or label_stack[-1][0] not in ("if", "else"):
                raise CompileError(f"'then' без 'if' (строка {tok.line})")
            _, idx = label_stack.pop()
            ctx.code[idx].arg = len(ctx.code) * 4
            i += 1
            continue

        if w == "begin":
            label_stack.append(("begin", len(ctx.code) * 4))
            i += 1
            continue

        if w == "while":
            if not label_stack or label_stack[-1][0] != "begin":
                raise CompileError(f"'while' без 'begin' (строка {tok.line})")
            jz_idx = ctx.emit(Opcode.JZ, 0, tok)
            label_stack.append(("while", jz_idx))
            i += 1
            continue

        if w == "repeat":
            begin_ok = (
                len(label_stack) >= 2
                and label_stack[-1][0] == "while"
                and label_stack[-2][0] == "begin"
            )
            if not begin_ok:
                raise CompileError(f"'repeat' без пары 'begin/while' (строка {tok.line})")
            _, jz_idx = label_stack.pop()
            _, begin_addr = label_stack.pop()
            ctx.emit(Opcode.JMP, begin_addr, tok)
            ctx.code[jz_idx].arg = len(ctx.code) * 4
            i += 1
            continue

        if w == "again":
            if not label_stack or label_stack[-1][0] != "begin":
                raise CompileError(f"'again' без 'begin' (строка {tok.line})")
            _, begin_addr = label_stack.pop()
            ctx.emit(Opcode.JMP, begin_addr, tok)
            i += 1
            continue

        if w == "until":
            if not label_stack or label_stack[-1][0] != "begin":
                raise CompileError(f"'until' без 'begin' (строка {tok.line})")
            _, begin_addr = label_stack.pop()
            ctx.emit(Opcode.JZ, begin_addr, tok)
            i += 1
            continue

        if w in ctx.variables:
            ctx.emit(Opcode.PUSH, ctx.variables[w], tok)
            i += 1
            continue

        if w in ctx.words:
            idx = ctx.emit(Opcode.CALL, 0, tok)
            ctx.forward_refs.append((idx, w, tok))
            i += 1
            continue

        raise CompileError(f"неизвестное слово '{raw}' (строка {tok.line}, col {tok.col})")

    if label_stack:
        kinds = ", ".join(k for k, _ in label_stack)
        where = "тело слова" if is_word_body else "top-level"
        raise CompileError(f"незакрытые конструкции в {where}: {kinds}")


def _emit_print_pstr_helper(ctx: CodegenCtx) -> None:
    e = ctx.emit
    e(Opcode.DUP)
    e(Opcode.LOAD)
    e(Opcode.SWAP)
    e(Opcode.PUSH, 4)  # skip length word (4 bytes) to reach first char
    e(Opcode.ADD)
    e(Opcode.SWAP)
    begin = len(ctx.code) * 4
    e(Opcode.DUP)
    e(Opcode.PUSH, 0)
    e(Opcode.GT)
    jz_idx = e(Opcode.JZ, 0)
    e(Opcode.OVER)
    e(Opcode.LOAD)
    e(Opcode.OUT, 1)
    e(Opcode.SWAP)
    e(Opcode.PUSH, 4)  # advance to next char word (4 bytes)
    e(Opcode.ADD)
    e(Opcode.SWAP)
    e(Opcode.PUSH, 1)  # decrement char counter
    e(Opcode.SUB)
    e(Opcode.JMP, begin)
    ctx.code[jz_idx].arg = len(ctx.code) * 4
    e(Opcode.DROP)
    e(Opcode.DROP)
    e(Opcode.RET)


def translate(source: str) -> tuple[list[Instr], list[int]]:
    tokens = tokenize(source)
    prog = first_pass(tokens)
    return codegen(prog)


def main(input_file: str, output_file: str) -> None:
    source = Path(input_file).read_text(encoding="utf-8-sig")
    code, data = translate(source)

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(pack_program(code, data))
    out_path.with_suffix(out_path.suffix + ".hex").write_text(
        to_hex_dump(code, data), encoding="utf-8"
    )

    print(
        f"source LoC: {len(source.splitlines())}  code: {len(code)} instr  data: {len(data)} words"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("output_file")
    args = parser.parse_args()

    main(args.input_file, args.output_file)
