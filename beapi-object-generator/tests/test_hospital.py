"""Tests del caso de estudio hospital (examples/hospital)."""
import os
import sys

from besser.utilities.web_modeling_editor.backend.services.converters import (
    process_class_diagram, process_object_diagram)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # pytest usa --import-mode=importlib
from cases import build_buml_project, load_result  # noqa: E402

RESULT = load_result("hospital")
STRUCTURES = RESULT["structures"]


def values(cls, attribute):
    """Valores que toma un atributo de una clase en todas las estructuras."""
    return [a["value"] for s in STRUCTURES for o in s["objects"] if o["class"] == cls
            for a in o["attributes"] if a["name"] == attribute]


def test_beapi_genera_10_estructuras_con_raiz_doctor():
    assert RESULT["rootClass"] == "Doctor"
    assert RESULT["structureCount"] == 10 == len(STRUCTURES)


def test_la_raiz_de_cada_estructura_es_un_doctor():
    for s in STRUCTURES:
        root = next(o for o in s["objects"] if o["id"] == s["root"])
        assert root["class"] == "Doctor"


def test_solo_aparecen_clases_y_asociaciones_del_modelo():
    classes = {o["class"] for s in STRUCTURES for o in s["objects"]}
    associations = {l["association"] for s in STRUCTURES for l in s["links"]}
    assert classes == {"Doctor", "Patient", "MedicalAppointment", "MedicalRecord"}
    assert associations == {"DoctorAppointments", "Patient_Doctor", "PatientAppointments", "AppointmentRecord"}


def test_los_atributos_heredados_de_person_se_exportan():
    assert set(values("Doctor", "fullName")) == {"a"}
    assert set(values("Patient", "fullName")) == {"a"}


def test_los_enums_usan_los_literales_de_beapi_json():
    assert {v["literal"] for v in values("Patient", "bloodGroup")} == {"AB_POSITIVE"}
    assert {v["literal"] for v in values("MedicalAppointment", "status")} == {"SCHEDULED"}


def test_besser_importa_cada_diagrama_de_objetos(tmp_path):
    model, [(_, diagrams)] = build_buml_project("hospital", RESULT, tmp_path)
    assert len(diagrams) == 10
    domain = process_class_diagram(model["class_diagram"])
    for s, diagram in zip(STRUCTURES, diagrams):
        objects = process_object_diagram(diagram, domain)
        assert len(objects.objects) == len(s["objects"])
        assert len(objects.links) == len(s["links"])
