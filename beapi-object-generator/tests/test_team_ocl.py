"""Tests del caso de estudio team_ocl (examples/team_ocl): conformidad OCL en el mismo proceso."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # pytest usa --import-mode=importlib
from cases import beapi_gen, build_buml_project, load_result  # noqa: E402

RESULT = load_result("team_ocl")


def test_beapi_genera_30_estructuras_con_raiz_team():
    assert RESULT["rootClass"] == "Team"
    assert RESULT["structureCount"] == 30


def test_conformidad_6_de_30(tmp_path):
    model, projects = build_buml_project("team_ocl", RESULT, tmp_path)
    [(report, outcome)] = beapi_gen.check_conformance("team_ocl", projects, model["class_diagram"])
    assert outcome["states"] == {"CUMPLE": 6, "NO CUMPLE": 24, "INDETERMINADO": 0}
    assert outcome["violations"] == {"AdultPlayer": 22, "TeamNotOverCapacity": 12}
    assert outcome["exit_code"] == 1
    with open(report, encoding="utf-8") as f:
        assert "Resumen: 6/30 cumplen, 24 no cumplen" in f.read()
