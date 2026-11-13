"""Tests del caso de estudio school (examples/school)."""
import json
import os
import sys

from besser.utilities.web_modeling_editor.backend.services.converters import (
    process_class_diagram, process_object_diagram)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # pytest usa --import-mode=importlib
from cases import build_buml_project, load_result  # noqa: E402

RESULT = load_result("school")
STRUCTURES = RESULT["structures"]


def test_beapi_genera_54_estructuras_con_raiz_student():
    assert RESULT["rootClass"] == "Student"
    assert RESULT["structureCount"] == 54 == len(STRUCTURES)


def test_la_raiz_de_cada_estructura_es_un_student():
    for s in STRUCTURES:
        root = next(o for o in s["objects"] if o["id"] == s["root"])
        assert root["class"] == "Student"


def test_solo_aparecen_clases_y_asociaciones_del_modelo():
    classes = {o["class"] for s in STRUCTURES for o in s["objects"]}
    associations = {l["association"] for s in STRUCTURES for l in s["links"]}
    assert classes == {"Student", "Subject", "InfoExam"}
    assert associations == {"Enrollment", "StudentExams", "SubjectExams"}


def test_las_fechas_se_exportan_como_texto():
    student = STRUCTURES[0]["objects"][0]
    birth = next(a for a in student["attributes"] if a["name"] == "birthDate")
    assert birth["value"] == "2000-01-02"


def test_proyecto_buml_tiene_un_diagrama_de_objetos_por_estructura(tmp_path):
    _, [(out, diagrams)] = build_buml_project("school", RESULT, tmp_path)
    with open(out, encoding="utf-8") as f:
        project = json.load(f)["project"]
    assert len(diagrams) == 54
    assert project["diagrams"]["ObjectDiagram"][-54:] == diagrams
    assert diagrams[0]["title"] == "BEAPI structure 1"


def test_besser_importa_cada_diagrama_de_objetos(tmp_path):
    model, [(_, diagrams)] = build_buml_project("school", RESULT, tmp_path)
    domain = process_class_diagram(model["class_diagram"])
    for s, diagram in zip(STRUCTURES, diagrams):
        objects = process_object_diagram(diagram, domain)
        assert len(objects.objects) == len(s["objects"])
        assert len(objects.links) == len(s["links"])
