"""
string_ops.py

Registry of OCL String operations (``(ocl_name, alloy_name, alloy_code)`` tuples)
and ``str_ops.als`` module generation.
"""

from collections.abc import Iterable
from pathlib import Path

StringOp = tuple[str, str, str]


class StringOpError(ValueError):
    """Raised when an OCL String operation is not recognised."""


class StringOpsRegistry:
    """Registry of OCL String operations (3-tuples) and ``str_ops.als`` generator."""

    _DEFAULT_OPERATIONS: list[StringOp] = [
        ("size", "len", "fun len[s: Str ] : Int { #(s.data)}"),
    ]

    def __init__(self, operations: Iterable[StringOp] | None = None) -> None:
        self._ops: dict[str, StringOp] = {}
        for ocl_name, alloy_name, alloy_code in (
            operations if operations is not None else self._DEFAULT_OPERATIONS
        ):
            self.register(ocl_name, alloy_name, alloy_code)

    def register(self, ocl_name: str, alloy_name: str, alloy_code: str) -> None:
        """Maps the OCL operation *ocl_name* to the Alloy callable *alloy_name*
        whose Alloy definition is *alloy_code*."""
        self._ops[ocl_name.lower()] = (ocl_name, alloy_name, alloy_code)

    def registered_names(self) -> list[str]:
        """Returns the sorted list of registered operation names."""
        return sorted(self._ops)

    def translate(self, name: str, expr: str, args: list[str]) -> str | None:
        """Translates ``expr.name(args)`` to the corresponding Alloy call, or
        returns ``None`` when the operation is not registered."""
        entry = self._ops.get(name.lower())
        if entry is None:
            return None
        _, alloy_name, _ = entry
        joined = ", ".join(args)
        if joined:
            return f"{alloy_name}[{expr}, {joined}]"
        return f"{alloy_name}[{expr}]"

    def generate_str_ops_model(self, output_dir: str | Path) -> Path:
        """Writes ``str_ops.als`` in *output_dir* with every registered snippet."""
        snippets = "\n\n".join(entry[2] for entry in self._ops.values())
        content = (
            "module string\n"
            + "abstract sig Char {}\n"
            + "one sig a extends Char {}\n"
            + "one sig b extends Char {}\n"
            + "one sig c extends Char {}\n"
            + "one sig d extends Char {}\n"
            + "one sig e extends Char {}\n"
            + "one sig f extends Char {}\n"
            + "one sig g extends Char {}\n"
            + "one sig h extends Char {}\n"
            + "one sig i extends Char {}\n"
            + "one sig j extends Char {}\n"
            + "one sig k extends Char {}\n"
            + "one sig l extends Char {}\n"
            + "one sig m extends Char {}\n"
            + "one sig n extends Char {}\n"
            + "one sig o extends Char {}\n"
            + "one sig p extends Char {}\n"
            + "one sig q extends Char {}\n"
            + "one sig r extends Char {}\n"
            + "one sig s extends Char {}\n"
            + "one sig t extends Char {}\n"
            + "one sig u extends Char {}\n"
            + "one sig v extends Char {}\n"
            + "one sig w extends Char {}\n"
            + "one sig x extends Char {}\n"
            + "one sig y extends Char {}\n"
            + "one sig z extends Char {}\n"
            + "sig   Str{\n"
            + "    data: seq Char\n"
            + "}\n"
            + snippets
        )
        path = Path(output_dir) / "strings.als"
        path.write_text(content, encoding="utf-8")
        return path
    