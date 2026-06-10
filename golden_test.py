import base64
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
TRANSLATOR = HERE / "translator.py"
MACHINE = HERE / "machine.py"

SEPARATOR = "============================================================"


@pytest.mark.golden_test("golden/*.yml")
def test_translator_and_machine(golden, tmp_path):
    source = tmp_path / "prog.forth"
    input_stream = tmp_path / "input.txt"
    target = tmp_path / "target.bin"
    target_hex = tmp_path / "target.bin.hex"

    source.write_bytes(golden["in_source"].encode("utf-8"))
    input_stream.write_bytes(golden["in_stdin"].encode("utf-8"))

    tr = subprocess.run(
        [sys.executable, str(TRANSLATOR), str(source), str(target)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    sim = subprocess.run(
        [sys.executable, str(MACHINE), str(target), str(input_stream), "--log", "debug"],
        capture_output=True,
        check=False,
    )

    program_output = sim.stdout.decode("latin-1")
    machine_log = sim.stderr.decode("utf-8", errors="replace").replace("\r\n", "\n")

    out_stdout = tr.stdout + SEPARATOR + "\n" + program_output

    log_text = machine_log
    if len(log_text.splitlines()) > 700:
        log_text = "\n".join(log_text.splitlines()[:700]) + "\n"

    code_bin = target.read_bytes()
    code_hex = target_hex.read_text(encoding="utf-8")

    assert out_stdout == golden.out["out_stdout"]
    assert log_text == golden.out["out_log"]
    assert code_hex == golden.out["out_code_hex"]
    assert base64.b64encode(code_bin).decode("ascii") == golden.out["out_code"]
