import pytest
from besser.generators.alloy.ocl_translator_new import UnsupportedOclError
from tests.generators.alloy.BUML_library_with_ocl_v2 import library_with_ocl_v2
from tests.generators.alloy.utils_alloy_re_parser import AlloySpec
from tests.generators.alloy.utils_alloy_translation import translate


@pytest.mark.parametrize("value, characters", [
    ("Cortázar!", "'á', '!'"),
    ("a b", "' '"),
    ("x-y-z", "'-'"),
    # the escape is resolved before the check: the value is it's
    ("it\\'s", "\"'\""),
])
def test_strings_with_invalid_identifier_characters_are_unsupported(library_with_ocl_v2, value, characters):
    with pytest.raises(UnsupportedOclError, match=f"the translation of the characters {characters} is unsupported"):
        translate(library_with_ocl_v2, "Author", f"self.name = '{value}'", scope=5)


@pytest.mark.parametrize("constraint, str_sigs", [
    # the empty string
    ("self.name = ''", {"Str_", "Str_str0", "Str_str1"}),
    # underscores and digits are identifier characters
    ("self.name = 'a_1'", {"Str_a_1", "Str_str0", "Str_str1"}),
    # the Str_ prefix makes a leading digit valid
    ("self.name = '1abc'", {"Str_1abc", "Str_str0", "Str_str1"}),
    # the Str_ prefix keeps Alloy keywords from clashing
    ("self.name = 'sig'", {"Str_sig", "Str_str0", "Str_str1"}),
    # strings are case sensitive
    ("self.name = 'Borges' or self.name = 'borges'", {"Str_Borges", "Str_borges", "Str_str0"}),
    # a repeated literal is declared once
    ("self.name = 'borges' or self.name = 'borges'", {"Str_borges", "Str_str0", "Str_str1"}),
])
def test_strings_with_valid_identifier_characters(library_with_ocl_v2, constraint, str_sigs):
    spec = translate(library_with_ocl_v2, "Author", constraint, scope=3)
    assert {sig for sig in spec.sigs if sig.startswith("one sig Str_")} == \
        {f"one sig {name} extends Str" for name in str_sigs}
    assert "3 Str" in spec.run_scopes


def test_string_constants_one_literal(library_with_ocl_v2):
    spec = translate(library_with_ocl_v2, "Author", "self.name = 'borges'", scope=3)
    str_sigs = {sig for sig in spec.sigs if sig.startswith("one sig Str_")}
    assert len(str_sigs) == 3
    assert "one sig Str_borges extends Str" in spec.sigs
    assert "one sig Str_str0 extends Str" in str_sigs
    assert "one sig Str_str1 extends Str" in str_sigs
    assert "3 Str" in spec.run_scopes


def test_other_strings_skip_taken_names(library_with_ocl_v2):
    spec = translate(library_with_ocl_v2, "Author", "self.name = 'str0'", scope=3)
    str_sigs = {sig for sig in spec.sigs if sig.startswith("one sig Str_")}
    assert len(str_sigs) == 3
    assert "one sig Str_str0 extends Str" in str_sigs
    assert "one sig Str_str1 extends Str" in str_sigs
    assert "one sig Str_str2 extends Str" in str_sigs
    assert "3 Str" in spec.run_scopes


def test_str_scope_holds_all_literals(library_with_ocl_v2):
    spec = translate(library_with_ocl_v2, "Author", "self.name = 'a' or self.name = 'b' or self.name = 'c'", scope=2)
    str_sigs = {sig for sig in spec.sigs if sig.startswith("one sig Str_")}
    assert len(str_sigs) == 3
    assert "one sig Str_a extends Str" in spec.sigs
    assert "one sig Str_b extends Str" in spec.sigs
    assert "one sig Str_c extends Str" in spec.sigs
    assert "3 Str" in spec.run_scopes
    assert "2 Author" in spec.run_scopes



