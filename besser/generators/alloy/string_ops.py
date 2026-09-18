"""
string_ops.py

Registry of OCL String operations (``(ocl_name, alloy_name, alloy_code)`` tuples)
and ``string.als`` module generation.
"""

from collections.abc import Iterable
from pathlib import Path

StringOp = tuple[str, str, str]


class StringOpError(ValueError):
    """Raised when an OCL String operation is not recognised."""


class StringOpsRegistry:
    """Registry of OCL String operations (3-tuples) and ``str_ops.als`` generator."""

    _DEFAULT_OPERATIONS = (
        ("size", "len", "fun len[s: Str ] : Int { #(s.data)}"),
        ("concat", "concat", "fun concat[s,m: Str] : Str { { res: Str | res.data = s.data.append[m.data]}}"),
        ("substring", "substring", "fun substring[s: Str, i,j: Int] : Str { { res: Str | res.data = s.data.subseq[i,j]}}"),
    )

    _DEFAULT_BINARY_OPERATIONS = (
        ("=", "strEq", "pred strEq[a, b: Str] {\n"
        "\teq[len[a], len[b]]\n"
        "\tall i: a.data.inds | a.data[i] = b.data[i]\n"
        "}\n"),
        ("<>", "strNe", "pred strNe[a, b: Str] {\n "
        "\tnot strEq[a,b]\n"
        "}\n"),
    )

    def __init__(self, operations: Iterable[StringOp] | None = None) -> None:
        self._ops: dict[str, StringOp] = {}
        for ocl_name, alloy_name, alloy_code in (
            operations if operations is not None else self._DEFAULT_OPERATIONS
        ):
            self.register(ocl_name, alloy_name, alloy_code)
        for ocl_name, alloy_name, alloy_code in self._DEFAULT_BINARY_OPERATIONS:
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

    def translate_binary(self, op: str, left: str, right: str) -> str | None:
        """Translates the binary comparison *op* (``=`` / ``!=``) between the
        translated string operands *left*/*right* to the corresponding Alloy
        call, or returns ``None`` when the operation is not registered.
        """
        entry = self._ops.get(op.lower())
        if entry is None:
            return None
        _, alloy_name, _ = entry
        return f"({alloy_name}[{left},{right}])"

    def generate_str_ops_model(self, output_dir: str | Path) -> Path:
        """Writes ``str_ops.als`` in *output_dir* with every registered snippet."""
        snippets = "\n\n".join(entry[2] for entry in self._ops.values())
        content = (
            "module string\n"
            + "abstract sig Char {}\n"
            + "one sig a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z extends Char {}\n"
            + "sig   Str{\n"
            + "    data: seq Char\n"
            + "}\n"
            + snippets
        )
        path = Path(output_dir) / "strings.als"
        path.write_text(content, encoding="utf-8")
        return path
    