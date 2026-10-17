**Title:** `object_buml_to_json` drops enum values, date values and many-valued links written by the B-UML exporter

---

### Describe the bug

`object_buml_to_json`
(`besser/utilities/web_modeling_editor/backend/services/converters/buml_to_json/object_diagram_converter.py`)
converts object-model Python code back into editor JSON. It reads the code as an AST and silently skips three forms that should belong to the output JSON:

1. enumeration values, e.g. `pos=Position.GK`
2. date values, e.g. `born=datetime.datetime.fromisoformat("2000-01-02")`
3. many-valued links, e.g. `t0_obj.players = {p0_obj, p1_obj}`

No error or warning is raised, just missing parts in the output JSON.

### To Reproduce

One failing test per defect, in
`tests/utilities/web_modeling_editor/backend/services/converters/test_object_buml_to_json.py`. The tests were added in commit
[`37aa1867`](https://github.com/uvamarcelo1977/BESSER/commit/37aa1867c9906a22fa0003a18be5e8169d9d876f)
on branch
[`test/object-buml-to-json-dropped-values`](https://github.com/uvamarcelo1977/BESSER/tree/test/object-buml-to-json-dropped-values),
which is based on `development`:

```bash
python -m pytest tests/utilities/web_modeling_editor/backend/services/converters/test_object_buml_to_json.py -q
```

Each test passes the converter one form, exactly as the exporter writes it. In the first two tests, a plain integer attribute (`age = 20`) is set alongside as a control. It survives, which shows that only the special form is lost.

**1. Enumeration value**

```python
def test_enum_attribute_value_is_kept():
    code = 'p0_obj = Player("p0").attributes(pos=Position.GK, age=20).build()\n'

    names = _attribute_names(object_buml_to_json(code, _reference_class_diagram()))

    assert "age = 20" in names
    assert "pos = GK" in names
```

Expected: `Position.GK` → ObjectAttribute `pos = GK`. Actual:

```
AssertionError: assert 'pos = GK' in {'age = 20'}
```

**2. Date value**

```python
def test_date_attribute_value_is_kept():
    code = 'p0_obj = Player("p0").attributes(born=datetime.datetime.fromisoformat("2000-01-02"), age=20).build()\n'

    names = _attribute_names(object_buml_to_json(code, _reference_class_diagram()))

    assert "age = 20" in names
    assert "born = 2000-01-02" in names
```

Expected: `datetime.datetime.fromisoformat("2000-01-02")` → ObjectAttribute `born = 2000-01-02`. Actual:

```
AssertionError: assert 'born = 2000-01-02' in {'age = 20'}
```

**3. Many-valued link**

```python
def test_set_valued_link_creates_one_link_per_target():
    code = (
        'p0_obj = Player("p0").attributes(age=20).build()\n'
        'p1_obj = Player("p1").attributes(age=30).build()\n'
        't0_obj = Team("t0").attributes(tname="Lions").build()\n'
        "\n"
        "t0_obj.players = {p0_obj, p1_obj}\n"
    )

    links = _links(object_buml_to_json(code, _reference_class_diagram()))

    assert len(links) == 2
```

Expected: `t0_obj.players = {p0_obj, p1_obj}` → one ObjectLink per target (two links). Actual:

```
assert 0 == 2
 +  where 0 = len([])
```

### Additional context

It is very important for the Alloy PR https://github.com/BESSER-PEARL/BESSER/pull/614 that 
this bug is fixed. The Alloy generator produces object diagrams from Alloy instances and shows them in the editor through `object_buml_to_json`. Until this is fixed, the generated objects would appear in the editor without their enumeration and date values, and without their many-valued links.

Notice that Claude can generate a candidate patch for this issue without user assistance, but I'm not an expert in the BUML language implementation and cannot evaluate the patch properly.