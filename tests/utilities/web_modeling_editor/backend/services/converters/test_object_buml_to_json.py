"""
Tests for object_buml_to_json reading object-model code written by the B-UML exporter.

The code snippets below use the exact forms that ``_write_object_model_section``
(``besser/utilities/buml_code_builder/domain_model_builder.py``) emits when an object
diagram or a project is exported. Importing that file again must not lose any value:
  - enumeration values are written as ``Enum.LITERAL``
  - date values are written as ``datetime.datetime.fromisoformat("...")``
  - many-valued links are written as ``obj.role = {target1, target2}``

Each test also sets a plain ``age`` value as a control, so that a failure shows that
only the special form is dropped.
"""

from besser.utilities.web_modeling_editor.backend.services.converters.buml_to_json.object_diagram_converter import (
    object_buml_to_json,
)


def _reference_class_diagram():
    """Minimal class-diagram JSON: Team(tname) 1 -- * Player(born, pos, age)."""
    def attribute(attr_id, name, attr_type):
        return {"id": attr_id, "name": name, "type": "ClassAttribute", "attributeType": attr_type}

    return {
        "elements": {
            "team": {"id": "team", "type": "Class", "name": "Team", "attributes": ["tname"]},
            "tname": attribute("tname", "tname", "str"),
            "player": {"id": "player", "type": "Class", "name": "Player", "attributes": ["born", "pos", "age"]},
            "born": attribute("born", "born", "date"),
            "pos": attribute("pos", "pos", "Position"),
            "age": attribute("age", "age", "int"),
        },
        "relationships": {
            "team_players": {
                "id": "team_players",
                "type": "ClassBidirectional",
                "source": {"element": "player", "role": "team"},
                "target": {"element": "team", "role": "players"},
            },
        },
    }


def _attribute_names(result):
    return {e["name"] for e in result["elements"].values() if e["type"] == "ObjectAttribute"}


def _links(result):
    return [r for r in result["relationships"].values() if r["type"] == "ObjectLink"]


def test_enum_attribute_value_is_kept():
    code = 'p0_obj = Player("p0").attributes(pos=Position.GK, age=20).build()\n'

    names = _attribute_names(object_buml_to_json(code, _reference_class_diagram()))

    assert "age = 20" in names
    assert "pos = GK" in names


def test_date_attribute_value_is_kept():
    code = 'p0_obj = Player("p0").attributes(born=datetime.datetime.fromisoformat("2000-01-02"), age=20).build()\n'

    names = _attribute_names(object_buml_to_json(code, _reference_class_diagram()))

    assert "age = 20" in names
    assert "born = 2000-01-02" in names


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
