import array
import sys
import types

import pytest


sys.modules.setdefault("board", types.SimpleNamespace())
sys.modules.setdefault("rp2pio", types.SimpleNamespace(StateMachine=object))

import pt1
import pulsetrain


LABELS = pt1.PUBLIC_LABELS


def compiled(source):
    return pulsetrain.compile(pt1, source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("", []),
        (" \t\nH  L\r\n", [LABELS["H"], LABELS["L"]]),
        ("HLzi", [LABELS["H"], LABELS["L"], LABELS["z"], LABELS["i"]]),
        ("H L 100", [LABELS["H"], LABELS["L"], LABELS["Delay"], 297]),
        (
            "HL100z12i",
            [
                LABELS["H"],
                LABELS["L"],
                LABELS["Delay"],
                297,
                LABELS["z"],
                LABELS["Delay"],
                33,
                LABELS["i"],
            ],
        ),
        ("1", [LABELS["Delay"], 0]),
    ],
)
def test_compile_success(source, expected):
    assert compiled(source) == array.array("I", expected)


def test_zero_delay_is_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        compiled("0")


def test_invalid_character_reports_offset():
    with pytest.raises(ValueError, match=r"unexpected character '\?' at offset 1"):
        compiled("H?")
