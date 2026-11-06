"""Tests del caso de estudio hospital (examples/hospital).

Leen output/hospital.json (generado con: python3 beapi_gen.py hospital)
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

with open(os.path.join(ROOT, "output", "hospital.json"), encoding="utf-8") as f:
    RESULT = json.load(f)
STRUCTURES = RESULT["structures"]


def build_buml_project(tmp_path):
    """Ejecuta el paso --buml y devuelve el proyecto BESSER generado."""
    args = argparse.Namespace(buml_base=None, buml_structures=None, buml_class_diagram=None,
                              buml_split=False, output_dir=str(tmp_path))
    [out] = beapi_gen.write_buml_projects("hospital", RESULT, os.path.join(ROOT, "examples", "hospital"), args)
    with open(out, encoding="utf-8") as f:
        return json.load(f)["project"]


def values(cls, attribute):
    """Valores que toma un atributo de una clase en todas las estructuras."""
    return [a["value"] for s in STRUCTURES for o in s["objects"] if o["class"] == cls
            for a in o["attributes"] if a["name"] == attribute]


def test_beapi_genera_16_estructuras_con_raiz_doctor():
    assert RESULT["rootClass"] == "Doctor"
    assert RESULT["structureCount"] == 16 == len(STRUCTURES)


def test_la_raiz_de_cada_estructura_es_un_doctor():
    for s in STRUCTURES:
        root = next(o for o in s["objects"] if o["id"] == s["root"])
        assert root["class"] == "Doctor"


def test_solo_aparecen_clases_y_asociaciones_del_modelo():
    classes = {o["class"] for s in STRUCTURES for o in s["objects"]}
    associations = {l["association"] for s in STRUCTURES for l in s["links"]}
    assert classes == {"Doctor", "Patient", "MedicalAppointment"}
    assert associations == {"DoctorAppointments", "Patient_Doctor", "PatientAppointments"}


def test_los_atributos_heredados_de_person_se_exportan():
    assert set(values("Doctor", "fullName")) == {"a"}
    assert set(values("Patient", "fullName")) == {"a"}


def test_los_enums_usan_los_literales_de_beapi_json():
    assert {v["literal"] for v in values("Patient", "bloodGroup")} == {"AB_POSITIVE"}
    assert {v["literal"] for v in values("MedicalAppointment", "status")} == {"SCHEDULED"}


def test_proyecto_buml_tiene_un_diagrama_de_objetos_por_estructura(tmp_path):
    project = build_buml_project(tmp_path)
    diagrams = project["diagrams"]["ObjectDiagram"]
    assert len(diagrams) == 16
    assert diagrams[0]["title"] == "BEAPI structure 1"


def test_besser_importa_cada_diagrama_de_objetos(tmp_path):
    project = build_buml_project(tmp_path)
    domain = process_class_diagram(project["diagrams"]["ClassDiagram"][0])
    for s, diagram in zip(STRUCTURES, project["diagrams"]["ObjectDiagram"]):
        objects = process_object_diagram(diagram, domain)
        assert len(objects.objects) == len(s["objects"])
        assert len(objects.links) == len(s["links"])
