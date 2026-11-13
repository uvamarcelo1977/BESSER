"""Valida con B-OCL los invariantes del modelo BESSER sobre cada diagrama de objetos.

Uso: python3 eval_bocl_interpreter.py ARCHIVO.json [-c TITULO_DIAGRAMA_DE_CLASES] [-p PREFIJO_TITULO]

Para cada diagrama de objetos evalua cada invariante (inv) del diagrama de clases. El resultado de un
invariante es:
  OK        se cumple;
  FALLA     el evaluador devolvio falso: el diagrama de objetos VIOLA el invariante;
  ERROR     el evaluador no pudo evaluarlo (expresion que B-OCL no soporta, error interno...): no se
            sabe si el diagrama lo cumple, y NO se cuenta como violacion;
  OMITIDA   no hay instancias de la clase de contexto: se cumple trivialmente.
Y el de cada diagrama de objetos:
  CUMPLE          todos los invariantes OK u OMITIDA;
  NO CUMPLE       al menos una FALLA;
  INDETERMINADO   ninguna FALLA, pero al menos un ERROR.

Con -p solo se evaluan los diagramas de objetos cuyo titulo empieza con el prefijo.

beapi_gen.py --conformance no ejecuta este script: importa evaluate() y la llama en el mismo proceso.

Codigo de salida: 0 todos CUMPLEN; 1 alguno NO CUMPLE; 3 ninguno NO CUMPLE pero hay INDETERMINADOS;
2 error de uso (archivo sin diagramas de clases, diagrama inexistente, ningun diagrama de objetos...).
"""
import argparse
import json
import re
import sys

from besser.utilities.web_modeling_editor.backend.services.converters import (
    process_class_diagram, process_object_diagram)
from bocl.OCLWrapper import OCLWrapper

CUMPLE, NO_CUMPLE, INDETERMINADO = "CUMPLE", "NO CUMPLE", "INDETERMINADO"
SUMMARY_HEADER = "=== Resumen ==="


def evaluate(class_diagram, object_diagrams, emit=print):
    """Evalua los invariantes de class_diagram (diagrama de clases del editor) sobre cada uno de
    object_diagrams (diagramas de objetos del editor). Escribe el informe linea por linea con emit,
    terminando con el bloque SUMMARY_HEADER, y devuelve un dict con:
      states      {CUMPLE|NO_CUMPLE|INDETERMINADO: cantidad de diagramas}
      violations  {invariante: cantidad de diagramas que lo violan}
      errors      {invariante: [cantidad de diagramas, primer mensaje de error]}
      exit_code   0 todos cumplen, 1 alguno no cumple, 3 ninguno no cumple pero hay indeterminados
    """
    domain = process_class_diagram(class_diagram)
    emit(f"Modelo de dominio: {domain.name} (diagrama de clases: '{class_diagram.get('title')}')")

    # Solo invariantes: las pre/post de metodos no se evaluan sobre objetos.
    constraints = sorted((c for c in domain.constraints if re.search(r"\binv\b", c.expression)),
                         key=lambda c: c.name or "")
    emit(f"Invariantes a evaluar: {len(constraints)}")
    for c in constraints:
        emit(f"  - {c.name}: {c.expression}")

    states = {CUMPLE: 0, NO_CUMPLE: 0, INDETERMINADO: 0}
    violations, errors = {}, {}
    for od in object_diagrams:
        od = dict(od)
        od["model"] = dict(od["model"], referenceDiagramData=class_diagram["model"])
        om = process_object_diagram(od, domain)
        emit(f"\n=== Modelo de objetos: {om.name} ===")
        emit("Objetos: " + ", ".join(f"{o.name}:{o.classifier.name}" for o in om.objects))

        wrapper = OCLWrapper(domain, om)
        failed = errs = 0
        for c in constraints:
            emit(f"  Evaluando [{c.name}] {c.expression}")
            if not any(o.classifier.name == c.context.name for o in om.objects):
                # sin instancias del contexto el evaluador devuelve False
                emit(f"    -> OMITIDA (no hay instancias de {c.context.name})")
                continue
            try:
                ok = bool(wrapper.evaluate(c))
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                emit(f"    -> ERROR {msg}")
                errs += 1
                errors.setdefault(c.name, [0, msg])[0] += 1
                continue
            emit(f"    -> {'OK' if ok else 'FALLA'}")
            if not ok:
                failed += 1
                violations[c.name] = violations.get(c.name, 0) + 1
        state = NO_CUMPLE if failed else INDETERMINADO if errs else CUMPLE
        states[state] += 1
        detail = ", ".join(p for p in (f"{failed} violada(s)" if failed else "",
                                       f"{errs} no evaluable(s)" if errs else "") if p)
        emit(f"Resultado {om.name}: {state}" + (f" ({detail})" if detail else ""))

    total = len(object_diagrams)
    emit("\n" + SUMMARY_HEADER)
    if violations:
        emit("Invariantes violados (FALLA):")
        for name, n in sorted(violations.items()):
            emit(f"  - {name}: en {n}/{total} diagrama(s)")
    if errors:
        emit("Invariantes que el evaluador no pudo evaluar (ERROR; no cuentan como violacion):")
        for name, (n, msg) in sorted(errors.items()):
            emit(f"  - {name}: en {n}/{total} diagrama(s); {msg}")
    emit(f"Resumen: {states[CUMPLE]}/{total} cumplen, {states[NO_CUMPLE]} no cumplen, "
         f"{states[INDETERMINADO]} indeterminados (invariantes no evaluables)")
    exit_code = 1 if states[NO_CUMPLE] else 3 if states[INDETERMINADO] else 0
    return {"states": states, "violations": violations, "errors": errors, "exit_code": exit_code}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("archivo", help="proyecto BESSER (.json) a verificar")
    ap.add_argument("-c", "--class-diagram", default=None,
                    help="titulo del diagrama de clases (opcional; por defecto el diagrama activo del proyecto)")
    ap.add_argument("-p", "--title-prefix", default=None,
                    help="evaluar solo los diagramas de objetos cuyo titulo empieza con este prefijo "
                         "(por defecto, todos)")
    args = ap.parse_args(argv)

    def usage_error(msg):
        print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    with open(args.archivo, encoding="utf-8") as f:
        project = json.load(f)["project"]
    diagrams = project["diagrams"]
    print(f"Archivo: {args.archivo}")
    print(f"Proyecto: {project.get('name')}")

    class_diagrams = diagrams.get("ClassDiagram", [])
    titles = [d["title"] for d in class_diagrams]
    if not class_diagrams:
        return usage_error("El JSON no contiene ningun diagrama de clases")
    if args.class_diagram:
        class_diagram = next((d for d in class_diagrams if d["title"] == args.class_diagram), None)
        if class_diagram is None:
            return usage_error(f"No hay diagrama de clases '{args.class_diagram}'. Disponibles: {titles}")
    else:
        idx = project.get("currentDiagramIndices", {}).get("ClassDiagram", 0)
        class_diagram = class_diagrams[idx] if idx < len(class_diagrams) else class_diagrams[0]
        if len(class_diagrams) > 1:
            print(f"Aviso: hay {len(class_diagrams)} diagramas de clases {titles}; "
                  f"se usa '{class_diagram['title']}' (cambiar con -c)")

    object_diagrams = diagrams.get("ObjectDiagram", [])
    selected = [od for od in object_diagrams
                if args.title_prefix is None or od.get("title", "").startswith(args.title_prefix)]
    if args.title_prefix is not None:
        print(f"Diagramas de objetos con titulo '{args.title_prefix}...': {len(selected)} "
              f"(se omiten {len(object_diagrams) - len(selected)})")
    if not selected:
        return usage_error("No hay diagramas de objetos para evaluar")
    return evaluate(class_diagram, selected)["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
