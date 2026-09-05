"""Tests for `besser.generators.alloy.instance_generator.alloy_solver`.

These tests invoke every module-level function and every class of
`alloy_solver.py` directly in Python, without going through the FastAPI
web-editor endpoint. Object-diagram generation tests drive `AlloySolver` with
the **real** Alloy Analyzer (``java -jar alloy.jar``) as an external process;
they are skipped when the jar or a JRE is not available. Pure helper functions
are unit-tested directly.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from besser.BUML.metamodel.structural import (
    BinaryAssociation,
    Class,
    Constraint,
    DomainModel,
    Generalization,
    IntegerType,
    Multiplicity,
    Property,
    StringType,
)
from besser.generators.alloy.alloy_utils_generator import (
    build_inheritance_and_attribute_maps,
    process_associations,
    translate_constraints,
)
from besser.generators.alloy.instance_generator.alloy_solver import (
    AlloySolver,
)
from besser.generators.alloy.instance_generator.alloy_solver_utils import (
    parse_receipt,
    resolve_alloy_jar_path,
    resolve_java_path,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def team_player_model():
    """Team 1 -- 3..4 Player."""
    team = Class(name="Team")
    player = Class(name="Player")
    team.attributes = {Property(name="name", type=StringType)}
    player.attributes = {
        Property(name="name", type=StringType),
        Property(name="age", type=IntegerType),
    }
    plays_for = BinaryAssociation(
        name="PlaysFor",
        ends={
            Property(name="players", type=player, multiplicity=Multiplicity(3, 4)),
            Property(name="team", type=team, multiplicity=Multiplicity(1, 1)),
        },
    )
    return DomainModel(name="TeamModel", types={team, player}, associations={plays_for})


@pytest.fixture
def person_model():
    """A minimal one-class model: Person(name: str)."""
    person = Class(name="Person")
    person.attributes = {Property(name="name", type=StringType)}
    return DomainModel(name="PersonModel", types={person})


def _alloy_real():
    """True when the real Alloy Analyzer (alloy.jar + java) is available.

    The object-generation tests that go through ``AlloySolver`` need to run the
    actual ``java -jar alloy.jar`` call; if the jar or a JRE is missing they are
    skipped rather than failing.
    """
    return resolve_alloy_jar_path() is not None and resolve_java_path() is not None


# ---------------------------------------------------------------------------
# build_inheritance_and_attribute_maps
# ---------------------------------------------------------------------------


class TestBuildInheritanceAndAttributeMaps:

    def test_class_without_parents_maps_to_underscore(self, team_player_model):
        inherits_from, data, basic_signatures, sigs_nv = build_inheritance_and_attribute_maps(team_player_model)

        assert inherits_from["Team"] == ["_"]
        assert inherits_from["Player"] == ["_"]
        assert "name:str" in data["Team"]
        assert "age:int" in data["Player"]
        assert {"str", "int"} <= basic_signatures
        assert "Team" in sigs_nv and "Player" in sigs_nv

    def test_generalization_records_parent_name(self):
        animal = Class(name="Animal")
        dog = Class(name="Dog")
        animal.attributes = {Property(name="name", type=StringType)}
        genealogy = Generalization(general=animal, specific=dog)
        model = DomainModel(
            name="Zoo", types={animal, dog}, generalizations={genealogy}
        )

        inherits_from, _, _, _ = build_inheritance_and_attribute_maps(model)

        assert inherits_from["Dog"] == ["Animal"]
        assert inherits_from["Animal"] == ["_"]


# ---------------------------------------------------------------------------
# process_associations
# ---------------------------------------------------------------------------


class TestProcessAssociations:

    def test_association_ends_added_to_both_sides(self, team_player_model):
        _, data, _, _ = build_inheritance_and_attribute_maps(team_player_model)

        facts = process_associations(team_player_model, data)

        assert "players:Player" in data["Team"]
        assert "team:Team" in data["Player"]
        assert len(facts) >= 1


# ---------------------------------------------------------------------------
# translate_constraints
# ---------------------------------------------------------------------------


class TestTranslateConstraints:

    def test_ocl_expression_is_replaced_by_alloy_fact(self, team_player_model):
        inherits_from, data, _, _ = build_inheritance_and_attribute_maps(team_player_model)
        process_associations(team_player_model, data)

        player_class = team_player_model.get_class_by_name("Player")
        constraint = Constraint(
            name="AgePositive",
            context=player_class,
            expression="context Player inv AgePositive: self.age > 0",
            language="OCL",
        )
        team_player_model.constraints = {constraint}

        translate_constraints(team_player_model, inherits_from, data, enums={})

        assert "Player_age > 0" in constraint.expression
        assert "fact{" in constraint.expression


# ---------------------------------------------------------------------------
# AlloySolver
# ---------------------------------------------------------------------------


class TestAlloySolverConstruction:

    def test_generates_als_file_and_sanitizes_names(self, tmpdir):
        # Valid BUML name (no spaces/hyphens) that is still invalid for Alloy.
        team = Class(name="Clase_Número")
        team.attributes = {Property(name="1attr", type=StringType)}
        model = DomainModel(name="M", types={team})

        solver = AlloySolver(model=model, output_dir=str(tmpdir.mkdir("out")))

        assert os.path.isfile(solver.file)
        with open(solver.file, encoding="utf-8") as f:
            als_content = f.read()
        # The generated .als must use sanitized, Alloy-valid identifiers.
        assert re.search(r"sig\s+Clase_Nmero", als_content)
        assert re.search(r"Clase_Nmero__1attr", als_content)
        # The original model must NOT be mutated.
        original = model.classes_sorted_by_inheritance()[0]
        assert original.name == "Clase_Número"
        assert {a.name for a in original.attributes} == {"1attr"}


class TestAlloySolverJarResolution:

    def test_uses_besser_alloy_jar_env_var(self, tmp_path, monkeypatch):
        fake_jar = tmp_path / "alloy.jar"
        fake_jar.write_text("", encoding="utf-8")
        monkeypatch.setenv("BESSER_ALLOY_JAR", str(fake_jar))

        assert resolve_alloy_jar_path() == str(fake_jar)

    def test_falls_back_to_default_location_when_env_var_invalid(self, monkeypatch):
        # An invalid BESSER_ALLOY_JAR must not crash; it falls back to the
        # bundled jar shipped under besser/BUML/notations/ocl/consistency/.
        monkeypatch.setenv("BESSER_ALLOY_JAR", "/nonexistent/alloy.jar")

        jar_path = resolve_alloy_jar_path()

        assert jar_path is None or jar_path.endswith("alloy.jar")


class TestAlloySolverExecuteAndParse:

    def test_parse_receipt_reports_error_when_missing(self, tmp_path):
        exec_output_dir = tmp_path / "exec_out"
        exec_output_dir.mkdir()
        fake_result = subprocess.CompletedProcess(args=["java"], returncode=0, stdout="boom", stderr="")

        parsed, error = parse_receipt(str(exec_output_dir), fake_result)

        assert parsed is None
        assert error["isValid"] is False


class TestAlloySolverPipelineWithoutEndpoint:
    """Exercises the full "generate an object diagram" pipeline directly on
    AlloySolver, running the real Alloy Analyzer (alloy.jar) as an external
    process. Every test builds a fresh model and writes the generated .als and
    instance XML into a temporary directory."""
    scope = 3

    @pytest.fixture(autouse=True)
    def _skip_unless_alloy(self):
        if not _alloy_real():
            pytest.skip("Real Alloy Analyzer (alloy.jar + java) not available")

    def test_check_consistency(self, person_model, tmpdir):
        solver = AlloySolver(model=person_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)

        satisfiable = solver.check_consistency()
        assert satisfiable is True

    def test_generate_instance_xml(self, person_model, tmpdir):
        solver = AlloySolver(model=person_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)

        xml_path = solver.generate_instance_xml()

        assert xml_path is not None
        assert os.path.isfile(xml_path)
        assert Path(xml_path).suffix == ".xml"

    def test_generate_object_diagram_code(self, person_model, tmpdir):
        solver = AlloySolver(model=person_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        code = solver.generate_object_diagram_code(xml_instance_path=xml_path)

        assert code is not None
        assert 'Person("Person_' in code
        assert "ObjectModel(" in code

    def test_generate_object_diagram_code_writes_output_dir(self, person_model, tmpdir):
        solver = AlloySolver(model=person_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        instances_dir = str(tmpdir.mkdir("instances"))

        code = solver.generate_object_diagram_code(output_dir=instances_dir)

        assert isinstance(code, str)
        assert "ObjectModel(" in code
        instance_file = Path(instances_dir) / "buml_object_instance1.py"
        assert instance_file.is_file()
        assert "ObjectModel(" in instance_file.read_text(encoding="utf-8")

    def test_generate_object_diagram_code_multiple_instances(self, person_model, tmpdir):
        solver = AlloySolver(model=person_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        instances_dir = str(tmpdir.mkdir("instances"))

        codes = solver.generate_object_diagram_code(num_instances=3, output_dir=instances_dir)

        assert isinstance(codes, list)
        assert len(codes) >= 1
        assert all("ObjectModel(" in code for code in codes)
        written = sorted(Path(instances_dir).glob("buml_object_instance*.py"))
        assert len(written) == len(codes)
        expected_names = [f"buml_object_instance{i}.py" for i in range(1, len(codes) + 1)]
        assert [p.name for p in written] == expected_names

    def test_generate_object_diagram_json(self, person_model, tmpdir):
        solver = AlloySolver(model=person_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        reference_model = {
            "elements": {
                "elem_1": {
                    "name": "Person",
                    "type": "Class",
                    "attributes": {"attr_1": {"name": "name", "type": "str"}},
                }
            },
            "relationships": {},
        }
        obj_json = solver.generate_object_diagram_json(reference_model, xml_instance_path=xml_path)

        assert obj_json is not None
        assert "elements" in obj_json

    def test_generate_integrated_buml_model(self, person_model, tmpdir):
        solver = AlloySolver(model=person_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        integrated_code = solver.generate_integrated_buml_model(xml_instance_path=xml_path)

        assert integrated_code is not None
        assert "# OBJECT MODEL #" in integrated_code
        assert 'Person("Person_' in integrated_code

    def test_generate_object_diagram_code_returns_none_when_unsat(self, person_model, tmpdir):
        # A model is guaranteed to be unsatisfiable by adding two contradictory
        # OCL invariants, which are translated to mutually exclusive Alloy facts.
        from besser.BUML.metamodel.structural import Constraint

        person = Class(name="Person")
        person.attributes = {
            Property(name="name", type=StringType),
            Property(name="age", type=IntegerType),
        }
        positive = Constraint(
            name="Positive",
            context=person,
            expression="context Person inv Positive: self.age > 0",
            language="OCL",
        )
        negative = Constraint(
            name="Negative",
            context=person,
            expression="context Person inv Negative: self.age < 0",
            language="OCL",
        )
        unsat_model = DomainModel(
            name="UnsatModel", types={person}, constraints={positive, negative}
        )

        solver = AlloySolver(model=unsat_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)

        assert solver.generate_object_diagram_code() is None


# ---------------------------------------------------------------------------
# AlloySolver – pipeline with Team/Player rich model
# ---------------------------------------------------------------------------


class TestAlloySolverInstanceGenerationRichModel:
    """Full pipeline tests using the Team/Player model, running the real Alloy
    Analyzer. Teams have 3..4 players, so a satisfying instance always contains
    at least one Team and three Player objects; exact object counts and labels
    are left unchecked because Alloy picks them non-deterministically."""
    scope = 8

    @pytest.fixture(autouse=True)
    def _skip_unless_alloy(self):
        if not _alloy_real():
            pytest.skip("Real Alloy Analyzer (alloy.jar + java) not available")

    def test_generate_object_diagram_code_team_player(self, team_player_model, tmpdir):
        solver = AlloySolver(model=team_player_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        code = solver.generate_object_diagram_code(xml_instance_path=xml_path)

        assert code is not None
        assert re.search(r'^\w+_obj = Team\("Team_', code, re.MULTILINE)
        assert re.search(r'^\w+_obj = Player\("Player_', code, re.MULTILINE)

    def test_generate_object_diagram_code_includes_attributes(self, team_player_model, tmpdir):
        solver = AlloySolver(model=team_player_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        code = solver.generate_object_diagram_code(xml_instance_path=xml_path)

        assert "'name':" in code
        assert "'age':" in code

    def test_generate_object_diagram_code_includes_association(self, team_player_model, tmpdir):
        solver = AlloySolver(model=team_player_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        code = solver.generate_object_diagram_code(xml_instance_path=xml_path)

        assert "setattr(" in code
        # The association should connect team to players or vice versa
        assert "team" in code
        assert "player" in code

    def test_generate_object_diagram_code_object_model_contains_all(self, team_player_model, tmpdir):
        solver = AlloySolver(model=team_player_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        code = solver.generate_object_diagram_code(xml_instance_path=xml_path)

        assert "ObjectModel(" in code
        # Team and Player objects must appear in the ObjectModel constructor
        assert "Team(" in code
        assert "Player(" in code

    def test_generate_integrated_buml_model_team_player(self, team_player_model, tmpdir):
        solver = AlloySolver(model=team_player_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        integrated = solver.generate_integrated_buml_model(xml_instance_path=xml_path)

        assert integrated is not None
        assert "# OBJECT MODEL #" in integrated
        assert 'Team("Team_' in integrated
        assert 'Player("Player_' in integrated

    def test_generate_integrated_buml_model_executes(self, team_player_model, tmpdir):
        # The integrated model is a valid .py script: it can be exec'd to
        # reconstruct the class diagram + object model from the real Alloy
        # instance.
        solver = AlloySolver(model=team_player_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        integrated = solver.generate_integrated_buml_model(xml_instance_path=xml_path)

        namespace = {}
        exec(compile(integrated, "<integrated>", "exec"), namespace)  # noqa: S102

        object_model = namespace["object_model"]
        assert object_model.name == "Object_Diagram"
        objects = object_model.objects
        assert len(objects) >= 1
        class_names = {obj.classifier.name for obj in objects}
        assert "Team" in class_names
        assert "Player" in class_names

    def test_generate_object_diagram_json_team_player(self, team_player_model, tmpdir):
        solver = AlloySolver(model=team_player_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)
        xml_path = solver.generate_instance_xml()

        reference_model = {
            "elements": {
                "e_team": {
                    "name": "Team",
                    "type": "Class",
                    "attributes": {"a1": {"name": "name", "type": "str"}},
                },
                "e_player": {
                    "name": "Player",
                    "type": "Class",
                    "attributes": {
                        "a1": {"name": "name", "type": "str"},
                        "a2": {"name": "age", "type": "int"},
                    },
                },
            },
            "relationships": {},
        }
        obj_json = solver.generate_object_diagram_json(reference_model, xml_instance_path=xml_path)

        assert obj_json is not None
        assert "elements" in obj_json

    def test_check_consistency(self, team_player_model, tmpdir):
        solver = AlloySolver(model=team_player_model, output_dir=str(tmpdir.mkdir("out")), scope=self.scope)

        satisfiable = solver.check_consistency()

        assert satisfiable is True
