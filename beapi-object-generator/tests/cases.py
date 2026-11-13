"""Ayudas comunes de los tests de los casos de estudio (se importa como modulo: el repo usa --import-mode=importlib).

Los tests leen output/<caso>/<caso>.json, que se genera con
    ../venv/bin/python beapi_gen.py examples/<caso>/<caso>.json
Si ese archivo no existe, los tests del caso se saltean.
"""
import argparse
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import beapi_gen  # noqa: E402


def load_result(case):
    """Contenido de output/<caso>/<caso>.json (pytest.skip si no se genero)."""
    path = os.path.join(ROOT, "output", case, case + ".json")
    if not os.path.exists(path):
        pytest.skip("falta %s: ejecutar beapi_gen.py examples/%s/%s.json" % (os.path.relpath(path, ROOT), case, case),
                    allow_module_level=True)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_buml_project(case, result, tmp_path):
    """Ejecuta el paso --buml en tmp_path y devuelve (modelo, [(archivo, diagramas de objetos)])."""
    args = argparse.Namespace(model=os.path.join(ROOT, "examples", case, case + ".json"), java_dir=None,
                              output_dir=str(tmp_path), buml_structures=None, buml_split=False)
    model = beapi_gen.load_model(args)
    args.output_dir = model["output_dir"]
    return model, beapi_gen.write_buml_projects(case, result, model, args)
