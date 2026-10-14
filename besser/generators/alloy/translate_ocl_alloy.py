"""Translate typed B-OCL expressions into Alloy facts."""

import re
from dataclasses import dataclass, field

from dateutil import parser as dateutil_parser

from besser.BUML.metamodel.ocl.ocl import (
    BooleanLiteralExpression,
    DateLiteralExpression,
    IfExp,
    InfixOperator,
    IntegerLiteralExpression,
    LoopExp,
    OCLConstraint,
    OCLExpression,
    OperationCallExpression,
    PropertyCallExpression,
    RealLiteralExpression,
    StringLiteralExpression,
    TypeExp,
    VariableExp,
)
from besser.BUML.metamodel.structural import (
    AnyType,
    BooleanType,
    Class,
    DateTimeType,
    DateType,
    DomainModel,
    FloatType,
    Generalization,
    IntegerType,
    Property,
    StringType,
    TimeDeltaType,
    TimeType,
)
from besser.BUML.notations.ocl.api import parse_ocl
from besser.generators.alloy.date_ops import DATES_DICT, DateOpsRegistry, encode_date
from besser.generators.alloy.string_ops import StringOpError, StringOpsRegistry

@dataclass
class TranslatorState:
    cont_select: int = 0
    maxseq: int = 0
    dates: list = field(default_factory=list)
    strings: list = field(default_factory=list)
    buffer_pred_aux: list = field(default_factory=list)
    is_set_origin: bool = True
    data: dict = field(default_factory=dict)
    string_ops: StringOpsRegistry = field(default_factory=StringOpsRegistry)
    date_ops: DateOpsRegistry = field(default_factory=DateOpsRegistry)
    _string_name_index: dict[str, str] = field(default_factory=dict, repr=False, compare=False)

    def init_constraint(self) -> None:
        self.is_set_origin = True
        self.buffer_pred_aux.clear()

    def write_aux_pred(self, text: str) -> None:
        self.buffer_pred_aux.append(text)

    def read_aux_pred(self) -> str:
        return "\n".join(self.buffer_pred_aux)

    def register_string(self, literal: str) -> str:
        name = self._string_name_index.get(literal)
        if name is None:
            name = f"Str{len(self.strings)}"
            self._string_name_index[literal] = name
            self.strings.append(literal)
            self.maxseq = max(self.maxseq, len(literal))
        return name


class UnsupportedOCLConstructError(ValueError):
    """Raised when a parsed OCL construct has no Alloy translation."""


# ══════════════════════════════════════════════════════════════════════════════
# Model field lookup
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# Typed AST parsing and translation
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# 4. CLASS PREFIX RESOLUTION
# ══════════════════════════════════════════════════════════════════════════════

def _search_field(subject_class: str, field: str, data: dict) -> str:
    """Returns the type of *field* in *subject_class*, or ``''`` if not found."""
    for entry in data.get(subject_class, []):
        field_name, field_type = entry.split(":", 1)
        if field_name == field:
            return field_type
    return ""


def _iter_parent_chain(subject_class: str, inherits_from: dict):
    """Yields *subject_class* and then its first-parent chain until the root marker."""
    curr_class = subject_class
    while curr_class:
        yield curr_class
        parents = inherits_from.get(curr_class, "_")
        if parents in ("_", None, []):
            break
        curr_class = parents[0]


def _resolve_field_with_inheritance(subject_class: str, subject_field: str, data: dict, inherits_from: dict):
    """Returns ``(owner_class, field_type)`` for *subject_field* searching *subject_class* and parents."""
    for candidate in _iter_parent_chain(subject_class, inherits_from):
        field_type = _search_field(candidate, subject_field, data)
        if field_type:
            return candidate, field_type
    return "", ""


# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# 6. DATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_DATE_TYPES = {"date", "datetime", "time", "timedelta"}

_DATE_PATTERN = re.compile(
    r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$"
    r"|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,\s+\d{4})?$",
    re.IGNORECASE,
)


def is_date(s: str) -> str | None:
    """
    Detects whether *s* is a date literal and returns its Alloy id (``dMMDDYYYY``) or ``None``.

    The whole content (after stripping single/double quotes) must be a date, so
    arbitrary strings that merely contain a date-like substring (e.g.
    ``'date 2024-01-01 x'``) are left untouched.
    """
    contents = s.strip().strip("'").strip('"').strip()
    if not _DATE_PATTERN.match(contents):
        return None
    try:
        curr_date = dateutil_parser.parse(contents)
        return encode_date(curr_date)
    except (ValueError, OverflowError):
        return None


def parse_date(s: str, state: TranslatorState) -> str:
    """
    Parses *s* as a date and records its ``dMMDDYYYY`` id on *state*.

    The ``one sig`` declarations and the ordering fact are emitted later by
    :func:`generate_dates_and_order`, which assigns the sequential ``DateN``
    sig names (``Date0``, ``Date1``, ...) to every date of the model — OCL
    literals are treated exactly like randomly generated dates. Duplicated
    literals are only recorded once across the whole model.

    Returns an empty string.

    Raises:
        ValueError: If *s* cannot be interpreted as a date.
    """
    contents = s.strip().strip("'").strip('"').strip()
    try:
        curr_date = dateutil_parser.parse(contents)
    except (ValueError, OverflowError):
        raise ValueError(f"Invalid date in OCL constraint: {s!r}") from None
    sig_id = encode_date(curr_date)
    if sig_id not in state.dates:
        state.dates.append(sig_id)
    return ""


_DATE_LITERAL_PATTERN = re.compile(r"\bd\d{8}\b")


def resolve_ocl_date_literals(constraints) -> None:
    """Rewrites translated OCL facts in place.

    Replaces every ``dMMDDYYYY`` literal id produced by :func:`is_date` /
    :func:`parse_date` with the sequential ``DateN`` sig name assigned by
    :func:`generate_dates_and_order` (via :data:`DATES_DICT`), so OCL date
    constants use exactly the same atoms as randomly generated dates.\n
    Unknown ids (not present in :data:`DATES_DICT`) are left untouched.
    """
    if not DATES_DICT:
        return
    name_by_id = {v: k for k, v in DATES_DICT.items()}
    for constraint in constraints:
        constraint.expression = _DATE_LITERAL_PATTERN.sub(
            lambda m: name_by_id.get(m.group(0), m.group(0)),
            constraint.expression,
        )


def _is_date_field(subject_field: str, data: dict) -> bool:
    """Returns ``True`` if *subject_field* references a date-typed attribute.

    Attribute references appear class-prefixed (``Class_field``) in the
    translated Alloy string (see :func:`_translate_ocl_node`), so they can be
    matched against the ``{ClassName: ['field:Type', ...]}`` *data* map.
    """
    if not data:
        return False
    for curr_class, fields in data.items():
        for curr_field in fields:
            field_name, field_type = curr_field.split(":", 1)
            if field_type in _DATE_TYPES and f"{curr_class}_{field_name}" in subject_field:
                return True
    return False


def _field_type_of(subject_field: str, data: dict) -> str:
    """Return the Alloy type of *subject_field* (e.g. ``self.Book_title`` → ``str``), or ``''``.

    The match is *exact* (full prefixed name at the end of the expression) so
    compound collection expressions that merely *contain* a field reference are
    not misclassified as that field's type.
    """
    for curr_class, fields in data.items():
        for curr_field in fields:
            field_name, field_type = curr_field.split(":", 1)
            pref = f"{curr_class}_{field_name}"
            if subject_field == pref or subject_field.endswith("." + pref):
                return field_type
    return ""


def _is_string_operand(subject: str, state: TranslatorState) -> bool:
    """Returns ``True`` when *subject* is a String operand: a ``str``-typed
    attribute or a quoted string literal that is not a date literal.

    Date literals are deliberately excluded because the date block in
    :func:`_translate_binaryop` runs before the string block and owns them.
    """
    if _field_type_of(subject, state.data) == "str":
        return True
    stripped = subject.strip()
    if (stripped.startswith("'") and stripped.endswith("'")) or (
        stripped.startswith('"') and stripped.endswith('"')
    ):
        return is_date(stripped) is None
    return False


def process_string_types(input_string: str, state: TranslatorState | None = None) -> str:
    """Replaces quoted string literals in the assembled Alloy fact with their
    model-wide sig names and registers them on *state*.

    Every ``'literal'`` occurrence is substituted by the ``StrN`` sig name
    assigned via :meth:`TranslatorState.register_string`, so identical
    literals — including the empty string ``''`` — always reference the same
    single ``one sig``.  The sig declarations themselves are emitted once per
    model by :func:`build_string_sigs` (in ``strings.als``), not inline here.

    Also records on *state* the maximum length of the extracted sequences
    (``state.maxseq``), used later to bound the Alloy ``seq`` scope.
    """
    if state is None:
        state = TranslatorState()
    literals = dict.fromkeys(re.findall(r"'([^']*)'", input_string))
    name_by_literal = {lit: state.register_string(lit) for lit in literals}
    return re.sub(
        r"'([^']*)'",
        lambda m: name_by_literal[m.group(1)],
        input_string,
    )

# ══════════════════════════════════════════════════════════════════════════════
# 7. INHERITANCE HIERARCHY UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def is_child(child: str, parent: str, inherits_from: dict) -> bool:
    """Returns ``True`` if *child* is a descendant of *parent* in the hierarchy."""
    if parent in inherits_from[child]:
        return True
    if inherits_from[child] == "_" or inherits_from[child] == ["_"]:
        return False
    return any(is_child(p, parent, inherits_from) for p in inherits_from[child])


def subtypes(subject_class: str, inherits_from: dict) -> list[str]:
    """Return the list of direct and indirect subtypes of *subject_class*."""
    return [e for e in inherits_from if is_child(e, subject_class, inherits_from)]


# ══════════════════════════════════════════════════════════════════════════════
# 8. AST → ALLOY (visitor)
# ══════════════════════════════════════════════════════════════════════════════

# ── 8a. Simple nodes ──────────────────────────────────────────────────────────

# ── 8c. Binary operator ───────────────────────────────────────────────────────

_MAP_OPS: dict[str, str] = {
    "<>": "!=", "!=": "!=", "and": "and", "xor": "xor", "or": "or", "implies": "=>"
}


def _is_boolean_field(val: str, data: dict) -> bool:
    field_reference = val.rsplit(".", 1)[-1]
    for class_name, fields in data.items():
        for field in fields:
            field_name, field_type = field.split(":", 1)
            if field_type == "bool" and field_reference == f"{class_name}_{field_name}":
                return True
    return False


def _normalize_boolean(val: str, op: str, data: dict) -> str:
    if op in {"=", "!="} and val == "isTrue[True]":
        return "True"
    if op in {"=", "!="} and val == "isFalse[False]":
        return "False"
    if op in {"and", "xor", "or", "=>"} and _is_boolean_field(val, data):
        return f"isTrue[{val}]"
    return val


def _translate_binaryop_date(
    op: str,
    left: str,
    right: str,
    is_left_lit: bool,
    is_right_lit: bool,
    state: TranslatorState,
) -> str:
    """Translates a comparison that involves at least one date operand.

    *left*/*right* may be date literals (declared as ``one sig`` and replaced
    by their ``dMMDDYYYY`` id) or date-typed attributes (kept as-is).  Ordered
    comparisons dispatch through the registry's registered Alloy code, which
    lives in ``date.als`` (``open date``) — the generator writes that module
    whenever the model has date-typed attributes or date literals.
    """
    extra = ""
    if is_left_lit:
        extra += parse_date(left, state)
    if is_right_lit:
        extra += parse_date(right, state)
    state.write_aux_pred(extra)

    left_val = is_date(left) if is_left_lit else left
    right_val = is_date(right) if is_right_lit else right

    if op in ("=", "!="):
        return f"({left_val} {op} {right_val})"
    return state.date_ops.translate(op, left_val, right_val) or ""


def _translate_binaryop_values(
    op: str, left: str, right: str, state: TranslatorState
) -> str:
    left_lit = is_date(left)
    right_lit = is_date(right)
    is_left_date = bool(left_lit) or _is_date_field(left, state.data)
    is_right_date = bool(right_lit) or _is_date_field(right, state.data)

    if (
        op in (">", ">=", "<", "<=", "=", "!=")
        and (is_left_date and is_right_date)
        and "null" not in (left, right)
    ):
        return _translate_binaryop_date(op, left, right, bool(left_lit), bool(right_lit), state)

    is_left_str = _is_string_operand(left, state)
    is_right_str = _is_string_operand(right, state)

    if (
        op in ("=", "!=")
        and (is_left_str and is_right_str)
        and "null" not in (left, right)
    ):
        str_result = state.string_ops.translate_binary(op, left, right)
        if str_result is None and op == "!=":
            str_result = state.string_ops.translate_binary("<>", left, right)
        if str_result is not None:
            return str_result
    if op == "*":
        return f"mul[{left}, {right}]"
    if op == "/":
        return f"div[{left}, {right}]"
    if op == "-":
        return left if right.lower() == "null" else f"minus[{left}, {right}]"

    if op == "+":
        return f"add[{left}, {right}]"

    if op == "xor":
        return f"((({left}) and not ({right})) or (not ({left}) and ({right})))"

    if op == "!=" and right == "null":
        return f"(! no({left}))"
    if op == "!=" and left == "null":
        return f"(! no({right}))"
    if op == "=" and right == "null":
        return f"( no({left}))"
    if op == "=" and left == "null":
        return f"( no({right}))"

    return f"({left} {op} {right})"


# ── 8d. Calls ─────────────────────────────────────────────────────────────────

def _as_set(expr: str, state: TranslatorState) -> str:
    """Return ``expr`` as a flat Alloy set and record that representation."""
    if not state.is_set_origin:
        state.is_set_origin = True
        return f"image[{expr}]"
    return expr


def _apply_asset(expr: str, state: TranslatorState) -> str:
    """
    Translates ``->asSet()`` to Alloy.

    When the source is a relation (``univ -> univ``), wraps in ``image[...]``
    to obtain the flat set of values.  Either way, marks the result as a set
    so that any subsequent chained operation (``->size()``, ``->union()``, etc.)
    treats it as ``set univ`` instead of ``univ -> univ``.
    """
    return _as_set(expr, state)


def _build_call_handlers() -> dict[str, callable]:
    """
    Builds the handler dict for OCL collection operations.

    Each handler has signature: ``(expr: str, args: list[str], state) -> str``.
    """
    return {
        "size":           lambda expr, args, state: f"#({expr})",
        "excluding":      lambda expr, args, state: (
            f"({_as_set(expr, state)})" if args[0].lower() == "null"
            else f"({_as_set(expr, state)} - {args[0]})"
        ),
        "including":      lambda expr, args, state: (
            f"({_as_set(expr, state)})" if args[0].lower() == "null"
            else f"({_as_set(expr, state)} + {args[0]})"
        ),
        "union":          lambda expr, args, state: f"({_as_set(expr, state)} + {args[0]})",
        "intersection":   lambda expr, args, state: f"({_as_set(expr, state)} & {args[0]})",
        "isempty":        lambda expr, args, state: f"(#({expr}) = 0)",
        "notempty":       lambda expr, args, state: f"(#({expr}) > 0)",
        "closure":        lambda expr, args, state: f"{expr}.*{args[0]}",
        "oclisundefined": lambda expr, args, state: f"no ({expr})",
        "includes":       lambda expr, args, state: (
            f"{args[0]} in image[{expr}]" if not state.is_set_origin else f"{args[0]} in {expr}"
        ),
        "excludes":       lambda expr, args, state: (
            f"not({args[0]} in image[{expr}])" if not state.is_set_origin
            else f"not({args[0]} in {expr})"
        ),
        "includesall":    lambda expr, args, state: (
            f"({args[0]} in image[{expr}])" if not state.is_set_origin else f"({args[0]} in {expr})"
        ),
        "excludesall":    lambda expr, args, state: (
            f"no ({args[0]} & image[{expr}])" if not state.is_set_origin
            else f"no ({args[0]} & {expr})"
        ),
        "asset":          lambda expr, args, state: _apply_asset(expr, state),
    }


CALL_HANDLERS: dict[str, callable] = _build_call_handlers()


def _translate_call_values(
    name: str,
    callname: str,
    source_node,
    expr: str,
    args: list[str],
    inherits_from: dict,
    state: TranslatorState,
) -> str:
    if name == "oclistypeof":
        s = f"{expr} in {args[0]}"
        subs = subtypes(args[0], inherits_from)
        if subs:
            s += " and " + " and ".join(f"{expr} not in {st}" for st in subs)
        return s

    if name == "ocliskindof":
        return f"{expr} in {args[0]}"

    if name == "abs":
        return f"abs[{expr}]"

    if _field_type_of(expr, state.data) == "str" or (
        isinstance(source_node, OperationCallExpression)
        and source_node.operation.lower() != "size"
        and source_node.operation.lower() in state.string_ops.registered_names()
    ):
        translated = state.string_ops.translate(name, expr, args)
        if translated is not None:
            return translated
        raise StringOpError(
            f"OCL String operation '{callname}()' is not supported on a "
            f"String attribute. Registered operations: "
            f"{', '.join(state.string_ops.registered_names())}."
        )

    handler = CALL_HANDLERS.get(name)
    if handler:
        if name in {"including", "excluding", "union", "intersection", "includes", "excludes", "includesall", "excludesall", "closure"} and not args:
            raise UnsupportedOCLConstructError(
                f"Unsupported OCL construct: malformed operation '{callname}'"
            )
        return handler(expr, args, state)

    raise UnsupportedOCLConstructError(
        f"Unsupported OCL construct: operation '{callname}'"
    )


# ── 8e. Iterators ─────────────────────────────────────────────────────────────

def _translate_collect_values(varnames: list[str], coll: str, expr: str) -> str:
    var = varnames[0] if varnames else "x"
    e = expr.replace(var + ".", "", 1)
    col = coll.replace(".", ",", 1)
    if "," in col:
        return f" collect[toSeq[{col}],{e}]"
    return f" toSeq[{col},{e}]"


def _compatibility_model(inherits_from: dict, data: dict, context_name: str) -> DomainModel:
    """Build a minimal model for callers using the legacy map-based API."""
    classes = {name: Class(name=name) for name in data}
    classes.setdefault(context_name, Class(name=context_name))
    for parents in inherits_from.values():
        names = [parents] if isinstance(parents, str) else parents
        for parent in names:
            if parent != "_":
                classes.setdefault(parent, Class(name=parent))

    primitive_types = {
        "str": StringType,
        "string": StringType,
        "int": IntegerType,
        "integer": IntegerType,
        "float": FloatType,
        "real": FloatType,
        "bool": BooleanType,
        "boolean": BooleanType,
        "time": TimeType,
        "date": DateType,
        "datetime": DateTimeType,
        "timedelta": TimeDeltaType,
        "any": AnyType,
    }
    for class_name, fields in data.items():
        attributes = set()
        for field in fields:
            field_name, type_name = field.split(":", 1)
            field_type = primitive_types.get(type_name.lower())
            if field_type is None:
                field_type = classes.setdefault(type_name, Class(name=type_name))
            attributes.add(Property(name=field_name, type=field_type))
        classes[class_name].attributes = attributes

    generalizations = set()
    for child_name, parents in inherits_from.items():
        parent_names = [parents] if isinstance(parents, str) else parents
        for parent_name in parent_names:
            if parent_name != "_":
                generalizations.add(
                    Generalization(
                        general=classes[parent_name],
                        specific=classes[child_name],
                    )
                )
    return DomainModel(
        name="AlloyOCLCompatibilityModel",
        types=set(classes.values()),
        generalizations=generalizations,
    )


def _static_class_name(node, context_name: str, iterator_types: dict[str, str], data: dict) -> str | None:
    if isinstance(node, VariableExp):
        if node.name == "self":
            return context_name
        return iterator_types.get(node.name)
    if isinstance(node, TypeExp):
        return node.name if node.name in data else None
    if isinstance(node, PropertyCallExpression):
        type_name = getattr(node.type, "name", None)
        return type_name if type_name in data else None
    if isinstance(node, LoopExp):
        return _static_class_name(node.source, context_name, iterator_types, data)
    if isinstance(node, OperationCallExpression) and node.operation.lower() == "allinstances":
        source_name = getattr(node.source, "name", None)
        return source_name if source_name in data else None
    if isinstance(node, OperationCallExpression) and node.operation.lower() in {
        "asset", "including", "excluding", "union", "intersection"
    }:
        return _static_class_name(node.source, context_name, iterator_types, data)
    return None


def _translate_ocl_node(
    node,
    context_name: str,
    inherits_from: dict,
    data: dict,
    state: TranslatorState,
    iterator_types: dict[str, str] | None = None,
) -> str:
    """Visit a typed B-OCL node and emit its Alloy expression directly."""
    iterator_types = iterator_types or {}

    if node is None:
        return "null"
    if isinstance(node, BooleanLiteralExpression):
        return "isTrue[True]" if node.value else "not isTrue[True]"
    if isinstance(node, (IntegerLiteralExpression, RealLiteralExpression)):
        return str(node.value)
    if isinstance(node, StringLiteralExpression):
        return f"'{node.value}'"
    if isinstance(node, DateLiteralExpression):
        if is_date(node.value):
            return f"'{node.value}'"
        raise UnsupportedOCLConstructError(
            f"Unsupported OCL construct: date expression '{node.value}'"
        )
    if isinstance(node, TypeExp):
        return node.name
    if isinstance(node, VariableExp):
        if node.name == "self" or node.name in iterator_types:
            return node.name
        raise UnsupportedOCLConstructError(
            f"Unsupported OCL construct: unresolved variable '{node.name}'"
        )
    if isinstance(node, PropertyCallExpression):
        source = node.source or VariableExp("self", None)
        subject_class = _static_class_name(source, context_name, iterator_types, data)
        if subject_class is None:
            raise UnsupportedOCLConstructError(
                f"Unsupported OCL construct: property navigation '{node.property.name}'"
            )
        owner, _ = _resolve_field_with_inheritance(
            subject_class, node.property.name, data, inherits_from
        )
        if not owner:
            owner = getattr(getattr(node.property, "owner", None), "name", "")
        if owner not in data:
            raise UnsupportedOCLConstructError(
                f"Unsupported OCL construct: property '{node.property.name}' on '{subject_class}'"
            )
        source_text = _translate_ocl_node(
            source, context_name, inherits_from, data, state, iterator_types
        )
        return f"{source_text}.{owner}_{node.property.name}"
    if isinstance(node, IfExp):
        condition = _translate_ocl_node(
            node.ifCondition, context_name, inherits_from, data, state, iterator_types
        )
        condition = _normalize_boolean(condition, "and", data)
        then_part = _translate_ocl_node(
            node.thenExpression, context_name, inherits_from, data, state, iterator_types
        )
        then_part = _normalize_boolean(then_part, "and", data)
        else_part = _translate_ocl_node(
            node.elseCondition, context_name, inherits_from, data, state, iterator_types
        )
        else_part = _normalize_boolean(else_part, "and", data)
        return (
            f"(({condition}) implies ({then_part})) "
            f"and ((not ({condition})) implies ({else_part}))"
        )
    if isinstance(node, LoopExp):
        kind = node.name.lower()
        collection = _translate_ocl_node(
            node.source, context_name, inherits_from, data, state, iterator_types
        )
        if len(node.body) != 1:
            raise UnsupportedOCLConstructError(
                f"Unsupported OCL construct: iterator '{node.name}' body count {len(node.body)}"
            )
        if kind not in {"forall", "exists", "select", "reject", "collect", "closure"}:
            raise UnsupportedOCLConstructError(
                f"Unsupported OCL construct: iterator '{node.name}'"
            )
        names = [iterator.name for iterator in node.iterator]
        source_type = _static_class_name(node.source, context_name, iterator_types, data)
        scoped_types = dict(iterator_types)
        for iterator in node.iterator:
            declared_type = getattr(iterator.type, "name", None)
            scoped_types[iterator.name] = declared_type if declared_type in data else source_type
        expression = _translate_ocl_node(
            node.body[0], context_name, inherits_from, data, state, scoped_types
        )
        expression = _normalize_boolean(expression, "and", data)
        if kind == "forall":
            keyword = "all"
            collection = collection if state.is_set_origin else f"image[{collection}]"
            return f"{keyword} {', '.join(names) or 'x'} : {collection} | {expression}"
        if kind == "exists":
            collection = collection if state.is_set_origin else f"image[{collection}]"
            return f"some {', '.join(names) or 'x'} : {collection} | {expression}"
        if kind in {"select", "reject"}:
            var = names[0] if names else "x"
            select_id = state.cont_select
            state.cont_select += 1
            is_reject = kind == "reject"
            neg_open = "not(" if is_reject else ""
            neg_close = ")" if is_reject else ""
            if state.is_set_origin:
                template = (
                    f"fun select{select_id}[suva:set univ]: set univ "
                    f"{{{{ ___x___:univ | ___x___ in suva and "
                    f"{neg_open}<expr>{neg_close} }}}}"
                )
            else:
                template = (
                    f"fun select{select_id}[suva:univ->univ]: univ->univ "
                    f"{{{{ a,___x___:univ | (a->___x___) in suva and "
                    f"{neg_open}<expr>{neg_close} }}}}"
                )
                state.is_set_origin = False
            state.write_aux_pred(
                "\n" + template.replace("<expr>", expression.replace(var + ".", "___x___."))
            )
            return f"{{select{select_id}[{collection}]}}"
        if kind == "collect":
            state.is_set_origin = False
            return _translate_collect_values(names, collection, expression)
        return _translate_call_values(
            "closure", "closure", node, collection, [expression], inherits_from, state
        )
    if isinstance(node, OperationCallExpression):
        operation = node.operation.lower()
        binary_operators = {
            "=", "<>", "!=", "<", ">", "<=", ">=", "+", "-", "*", "/",
            "and", "or", "xor", "implies",
        }
        if operation in binary_operators:
            if len(node.arguments) == 3 and isinstance(node.arguments[1], InfixOperator):
                left_node, infix, right_node = node.arguments
                if infix.get_infix_operator().lower() != operation:
                    raise UnsupportedOCLConstructError(
                        f"Unsupported OCL construct: malformed '{node.operation}' operation"
                    )
            elif len(node.arguments) == 2 and operation in {"and", "or", "xor", "implies"}:
                left_node, right_node = node.arguments
            else:
                raise UnsupportedOCLConstructError(
                    f"Unsupported OCL construct: malformed '{node.operation}' operation"
                )
            alloy_op = _MAP_OPS.get(operation, operation)
            left = _normalize_boolean(
                _translate_ocl_node(left_node, context_name, inherits_from, data, state, iterator_types),
                alloy_op,
                data,
            )
            right = _normalize_boolean(
                _translate_ocl_node(right_node, context_name, inherits_from, data, state, iterator_types),
                alloy_op,
                data,
            )
            return _translate_binaryop_values(alloy_op, left, right, state)
        if operation in {"not", "unary_not", "unary_-"}:
            if len(node.arguments) != 1:
                raise UnsupportedOCLConstructError(
                    f"Unsupported OCL construct: malformed unary '{node.operation}'"
                )
            operand = _translate_ocl_node(
                node.arguments[0], context_name, inherits_from, data, state, iterator_types
            )
            if operation in {"not", "unary_not"}:
                operand = _normalize_boolean(operand, "and", data)
            return f"not ({operand})" if operation in {"not", "unary_not"} else f"minus[0, {operand}]"
        if operation == "allinstances":
            type_name = getattr(node.source, "name", None)
            if type_name:
                return type_name
            raise UnsupportedOCLConstructError(
                "Unsupported OCL construct: allInstances without a class source"
            )
        if node.source is None and operation == "abs" and len(node.arguments) == 1:
            operand = _translate_ocl_node(
                node.arguments[0], context_name, inherits_from, data, state, iterator_types
            )
            return f"abs[{operand}]"
        if node.source is None:
            raise UnsupportedOCLConstructError(
                f"Unsupported OCL construct: operation '{node.operation}'"
            )
        expr = _translate_ocl_node(
            node.source, context_name, inherits_from, data, state, iterator_types
        )
        args = [
            _translate_ocl_node(arg, context_name, inherits_from, data, state, iterator_types)
            for arg in node.arguments
        ]
        return _translate_call_values(
            operation, node.operation, node.source, expr, args, inherits_from, state
        )
    raise UnsupportedOCLConstructError(
        f"Unsupported OCL construct: {type(node).__name__}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 9. MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def ocl_to_alloy(
    inherits_from: dict,
    data: dict,
    ocl: str | OCLExpression | OCLConstraint,
    context_name: str = "",
    state: TranslatorState | None = None,
    enums: dict[str, set[str]] | None = None,
    *,
    model: DomainModel | None = None,
) -> str:
    """Translate OCL through the typed B-OCL AST into an Alloy fact.

    Args:
        inherits_from: ``{ClassName: [Parent, ...] | '_'}`` hierarchy map.
        data:          ``{ClassName: ['field:Type', ...]}`` attribute map.
        ocl:           OCL source, an OCL expression node, or parsed constraint.
        context_name:  Name of the class the constraint applies to.
        state:        Shared state between constraints (created if ``None``).
        enums:         Retained for compatibility with existing callers.
        model:         Domain model used by :func:`parse_ocl`. When omitted,
                       a minimal model is built from ``inherits_from``/``data``.

    Returns:
        A string with the generated Alloy fact (including auxiliary predicates
        and string/date sigs when applicable).

    Raises:
        UnsupportedOCLConstructError: If a parsed node or operation has no
            Alloy translation.
    """
    if state is None:
        state = TranslatorState()
    state.data = data
    state.init_constraint()

    if model is None:
        model = _compatibility_model(inherits_from, data, context_name)
    context_class = next(
        (item for item in model.types if isinstance(item, Class) and item.name == context_name),
        None,
    )
    if context_class is None:
        raise ValueError(f"OCL context class '{context_name}' was not found in the domain model")

    if isinstance(ocl, OCLConstraint):
        expression = ocl.ast
        context_name = ocl.context.name
    elif isinstance(ocl, OCLExpression):
        expression = ocl
    else:
        ocl_source = ocl.strip()
        if not re.match(r"^context\b", ocl_source, flags=re.IGNORECASE):
            ocl_source = f"context {context_name} inv: {ocl_source}"
        expression = parse_ocl(ocl_source, model, context_class).ast

    invariante = _translate_ocl_node(
        expression, context_name, inherits_from, data, state
    )
    invariante = _normalize_boolean(invariante, "and", data)
    pred_aux = state.read_aux_pred()
    result = pred_aux + f"fact{{ all self:this/{context_name}|{invariante}}}"
    return process_string_types(result, state)
