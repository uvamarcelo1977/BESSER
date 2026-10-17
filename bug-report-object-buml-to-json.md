**Title:** `object_buml_to_json` drops enum values, date values and many-valued links written by the B-UML exporter

---

### Describe the bug

`object_buml_to_json`
(`besser/utilities/web_modeling_editor/backend/services/converters/buml_to_json/object_diagram_converter.py`)
converts object-model Python code back into editor JSON. It reads the code as an AST and silently skips three
forms that BESSER's own exporter, `_write_object_model_section`
(`besser/utilities/buml_code_builder/domain_model_builder.py`), writes:

| # | The exporter writes | Why the converter drops it | Result |
|---|---|---|---|
| 1 | `pos=Position.GK` (enumeration literal) | only `ast.Constant` keyword values are read (`object_diagram_converter.py:156`) | attribute missing |
| 2 | `born=datetime.datetime.fromisoformat("2000-01-02")` | same check (`:156`) | attribute missing |
| 3 | `t0_obj.players = {p0_obj, p1_obj}` (many-valued link) | only a single `ast.Name` on the right-hand side is read (`:286`) | all links of that end missing |

No error or warning is raised.

### To Reproduce

One failing test per defect, in
`tests/utilities/web_modeling_editor/backend/services/converters/test_object_buml_to_json.py`:

```bash
python -m pytest tests/utilities/web_modeling_editor/backend/services/converters/test_object_buml_to_json.py -q
```

```
test_enum_attribute_value_is_kept                  AssertionError: assert 'pos = GK' in {'age = 20'}
test_date_attribute_value_is_kept                  AssertionError: assert 'born = 2000-01-02' in {'age = 20'}
test_set_valued_link_creates_one_link_per_target   assert 0 == 2
```

Each test passes the converter one form, exactly as the exporter writes it. In the first two tests, a plain integer attribute (`age = 20`) is set alongside as a control. It survives, which shows that only the special form is lost.

### Expected behavior

1. `Position.GK` → ObjectAttribute `pos = GK`
2. `datetime.datetime.fromisoformat("2000-01-02")` → ObjectAttribute `born = 2000-01-02`
3. `t0_obj.players = {p0_obj, p1_obj}` → one ObjectLink per target (two links)
