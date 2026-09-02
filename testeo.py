#!/usr/bin/env python
"""Ejecuta todos los tests del proyecto BESSER por directorio y reporta resultados."""

import os
import subprocess
import sys

TESTS_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")

IGNORED = [
    "--ignore", "tests/generators/nn",
    "--ignore", "tests/utilities/web_modeling_editor/backend/test_spreadsheet_import.py",
]


def discover_test_dirs():
    dirs = []
    for entry in sorted(os.listdir(TESTS_ROOT)):
        full = os.path.join(TESTS_ROOT, entry)
        if os.path.isdir(full) and entry != "__pycache__":
            dirs.append(full)
    return dirs


def main():
    dirs = discover_test_dirs()
    passed, failed = [], []

    print(f"\n{'='*60}")
    print(f"  BESSER Test Runner - {len(dirs)} directorios")
    print(f"{'='*60}\n")

    for d in dirs:
        name = os.path.relpath(d, os.path.dirname(TESTS_ROOT))
        print(f"\n{'─'*60}")
        print(f"▶ {name}")
        print(f"{'─'*60}")

        result = subprocess.run(
            [sys.executable, "-m", "pytest", name, "-v", "--tb=short"] + IGNORED,
        )
        if result.returncode == 0:
            passed.append(name)
        else:
            failed.append(name)

    print(f"\n{'='*60}")
    print(f"  RESUMEN: {len(passed)} OK / {len(failed)} FAIL / {len(dirs)} total")
    print(f"{'='*60}")

    if failed:
        print("\nDirectorios con errores:")
        for name in failed:
            print(f"  ✗ {name}")
        sys.exit(1)
    else:
        print("\nTodos los tests pasaron ✓")


if __name__ == "__main__":
    main()
