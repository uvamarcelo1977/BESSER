"""Valida con B-OCL los invariantes del modelo BESSER sobre cada diagrama de objetos.

Uso: python3 validar_bocl.py ARCHIVO.json [-c TITULO_DIAGRAMA_DE_CLASES]
"""
import argparse
import json
import re
import sys

from besser.utilities.web_modeling_editor.backend.services.converters import (
    process_class_diagram, process_object_diagram)
from bocl.OCLWrapper import OCLWrapper

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("archivo", help="proyecto BESSER (.json) a verificar")
ap.add_argument("-c", "--class-diagram", default=None,
                help="titulo del diagrama de clases (opcional; por defecto se detecta "
                     "el del propio JSON)")
args = ap.parse_args()

project = json.load(open(args.archivo))["project"]
diagrams = project["diagrams"]
print(f"Archivo: {args.archivo}")
print(f"Proyecto: {project.get('name')}")

class_diagrams = diagrams.get("ClassDiagram", [])
titulos = [d["title"] for d in class_diagrams]
if not class_diagrams:
    sys.exit("El JSON no contiene ningun diagrama de clases")
if args.class_diagram:
    class_diagram = next((d for d in class_diagrams if d["title"] == args.class_diagram), None)
    if class_diagram is None:
        sys.exit(f"No hay diagrama de clases '{args.class_diagram}'. Disponibles: {titulos}")
else:
    # el diagrama activo del proyecto, o el primero con restricciones OCL
    idx = project.get("currentDiagramIndices", {}).get("ClassDiagram", 0)
    class_diagram = class_diagrams[idx] if idx < len(class_diagrams) else class_diagrams[0]
    if len(class_diagrams) > 1:
        print(f"Aviso: hay {len(class_diagrams)} diagramas de clases {titulos}; "
              f"se usa '{class_diagram['title']}' (cambiar con -c)")
domain = process_class_diagram(class_diagram)
print(f"Modelo de dominio: {domain.name} (diagrama de clases: '{class_diagram['title']}')")

# Solo invariantes: las pre/post de metodos no se evaluan sobre objetos.
constraints = sorted((c for c in domain.constraints if re.search(r"\binv\b", c.expression)),
                     key=lambda c: c.name or "")
print(f"Invariantes a evaluar: {len(constraints)}")
for c in constraints:
    print(f"  - {c.name}: {c.expression}")

modelos_con_falla = 0
for od in diagrams["ObjectDiagram"]:
    od = dict(od)
    od["model"] = dict(od["model"], referenceDiagramData=class_diagram["model"])
    om = process_object_diagram(od, domain)
    objetos = ", ".join(f"{o.name}:{o.classifier.name}" for o in om.objects)
    print(f"\n=== Modelo de objetos: {om.name} ===")
    print(f"Objetos: {objetos}")

    wrapper = OCLWrapper(domain, om)
    fallas = 0
    for c in constraints:
        print(f"  Evaluando [{c.name}] {c.expression}")
        if not any(o.classifier.name == c.context.name for o in om.objects):
            # sin instancias del contexto el evaluador devuelve False
            print(f"    -> OMITIDA (no hay instancias de {c.context.name})")
            continue
        try:
            ok = bool(wrapper.evaluate(c))
            print(f"    -> {'OK' if ok else 'FALLA'}")
        except Exception as e:
            ok = False
            print(f"    -> ERROR {type(e).__name__}: {e}")
        fallas += not ok
    modelos_con_falla += bool(fallas)
    print(f"Resultado {om.name}: {'OK' if not fallas else f'{fallas} restriccion(es) violada(s)'}")

total = len(diagrams["ObjectDiagram"])
print(f"\nResumen: {total - modelos_con_falla}/{total} modelos de objetos cumplen todas las restricciones")
sys.exit(1 if modelos_con_falla else 0)
