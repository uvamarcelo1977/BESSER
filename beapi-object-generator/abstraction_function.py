#!/usr/bin/env python3
"""Función de abstracción de un diagrama de clases B-UML, como archivo JSON externo.

Registra la información que antes el generador Java escribía como anotaciones
(@BClass, @BAttribute, @BAssociationEnd, @BEnumeration, @BLiteral) y, para cada
elemento, cómo se realiza en Java (un bloque "java"). El generador Java ya no
escribe anotaciones: este JSON las reemplaza. Otros lenguajes pueden añadirse
como bloques hermanos ("python": {...}) sin cambiar la parte del modelo.

Uso (desde la raíz del repositorio BESSER):
    PYTHONPATH=. python beapi-object-generator/abstraction_function.py MODEL [-o OUT.json]

MODEL es un archivo Python B-UML (define un DomainModel) o un JSON de
proyecto/diagrama de clases exportado por el editor web de BESSER. Sin -o, el JSON
se escribe en la salida estandar (beapi_gen.py lo escribe en output/<modelo>/).

Los nombres Java replican besser/generators/java_classes/templates/java_template.py.j2:
si cambia la plantilla, hay que cambiar esto también.

Sobre el no determinismo (verificado con la plantilla actual, 2026-11-10):

* La versión anterior de este archivo advertía que, en las asociaciones 1..1 y
  *..*, la clase que contenía el campo podía cambiar de una ejecución a otra.
  Eso pasaba con la plantilla de la rama generator_with_abstract_function_out,
  que realizaba cada asociación una sola vez, en la primera clase que la
  procesaba (y cuyo orden podía variar). La plantilla actual ya no lo hace:
  cada clase realiza su propio extremo opuesto si es navegable (asociaciones
  bidireccionales) y solo las autoasociaciones se procesan una única vez.
  Qué clase tiene qué campo y con qué nombre depende ahora solo del modelo,
  así que el bloque "java" de cada extremo es determinista y se puede calcular
  en un proceso distinto del que generó el código.

* Sigue habiendo un no determinismo de ORDEN. Class.attributes, Class.associations,
  Association.ends y Enumeration.literals son set de objetos sin __hash__ propio
  (hash por identidad, es decir, por dirección de memoria), y la plantilla los
  recorre tal cual. Entre ejecuciones cambian el orden de los campos, de los
  getters/setters y, sobre todo, de los PARÁMETROS DEL CONSTRUCTOR. Por ejemplo,
  NodeCachingLinkedList(int maximumCacheSize, int modCount, ...) en una ejecución
  y NodeCachingLinkedList(int DEFAULT_MAXIMUM_CACHE_SIZE, ...) en otra. Al
  generar cinco veces los modelos school, hospital, genealogy y nodecachinglist,
  el texto de los .java cambió, pero el conjunto de campos y de firmas de cada
  clase fue siempre el mismo.
  Por eso este JSON NO registra el orden de los parámetros del constructor: quien
  lo necesite (p.ej. los builders de BEAPI) debe leerlo del .java o del .class
  compilado, no deducirlo del modelo. Los elementos de este JSON se emiten
  ordenados por nombre, así que el archivo es estable entre ejecuciones.
"""
import argparse
import json
import runpy
import sys
import uuid
from operator import attrgetter

from besser.BUML.metamodel.structural import (
    BinaryAssociation, DomainModel, UNLIMITED_MAX_MULTIPLICITY,
)

NAME = attrgetter("name")   # orden de salida: por nombre, estable entre ejecuciones

# Mismo namespace que usaban las anotaciones (java_trace.py en la rama
# generator_with_abstract_function_out): los ids coinciden con los de las clases
# Java anotadas de beapi-object-generator/examples/.
_BESSER_TRACE_NS = uuid.UUID("f6f9040e-d104-4385-9f1d-a9d6ed54466a")

# tipo primitivo B-UML -> tipo Java (igual que java_fields.py.j2)
JAVA_TYPES = {"str": "String", "text": "String", "int": "int", "float": "float", "bool": "boolean",
              "date": "LocalDate", "datetime": "LocalDateTime", "time": "LocalTime", "uuid": "UUID"}


def element_id(model: DomainModel, kind: str, qualified_name: str) -> str:
    """Id estable de un elemento del modelo.

    B-UML no tiene identificadores persistentes, así que el id se deriva del
    nombre calificado: no cambia entre regeneraciones, pero sí si se renombra el elemento.
    """
    return str(uuid.uuid5(_BESSER_TRACE_NS, f"{model.name}/{kind}/{qualified_name}"))


def upper_first(name: str) -> str:
    """Como la plantilla: name[0]|upper ~ name[1:] (no str.capitalize, que pasa el resto a minúsculas)."""
    return name[:1].upper() + name[1:]


def class_diagram_json(data: dict) -> dict:
    """Diagrama de clases de un JSON del editor web: si es un proyecto, su diagrama de clases activo
    (currentDiagramIndices); si no, el propio diagrama."""
    if "project" not in data:
        return data
    project = data["project"]
    diagrams = project["diagrams"].get("ClassDiagram")
    if not diagrams:
        raise ValueError("el proyecto no tiene diagramas de clases")
    if isinstance(diagrams, list):
        index = (project.get("currentDiagramIndices") or {}).get("ClassDiagram", 0)
        diagrams = diagrams[index if 0 <= index < len(diagrams) else 0]
    return diagrams


def domain_model_from_json(class_diagram: dict) -> DomainModel:
    """DomainModel de un diagrama de clases del editor web (conversor JSON -> B-UML de BESSER)."""
    from besser.utilities.web_modeling_editor.backend.services.converters.json_to_buml.class_diagram_processor \
        import process_class_diagram
    return process_class_diagram(class_diagram)


def load_model(path: str) -> DomainModel:
    if path.endswith(".py"):
        found = [v for v in runpy.run_path(path).values() if isinstance(v, DomainModel)]
        if not found:
            raise SystemExit(f"{path} defines no DomainModel")
        return found[0]
    with open(path, encoding="utf-8") as f:
        return domain_model_from_json(class_diagram_json(json.load(f)))


def abstraction_function(model: DomainModel) -> dict:
    def eid(kind, qualified_name):
        return element_id(model, kind, qualified_name)

    java_ends = realized_java_ends(model)

    def multiplicity(prop):
        upper = prop.multiplicity.max
        return {"lower": prop.multiplicity.min, "upper": "*" if upper >= UNLIMITED_MAX_MULTIPLICITY else upper}

    enumerations = [{
        "id": eid("enumeration", e.name),
        "name": e.name,
        "java": {"type": e.name},
        "literals": [{"id": eid("literal", f"{e.name}::{lit.name}"), "name": lit.name,
                      "java": {"constant": lit.name}} for lit in sorted(e.literals, key=NAME)],
    } for e in sorted(model.get_enumerations(), key=NAME)]

    classes = [{
        "id": eid("class", c.name),
        "name": c.name,
        "isAbstract": c.is_abstract,
        "parents": sorted(p.name for p in c.parents()),
        "java": {"type": c.name},
        "attributes": [{
            "id": eid("attribute", f"{c.name}::{a.name}"),
            "name": a.name,
            "type": a.type.name,
            **multiplicity(a),
            "isId": a.is_id,
            "readOnly": a.is_read_only,
            "derived": a.is_derived,
            "java": {"field": a.name, "type": JAVA_TYPES.get(a.type.name, a.type.name),
                     "get": "get" + upper_first(a.name), "set": "set" + upper_first(a.name)},
        } for a in sorted(c.attributes, key=NAME)],
    } for c in sorted(model.get_classes(), key=NAME)]

    associations = []
    for assoc in sorted(model.associations, key=NAME):
        ends = []
        for end in sorted(assoc.ends, key=NAME):
            others = [e for e in assoc.ends if e is not end]
            ends.append({
                "id": eid("association_end", f"{assoc.name}::{end.name}"),
                "name": end.name,
                "type": end.type.name,
                **multiplicity(end),
                "opposite": others[0].name if len(others) == 1 else None,
                "composite": end.is_composite,
                "navigable": end.is_navigable,
                "java": java_ends.get((assoc.name, end.name)),   # None: ninguna clase Java contiene este extremo
            })
        associations.append({"id": eid("association", assoc.name), "name": assoc.name, "ends": ends})

    return {"format": "besser-abstraction-function/1.0",
            "model": {"id": eid("model", model.name), "name": model.name},
            "enumerations": enumerations, "classes": classes, "associations": associations}


def realized_java_ends(model: DomainModel) -> dict:
    """{(asociación, extremo): bloque java} para los extremos que la plantilla Java convierte en campo.

    Mismas reglas que java_template.py.j2:
    * autoasociación (ambos extremos del mismo tipo): se procesa una vez; cada extremo
      navegable es un campo con el nombre del rol; si es múltiple, el método para agregar es addTo<Rol>.
    * asociación entre clases distintas: cada clase realiza el extremo opuesto si es navegable,
      con el nombre del rol; si es múltiple, el método para agregar es add<TipoOpuesto>.
    Ninguna regla depende del orden en que se recorren las clases (ver docstring del módulo)."""
    realized, processed_self = {}, set()
    for cls in model.classes_sorted_by_inheritance():
        for assoc in cls.associations:
            if not isinstance(assoc, BinaryAssociation):
                continue
            first, second = list(assoc.ends)
            if first.type.name == second.type.name:   # autoasociación
                if assoc.name in processed_self:
                    continue
                processed_self.add(assoc.name)
                for end in (first, second):
                    if end.is_navigable:
                        realized[(assoc.name, end.name)] = java_end(
                            cls, end, end.multiplicity.max > 1, "addTo" + upper_first(end.name))
                continue
            far = second if first.type.name == cls.name else first
            if far.is_navigable:
                realized[(assoc.name, far.name)] = java_end(
                    cls, far, far.multiplicity.max > 1, "add" + far.type.name)
    return realized


def java_end(owner, end, many, adder) -> dict:
    accessors = {"get": "get" + upper_first(end.name)}
    accessors.update({"add": adder} if many else {"set": "set" + upper_first(end.name)})
    return {"owner": owner.name, "field": end.name,
            "type": f"List<{end.type.name}>" if many else end.type.name, **accessors}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("model", help="B-UML .py file or web editor .json (project or class diagram)")
    parser.add_argument("-o", "--output", help="output JSON (default: standard output)")
    args = parser.parse_args()
    text = json.dumps(abstraction_function(load_model(args.model)), indent=2, ensure_ascii=False) + "\n"
    if not args.output:
        sys.stdout.write(text)
        return
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"abstraction function -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
