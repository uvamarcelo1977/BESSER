#!/usr/bin/env python
"""Script para ejecutar todos los tests del proyecto BESSER.

Si el script no se invoca con el intérprete del venv de este proyecto
(venv/ en la raiz), se re-ejecuta automaticamente con ese venv para
garantizar que esten disponibles todas las dependencias.

La deteccion se basa en sys.prefix (no en la resolucion de symlinks), porque
los venv de Python suelen ser symlinks al python del sistema y uno no debe
confundirlos con "estar dentro del venv correcto".
"""

import os
import subprocess
import sys


def project_root():
    return os.path.dirname(os.path.abspath(__file__))


def venv_python():
    root = project_root()
    for name in ("venv", ".venv"):
        base = os.path.join(root, name)
        for python_name in ("python", "python3"):
            path = os.path.join(base, "bin", python_name)
            if os.path.exists(path):
                return path
    return None


def using_project_venv():
    venv_py = venv_python()
    if venv_py is None:
        return False
    venv_root = os.path.dirname(os.path.dirname(venv_py))
    return os.path.abspath(sys.prefix) == os.path.abspath(venv_root)


def main():
    if not using_project_venv():
        venv_py = venv_python()
        if venv_py is not None:
            print(f"Re-ejecutando con el venv del proyecto: {venv_py}")
            os.execv(venv_py, [venv_py, os.path.abspath(__file__)] + sys.argv[1:])

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "--ignore=tests/generators/nn",
        "--ignore=tests/utilities/web_modeling_editor/backend/test_spreadsheet_import.py",
        "-v",
    ]

    # Pass extra arguments to pytest (e.g. -k pattern, --tb short, etc.)
    cmd.extend(sys.argv[1:])

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
