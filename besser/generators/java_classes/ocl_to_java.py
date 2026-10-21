"""Translate supported B-OCL expressions into Java expressions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from besser.BUML.metamodel.ocl.ocl import (
    BooleanLiteralExpression,
    DateLiteralExpression,
    IfExp,
    InfixOperator,
    IntegerLiteralExpression,
    LoopExp,
    OperationCallExpression,
    PropertyCallExpression,
    RealLiteralExpression,
    StringLiteralExpression,
    TypeExp,
    VariableExp,
)
from besser.BUML.metamodel.structural import Class, DomainModel, Property


class OCLTranslationError(ValueError):
    """Raised when an OCL expression cannot be represented safely in Java."""


@dataclass(frozen=True)
class _Value:
    """A translated Java expression and what is known about its type.

    ``boxed`` marks primitive values taken from a collection (``Integer``,
    ``Float``...), which must not be compared with ``==``.
    """

    code: str
    type_name: str
    many: bool = False
    class_type: Class | None = None
    boxed: bool = False


_PRIMITIVES = {"int", "float", "double", "boolean"}

# B-UML primitive type names -> Java types (same mapping as java_fields.py.j2).
_JAVA_TYPES = {
    "str": "String",
    "text": "String",
    "int": "int",
    "float": "float",
    "bool": "boolean",
    "date": "LocalDate",
    "datetime": "LocalDateTime",
    "time": "LocalTime",
    "uuid": "UUID",
}


_JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new", "package",
    "private", "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws", "transient",
    "try", "void", "volatile", "while", "true", "false", "null", "var", "yield",
}


def _escape_java_string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _type_name(value: Any) -> str:
    name = getattr(value, "name", value)
    if not isinstance(name, str):
        name = type(value).__name__
    return _JAVA_TYPES.get(name.lower(), name)


class OCLToJavaVisitor:
    """Translate OCL AST nodes to Java and track required imports/registries."""

    def __init__(self, context_class: Class, model: DomainModel):
        self.context_class = context_class
        self.model = model
        self.imports: set[str] = set()
        self.all_instances: set[str] = set()
        self._this = _Value("this", context_class.name, class_type=context_class)
        # Iterator variables visible in the current expression.
        self._scope: dict[str, _Value] = {}
        # Element used to resolve bare names inside isUnique(...), else ``this``.
        self._implicit = self._this

    def visit(self, node: Any) -> _Value:
        if node is None:
            return _Value("null", "null")
        method = getattr(self, f"_visit_{type(node).__name__}", None)
        if method is None:
            raise OCLTranslationError(f"Unsupported OCL node: {type(node).__name__}")
        return method(node)

    def _visit_Property(self, node: Property) -> _Value:
        return self._property_access(self._this, node)

    def _visit_PropertyCallExpression(self, node: PropertyCallExpression) -> _Value:
        source = self.visit(node.source) if node.source is not None else self._this
        if not source.many:
            return self._property_access(source, node.property)
        # Navigation over a collection is an implicit collect, flattened as in OCL.
        variable = self._fresh_variable("__ocl")
        element = _Value(variable, source.type_name, class_type=source.class_type)
        access = self._property_access(element, node.property)
        if access.many:
            mapping = f"flatMap({variable} -> {self._stream(access.code)})"
        else:
            mapping = f"map({variable} -> {access.code})"
        self.imports.add("java.util.stream.Collectors")
        return _Value(
            f"{self._stream(source.code)}.{mapping}.collect(Collectors.toList())",
            access.type_name,
            many=True,
            class_type=access.class_type,
        )

    def _visit_VariableExp(self, node: VariableExp) -> _Value:
        if node.name == "self":
            return self._this
        if node.name in self._scope:
            return self._scope[node.name]
        # A bare name is a property of the implicit element, or of self.
        for receiver in (self._implicit, self._this):
            prop = self._find_property(receiver.class_type, node.name)
            if prop is not None:
                return self._property_access(receiver, prop)
        raise OCLTranslationError(f"Unresolved OCL variable or property: {node.name}")

    def _visit_TypeExp(self, node: TypeExp) -> _Value:
        return _Value(node.name, node.name, class_type=None)

    def _visit_IntegerLiteralExpression(self, node: IntegerLiteralExpression) -> _Value:
        return _Value(str(node.value), "int")

    def _visit_RealLiteralExpression(self, node: RealLiteralExpression) -> _Value:
        return _Value(f"{node.value}f", "float")

    def _visit_BooleanLiteralExpression(self, node: BooleanLiteralExpression) -> _Value:
        return _Value(str(node.value).lower(), "boolean")

    def _visit_StringLiteralExpression(self, node: StringLiteralExpression) -> _Value:
        return _Value(f'"{_escape_java_string(str(node.value))}"', "String")

    def _visit_DateLiteralExpression(self, node: DateLiteralExpression) -> _Value:
        raw = str(node.value)
        if raw == "Date::today()":
            self.imports.add("java.time.LocalDate")
            return _Value("LocalDate.now()", "LocalDate")
        if raw == "Date::now()":
            self.imports.add("java.time.LocalDateTime")
            return _Value("LocalDateTime.now()", "LocalDateTime")
        match = re.fullmatch(r"Date::today\(\)\.addDays\((-?\d+)\)", raw)
        if match:
            self.imports.add("java.time.LocalDate")
            return _Value(f"LocalDate.now().plusDays({match.group(1)})", "LocalDate")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            self.imports.add("java.time.LocalDate")
            return _Value(f'LocalDate.parse("{raw}")', "LocalDate")
        raise OCLTranslationError(f"Unsupported OCL date literal: {raw}")

    def _visit_IfExp(self, node: IfExp) -> _Value:
        condition, then_value, else_value = (
            self.visit(node.ifCondition),
            self.visit(node.thenExpression),
            self.visit(node.elseCondition),
        )
        kind = then_value.type_name if then_value.type_name == else_value.type_name else "Object"
        return _Value(
            f"({condition.code} ? {then_value.code} : {else_value.code})",
            kind,
            class_type=then_value.class_type if kind != "Object" else None,
        )

    def _visit_OperationCallExpression(self, node: OperationCallExpression) -> _Value:
        op = str(node.operation)
        args = node.arguments
        if len(args) == 3 and isinstance(args[1], InfixOperator):
            return self._infix(self.visit(args[0]), args[1].operator, self.visit(args[2]))
        if op in {"and", "AND_BINARY", "or", "OR_BINARY", "xor", "XOR_BINARY",
                  "implies", "IMPLIES_BINARY"}:
            left, right = self.visit(args[0]), self.visit(args[1])
            operators = {
                "and": "&&", "AND_BINARY": "&&", "or": "||", "OR_BINARY": "||",
                "xor": "^", "XOR_BINARY": "^",
            }
            if op in {"implies", "IMPLIES_BINARY"}:
                return _Value(f"(!({left.code}) || ({right.code}))", "boolean")
            return _Value(f"({left.code} {operators[op]} {right.code})", "boolean")
        if op in {"not", "NOT"}:
            return _Value(f"!({self.visit(args[0]).code})", "boolean")
        if op in {"-", "unary_-"} and len(args) == 1:
            value = self.visit(args[0])
            return _Value(f"-({value.code})", value.type_name)
        if op in {"Size", "size"}:
            source = self._source(node)
            if source.type_name == "String" and not source.many:
                return _Value(f"{source.code}.length()", "int")
            if source.many:
                return _Value(f"{source.code}.size()", "int")
            return _Value(f"({source.code} == null ? 0 : 1)", "int")
        if op in {"IsEmpty", "isEmpty"}:
            source = self._source(node)
            if source.type_name == "String" and not source.many:
                return _Value(f"{source.code}.isEmpty()", "boolean")
            if source.many:
                return _Value(f"{source.code}.isEmpty()", "boolean")
            return _Value(f"({source.code} == null)", "boolean")
        if op in {"First", "first", "Last", "last"}:
            source = self._source(node)
            if not source.many:
                raise OCLTranslationError(f"{op} requires a collection")
            if op.lower() == "first":
                code = f"{self._stream(source.code)}.findFirst().orElse(null)"
            else:
                code = f"{self._stream(source.code)}.reduce((a, b) -> b).orElse(null)"
            return _Value(code, source.type_name, class_type=source.class_type, boxed=True)
        if op in {"INCLUDES", "includes", "EXCLUDES", "excludes"}:
            source, item = self._source(node), self.visit(args[0])
            included = f"{source.code}.contains({item.code})"
            return _Value(f"!({included})" if op.lower() == "excludes" else included, "boolean")
        if op in {"INCLUDING", "EXCLUDING"}:
            raise OCLTranslationError(f"{op} is not supported for immutable collection translation")
        if op == "ALLInstances":
            if not isinstance(node.source, TypeExp):
                raise OCLTranslationError("allInstances requires a class type")
            class_name = node.source.name
            self.all_instances.add(class_name)
            class_obj = next(
                (item for item in self.model.types
                 if isinstance(item, Class) and item.name == class_name),
                None,
            )
            return _Value(
                f"{class_name}.allInstances",
                class_name,
                many=True,
                class_type=class_obj,
            )
        if op in {"ASSET", "asSet"}:
            source = self._source(node)
            if not source.many:
                return _Value(f"java.util.Collections.singletonList({source.code})",
                              source.type_name, many=True, class_type=source.class_type)
            self.imports.add("java.util.stream.Collectors")
            return _Value(f"{self._stream(source.code)}.distinct().collect(Collectors.toList())",
                          source.type_name, many=True, class_type=source.class_type)
        if op == "Sum":
            source = self._source(node)
            if not source.many:
                raise OCLTranslationError("sum requires a collection")
            if source.type_name == "int":
                return _Value(f"{self._stream(source.code)}.mapToInt(Integer::intValue).sum()", "int")
            if source.type_name == "float":
                return _Value(f"{self._stream(source.code)}.mapToDouble(Float::doubleValue).sum()", "double")
            raise OCLTranslationError(f"sum is unsupported for collection type {source.type_name}")
        if op in {"INTERSECTION", "SYMMETRICDIFFERENCE"}:
            raise OCLTranslationError(f"{op} is not supported")
        if op in {"OCLISTYPEOF", "OCLISKINDOF", "OCLASTYPE"}:
            return self._type_operation(node)
        if op in {"toUpper", "toUpperCase", "toLower", "toLowerCase", "concat", "substring"}:
            return self._string_operation(node)
        if op == "ISUNIQUE":
            return self._is_unique(node)
        raise OCLTranslationError(f"Unsupported OCL operation: {op}")

    def _visit_LoopExp(self, node: LoopExp) -> _Value:
        if not node.body:
            raise OCLTranslationError(f"Iterator {node.name} has no body")
        source = self._source(node)
        if not source.many:
            source_code = (
                f"({source.code} == null ? Stream.empty() : Stream.of({source.code}))"
            )
            self.imports.add("java.util.stream.Stream")
        else:
            source_code = self._stream(source.code)
        iterator_defs = list(node.iterator)
        if not iterator_defs:
            iterator_defs = [type("ImplicitIterator", (), {"name": "it", "type": source.class_type})()]
        prior_scope = self._scope.copy()
        variables = [
            self._safe_variable(getattr(iterator, "name", "it"))
            for iterator in iterator_defs
        ]
        for iterator, variable in zip(iterator_defs, variables):
            iterator_type = getattr(iterator, "type", None)
            inferred_class = iterator_type if isinstance(iterator_type, Class) else source.class_type
            self._scope[getattr(iterator, "name", variable)] = _Value(
                variable,
                inferred_class.name if inferred_class else source.type_name,
                class_type=inferred_class,
                boxed=source.many,
            )
        body = self.visit(node.body[0])
        self._scope = prior_scope
        operation = node.name.lower()
        if operation == "forall":

            def nested_all_match(index: int) -> str:
                if index == len(variables) - 1:
                    return f"{source_code}.allMatch({variables[index]} -> {body.code})"
                return (
                    f"{source_code}.allMatch({variables[index]} -> "
                    f"{nested_all_match(index + 1)})"
                )

            rendered = nested_all_match(0)
            return _Value(rendered, "boolean")
        if len(variables) != 1:
            raise OCLTranslationError(f"{node.name} supports one iterator only")
        variable = variables[0]
        if operation == "exists":
            return _Value(f"{source_code}.anyMatch({variable} -> {body.code})", "boolean")
        if operation in {"select", "reject"}:
            predicate = body.code if operation == "select" else f"!({body.code})"
            self.imports.add("java.util.stream.Collectors")
            return _Value(
                f"{source_code}.filter({variable} -> {predicate}).collect(Collectors.toList())",
                source.type_name, many=True, class_type=source.class_type,
            )
        if operation == "collect":
            self.imports.add("java.util.stream.Collectors")
            if body.many:
                return _Value(
                    f"{source_code}.flatMap({variable} -> {self._stream(body.code)})"
                    ".collect(Collectors.toList())",
                    body.type_name, many=True, class_type=body.class_type,
                )
            return _Value(
                f"{source_code}.map({variable} -> {body.code}).collect(Collectors.toList())",
                body.type_name, many=True, class_type=body.class_type,
            )
        raise OCLTranslationError(f"Unsupported OCL iterator: {node.name}")

    def _property_access(self, source: _Value, prop: Property) -> _Value:
        if source.class_type is None and source.type_name not in {"this", self.context_class.name}:
            raise OCLTranslationError(f"Cannot resolve property {prop.name} on {source.type_name}")
        if prop.owner is not None and hasattr(prop.owner, "ends") and not prop.is_navigable:
            raise OCLTranslationError(f"Association end {prop.name} is not navigable")
        class_type = prop.type if isinstance(prop.type, Class) else None
        return _Value(
            f"{source.code}.get{prop.name[:1].upper()}{prop.name[1:]}()",
            class_type.name if class_type else _type_name(prop.type),
            many=prop.multiplicity.max > 1,
            class_type=class_type,
        )

    def _find_property(self, class_obj: Class | None, name: str) -> Property | None:
        if class_obj is None:
            return None
        for candidate in [class_obj, *class_obj.all_parents()]:
            for prop in candidate.attributes:
                if prop.name == name:
                    return prop
            for association in candidate.associations:
                for end in association.ends:
                    if end.name == name and end.is_navigable:
                        return end
        return None

    def _source(self, node: OperationCallExpression) -> _Value:
        if node.source is None:
            raise OCLTranslationError(f"{node.operation} has no source expression")
        return self.visit(node.source)

    def _infix(self, left: _Value, operator: str, right: _Value) -> _Value:
        if operator in {"=", "==", "<>", "!="}:
            return self._equality(left, right, equal=operator in {"=", "=="})
        if operator in {"<", "<=", ">", ">="}:
            if left.type_name in {"String", "LocalDate", "LocalDateTime", "LocalTime"}:
                return _Value(f"({left.code}.compareTo({right.code}) {operator} 0)", "boolean")
            return _Value(f"({left.code} {operator} {right.code})", "boolean")
        if operator == "/":
            return _Value(f"((double) {left.code} / {right.code})", "double")
        if operator not in {"+", "-", "*", "%"}:
            raise OCLTranslationError(f"Unsupported infix operator: {operator}")
        result_kind = next(
            (kind for kind in ("double", "float") if kind in (left.type_name, right.type_name)),
            "int",
        )
        return _Value(f"({left.code} {operator} {right.code})", result_kind)

    def _equality(self, left: _Value, right: _Value, equal: bool) -> _Value:
        """Use ``==`` for null checks and primitives, ``Objects.equals`` otherwise."""
        is_null_check = "null" in (left.type_name, right.type_name)
        both_primitive = left.type_name in _PRIMITIVES and right.type_name in _PRIMITIVES
        both_boxed = left.boxed and right.boxed
        if is_null_check or (both_primitive and not both_boxed):
            operator = "==" if equal else "!="
            return _Value(f"({left.code} {operator} {right.code})", "boolean")
        self.imports.add("java.util.Objects")
        code = f"Objects.equals({left.code}, {right.code})"
        return _Value(code if equal else f"!{code}", "boolean")

    def _type_operation(self, node: OperationCallExpression) -> _Value:
        source = self._source(node)
        type_arg = next((arg for arg in node.arguments if isinstance(arg, TypeExp)), None)
        if type_arg is None:
            raise OCLTranslationError(f"{node.operation} requires a type argument")
        class_name = type_arg.name
        if node.operation == "OCLISTYPEOF":
            return _Value(f"({source.code} != null && {source.code}.getClass() == {class_name}.class)",
                          "boolean")
        if node.operation == "OCLISKINDOF":
            return _Value(f"({source.code} instanceof {class_name})", "boolean")
        return _Value(f"(({class_name}) {source.code})", class_name)

    def _string_operation(self, node: OperationCallExpression) -> _Value:
        source = self._source(node)
        args = [self.visit(arg) for arg in node.arguments if not isinstance(arg, InfixOperator)]
        op = node.operation
        if op in {"toUpper", "toUpperCase"}:
            return _Value(f"{source.code}.toUpperCase()", "String")
        if op in {"toLower", "toLowerCase"}:
            return _Value(f"{source.code}.toLowerCase()", "String")
        if op == "concat":
            return _Value(f"{source.code}.concat({args[0].code})", "String")
        if op == "substring" and len(args) == 2:
            return _Value(f"{source.code}.substring({args[0].code} - 1, {args[1].code})",
                          "String")
        raise OCLTranslationError(f"Unsupported String operation: {op}")

    def _is_unique(self, node: OperationCallExpression) -> _Value:
        source = self._source(node)
        if not source.many or not node.arguments:
            raise OCLTranslationError("isUnique requires a collection and a body")
        # isUnique(expr) has no named iterator: bare names in expr refer to
        # each element of the collection.
        variable = self._fresh_variable("__unique")
        previous_implicit = self._implicit
        self._implicit = _Value(variable, source.type_name, class_type=source.class_type, boxed=True)
        try:
            body = self.visit(node.arguments[0])
        finally:
            self._implicit = previous_implicit
        mapped = f"{self._stream(source.code)}.map({variable} -> {body.code})"
        return _Value(f"{mapped}.distinct().count() == {source.code}.size()", "boolean")

    @staticmethod
    def _safe_variable(name: str) -> str:
        return f"{name}_" if name in _JAVA_KEYWORDS else name

    def _fresh_variable(self, base: str) -> str:
        used = {value.code for value in self._scope.values()}
        candidate = base
        index = 1
        while candidate in used:
            candidate = f"{base}{index}"
            index += 1
        return candidate

    @staticmethod
    def _stream(code: str) -> str:
        return f"{code}.stream()"
