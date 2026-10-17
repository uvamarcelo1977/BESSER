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

import datetime

from besser.BUML.metamodel.object import Link, LinkEnd, Object, ObjectModel
from besser.BUML.metamodel.structural import (
    BinaryAssociation, Class, DateType, Enumeration, EnumerationLiteral, IntegerType, Multiplicity, Property,
    StringType,
)
from besser.utilities.buml_code_builder.domain_model_builder import object_model_to_code
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


def test_exported_object_model_round_trips(tmp_path):
    """Export an ObjectModel with the B-UML exporter, import the file, and check nothing is lost."""
    gk = EnumerationLiteral("GK")
    position = Enumeration("Position", literals={gk, EnumerationLiteral("FW")})
    team = Class("Team", attributes={Property("tname", StringType)})
    player = Class("Player", attributes={
        Property("born", DateType), Property("pos", position), Property("age", IntegerType),
    })
    team_end = Property("team", team, multiplicity=Multiplicity(1, 1))
    players_end = Property("players", player, multiplicity=Multiplicity(0, "*"))
    team_players = BinaryAssociation("team_players", ends={team_end, players_end})

    t0 = Object("t0", team)
    t0.tname = "Lions"
    p0 = Object("p0", player)
    p0.born = datetime.date(2000, 1, 2)
    p0.pos = gk
    p0.age = 20
    p1 = Object("p1", player)
    p1.age = 30
    for p in (p0, p1):
        Link("team_players", team_players, [LinkEnd("team", team_end, t0), LinkEnd("players", players_end, p)])

    code_file = tmp_path / "object_model.py"
    object_model_to_code(ObjectModel("OM", objects={t0, p0, p1}), str(code_file))
    result = object_buml_to_json(code_file.read_text(encoding="utf-8"), _reference_class_diagram())
    names = _attribute_names(result)

    assert "tname = Lions" in names
    assert "age = 20" in names
    assert "age = 30" in names
    assert "pos = GK" in names
    assert "born = 2000-01-02" in names
    assert len(_links(result)) == 2
