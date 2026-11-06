"""Tests del caso de estudio school (examples/school).

Leen output/school.json (generado con: python3 beapi_gen.py school)
y arman el proyecto BESSER (--buml) en un directorio temporal.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import beapi_gen  # noqa: E402
from besser.utilities.web_modeling_editor.backend.services.converters import (  # noqa: E402
    process_class_diagram, process_object_diagram)

with open(os.path.join(ROOT, "output", "school.json"), encoding="utf-8") as f:
    RESULT = json.load(f)
STRUCTURES = RESULT["structures"]


def build_buml_project(tmp_path):
    """Ejecuta el paso --buml y devuelve el proyecto BESSER generado."""
    args = argparse.Namespace(buml_base=None, buml_structures=None, buml_class_diagram=None,
                              buml_split=False, output_dir=str(tmp_path))
    [out] = beapi_gen.write_buml_projects("school", RESULT, os.path.join(ROOT, "examples", "school"), args)
    with open(out, encoding="utf-8") as f:
        return json.load(f)["project"]


def test_beapi_genera_27_estructuras_con_raiz_student():
    assert RESULT["rootClass"] == "Student"
    assert RESULT["structureCount"] == 27 == len(STRUCTURES)


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
    project = build_buml_project(tmp_path)
    diagrams = project["diagrams"]["ObjectDiagram"]
    assert len(diagrams) == 27
    assert diagrams[0]["title"] == "BEAPI structure 1"


def test_besser_importa_cada_diagrama_de_objetos(tmp_path):
    project = build_buml_project(tmp_path)
    domain = process_class_diagram(project["diagrams"]["ClassDiagram"][0])
    for s, diagram in zip(STRUCTURES, project["diagrams"]["ObjectDiagram"]):
        objects = process_object_diagram(diagram, domain)
        assert len(objects.objects) == len(s["objects"])
        assert len(objects.links) == len(s["links"])
