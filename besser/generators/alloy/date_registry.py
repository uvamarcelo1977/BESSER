"""
date_registry.py

Centralizes all date-related logic for the Alloy generator: encoding/parsing
of ``dMMDDYYYY`` ids, detection of date literals, random date generation for
filling scopes, and the ``dateN -> dMMDDYYYY`` mapping that ties OCL date
literals to the ``one sig`` date atoms of a generated specification.

:class:`DateRegistry` is an immutable-after-build container: the mapping is
produced once (via :meth:`DateRegistry.build`) and then passed around
explicitly instead of being stored in a module-level global. This makes the
generation pipeline safe to run concurrently (each ``AlloySolver`` /
``AlloyGenerator`` owns its own registry) and easy to reuse.
"""

import random
import re
from datetime import date, timedelta

from dateutil import parser as dateutil_parser

# Type names that the Alloy generator treats as dates.
DATE_TYPES = {"date", "datetime", "time", "timedelta"}

# Matches whole date literals such as '2024-01-01', '13-10-1977', '2024/10/13',
# 'Jan 1, 2024' (after stripping surrounding quotes). Used to detect that the
# entire content of a literal is a date.
_DATE_PATTERN = re.compile(
    r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$"
    r"|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,\s+\d{4})?$",
    re.IGNORECASE,
)

YEAR_START = 1970

YEAR_END = 2038

# Matches a raw Alloy date id like ``d01012000``.
DATE_SIG_PATTERN = re.compile(r"^d\d{8}$")

# Matches a ``dMMDDYYYY`` literal id (word boundary) inside a translated fact.
_DATE_LITERAL_PATTERN = re.compile(r"\bd\d{8}\b")

class DateRegistry:
    """Immutable mapping ``dateN -> dMMDDYYYY`` plus Alloy block rendering.

    Built with :meth:`build` (fills a date universe up to *scope* and names the
    dates sequentially in ascending order) or :meth:`empty`. Once built, the
    mapping cannot be mutated, so it is safe to share and to read concurrently.
    """

    __slots__ = ("_by_name",)

    def __init__(self, by_name: dict[str, str]):
        self._by_name = dict(by_name)

    @classmethod
    def build(
        cls,
        ocl_dates: list[str],
        scope: int,
        start: date = date(YEAR_START, 1, 1),
        end: date = date(YEAR_END, 1, 1),
        max_attempts: int = 10000,
    ) -> "DateRegistry":
        """Builds a registry with *scope* unique dates.

        Fills *ocl_dates* up to *scope* with new unique dates, sorts all of
        them ascending and assigns the sequential ``dateN`` sig names
        (``date0``, ``date1``, ...) so that earlier dates get lower indices.

        Raises:
            RuntimeError: If a unique new date cannot be generated within
                *max_attempts* (date range may be exhausted for *scope*).
        """
        dates_set = set(ocl_dates)
        attempts = 0

        while len(dates_set) < scope:
            if attempts >= max_attempts:
                raise RuntimeError(
                    f"Could not generate a unique new date after {max_attempts} attempts "
                    f"(date range may be exhausted for scope={scope})."
                )
            new_d = random_date(start, end)
            encoded = encode_date(new_d)

            # skip if already present, retry
            if encoded in dates_set:
                attempts += 1
                continue

            dates_set.add(encoded)
            attempts = 0  # reset counter after a successful generation

        # sort all dates (original + generated) ascending
        sorted_dates = sorted(dates_set, key=parse_ocl_date)

        return cls({f"date{i}": d for i, d in enumerate(sorted_dates)})

    @classmethod
    def empty(cls) -> "DateRegistry":
        """Returns an empty registry (models without date support)."""
        return cls({})

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def contains_atom(self, atom_label: str) -> bool:
        """Returns ``True`` if *atom_label* refers to one of this registry's dates.

        The atom label may be a sequential name (``date0$0``) or a raw literal
        id (``d01012000$0``).
        """
        base = atom_label.split("$")[0]
        return base in self._by_name or DATE_SIG_PATTERN.match(base) is not None

    def get_date_value(self, atom_label: str) -> str:
        """Extracts the date value from an atom.

        Args:
            atom_label: atom label (e.g., 'date0$0', 'd01012000$0' or 'date$01')

        Returns:
            Date value as an ISO-8601 string with quotes (e.g., '"2000-01-01"')
        """
        base = atom_label.split("$")[0]
        dmmdd = self._by_name.get(base)
        if dmmdd is None and DATE_SIG_PATTERN.match(base):
            dmmdd = base
        if dmmdd is not None:
            return f'"{dmmdd[5:9]}-{dmmdd[1:3]}-{dmmdd[3:5]}"'
        return f'"{atom_label}"'

    def snapshot(self) -> dict[str, str]:
        """Returns a shallow copy of the ``dateN -> dMMDDYYYY`` mapping."""
        return dict(self._by_name)

    def rewrite_facts(self, constraints) -> None:
        """Rewrites translated OCL facts so literals use this registry's atom names.

        Replaces every ``dMMDDYYYY`` literal id produced by :func:`is_date` /
        ``parse_date`` with the sequential ``dateN`` sig name assigned by this
        registry (via :meth:`build`), so OCL date constants use exactly the
        same atoms as randomly generated dates. Unknown ids (not present in
        the registry) are left untouched.

        Args:
            constraints: Iterable of objects exposing an ``expression``
                attribute (e.g. BUML ``Constraint`` instances).
        """
        if not self._by_name:
            return
        name_by_id = {v: k for k, v in self._by_name.items()}
        for constraint in constraints:
            constraint.expression = _DATE_LITERAL_PATTERN.sub(
                lambda m: name_by_id.get(m.group(0), m.group(0)),
                constraint.expression,
            )

    # ------------------------------------------------------------------
    # Alloy block rendering
    # ------------------------------------------------------------------

    def render_sigs_and_order(self) -> str:
        """Emits a ``one sig dateN extends Date {}`` line for every date (sorted
        ascending) and a fact fixing the total order from smallest to largest.
        """
        names = sorted(self._by_name, key=lambda n: parse_ocl_date(self._by_name[n]))
        if not names:
            return ""

        res = ''.join(f"one sig {n} extends Date {{}}\n" for n in names)

        fact_lines = [f"{names[0]} = first"]
        for i in range(len(names) - 1):
            fact_lines.append(f"{names[i]}.next = {names[i + 1]}")
        fact_lines.append(f"{names[-1]} = last")

        res += 'fact Order {\n'
        res += '\n'.join(f'    {line}' for line in fact_lines)
        res += '\n}\n'

        return res

    # ------------------------------------------------------------------
    # Dunder protocol
    # ------------------------------------------------------------------

    def __bool__(self) -> bool:
        return bool(self._by_name)

    
def parse_ocl_date(s: str) -> date:
    """Converts ``'dMMDDYYYY'`` -> ``date``. E.g. ``'d10131977'`` -> ``date(1977, 10, 13)``."""
    mm = int(s[1:3])
    dd = int(s[3:5])
    yyyy = int(s[5:9])
    return date(yyyy, mm, dd)


def encode_date(d: date) -> str:
    """Converts ``date`` -> ``'dMMDDYYYY'``."""
    return 'd' + d.strftime('%m%d%Y')


def random_date(start: date, end: date) -> date:
    """Generates a random date between *start* and *end* (inclusive)."""
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


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


