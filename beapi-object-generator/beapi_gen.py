#!/usr/bin/env python3
"""Generacion bounded-exhaustive de objetos con BEAPI a partir de un modelo B-UML y sus clases Java.

Entrada: un modelo B-UML (proyecto exportado del editor web de BESSER, examples/<nombre>/<nombre>.json)
y las clases Java que lo implementan, SIN anotaciones (examples/<nombre>/java/). La relacion entre el
modelo y el codigo es la funcion de abstraccion que calcula abstraction_function.py.

Pasos (todos los resultados quedan en output/<nombre>/, los intermedios en work/<nombre>/):
  0. abstraction_function.py escribe <nombre>.abstraction.json a partir del diagrama de clases activo;
  1. copia las clases Java a work/<nombre>/src (el ejemplo original no se modifica) y las prepara:
     agrega Serializable + serialVersionUID y constructores auxiliares que reciben las fechas
     LocalDate como int (BEAPI descarta los objetos que contienen LocalDate);
  2. genera la configuracion de BEAPI: builders (constructores y los add/set de cada extremo de
     asociacion de la abstraccion), literales y canonicalizador (omit.fields con los campos LocalDate);
  3. compila con Java 8 y verifica que las clases tengan todo lo que nombra la abstraccion;
  4. ejecuta BEAPI (randoop.main.Main gentests) con --all-sequences=true y serializa los
     objetos de la clase raiz en work/<nombre>/objects.ser;
  5. tools/BAbstractionDump.java recorre cada objeto con los getters de la abstraccion y escribe
     <nombre>.json con objetos, attribute links y links;
  6. (opcional, --buml) agrega las estructuras como diagramas de objetos a una copia del modelo;
  7. (opcional, --conformance) evalua los invariantes OCL del modelo sobre esos diagramas de
     objetos (eval_bocl_interpreter.evaluate) y escribe el informe en <nombre>_buml_conformance.txt.

Organizacion del archivo (de arriba hacia abajo):
  - constantes;
  - programa principal: main(), load_model() y generate(), que siguen los pasos de arriba;
  - cada paso: write_abstraction() (0), prepare() (1-2), run_beapi() (4), write_buml_projects() (6)
    y check_conformance() (7);
  - utilidades generales (linea de comandos, configuracion, Java, archivos).

Necesita BESSER y B-OCL: ejecutar con el entorno virtual de BESSER (../venv/bin/python). Ver README.md.
"""
import argparse,datetime,glob,json,os,re,shutil,subprocess,sys,time,types,uuid

HERE = os.path.dirname(os.path.abspath(__file__))
BEAPI_JAR = os.path.join(HERE, "libs", "beapi.jar")
DUMP_SRC = os.path.join(HERE, "tools", "BAbstractionDump.java")   # verifica las clases y exporta objects.ser
BEAPI_DIAGRAM_TITLE = "BEAPI structure %s"                       # titulo de los diagramas de objetos agregados
JAVA_DIR = "java"                                                # clases Java: <carpeta del modelo>/java
CONFIG_NAME = "beapi.json"                                       # configuracion opcional, junto al modelo

# tipo Java -> (clase de literales de BEAPI, valores por defecto, formato de un valor en literals.txt)
LITERAL_TYPES = {
    "int": ("java.lang.Integer", [1], lambda v: "int:%d" % int(v)),
    "long": ("java.lang.Long", [1], lambda v: "long:%d" % int(v)),
    "float": ("java.lang.Float", [1.0], lambda v: "float:%s" % float(v)),
    "double": ("java.lang.Double", [1.0], lambda v: "double:%s" % float(v)),
    "boolean": ("java.lang.Boolean", [True], lambda v: "boolean:%s" % str(v).lower()),
    "String": ("java.lang.String", ["a", "b"], lambda v: 'String:"%s"' % str(v).replace('"', '\\"')),
}
DATE_TYPES = {"LocalDate", "java.time.LocalDate"}
# declaracion del tipo principal de un .java: (modificadores, class|enum, nombre)
TYPE_DECLARATION = r"(?:^|\n)\s*public\s+((?:abstract\s+|final\s+)*)(class|enum)\s+(\w+)"
# claves validas de beapi.json y sus valores por defecto
DEFAULTS = {
    "scope": 3,                 # max. objetos por clase (canonicalizador) y base de los limites de BEAPI
    "root_class": None,         # clase serializada; None = la que alcanza mas clases por asociaciones
    "literals": {},             # tipo Java -> lista de valores (reemplaza los de LITERAL_TYPES)
    "enum_literals": 2,         # cuantos literales de cada enum, o {enum: [literales]}
    "builders": None,           # lista de builders que reemplaza a la deducida de la abstraccion
    "extra_builders": [],       # builders que se agregan a la lista
    "exclude_builders": [],     # regex: se quitan los builders que coinciden
    "timelimit": 36000,
    "max_heap": "4g",
    "max_structures": None,     # exportar como maximo N estructuras al JSON
}

# proyecto del editor web de BESSER
BUML_CLASS_TYPES = ("Class", "AbstractClass")
BUML_ASSOC_TYPES = ("ClassBidirectional", "ClassUnidirectional", "ClassComposition", "ClassAggregation")
# geometria de los diagramas de objetos (la misma que usa el editor web)
OBJ_WIDTH, OBJ_HEADER, ATTR_HEIGHT, COL_GAP, ROW_GAP = 240, 40, 25, 160, 40


class GenError(Exception):
    """Error esperable (configuracion, compilacion, BEAPI...): se informa sin traceback."""


_BESSER = None


def besser():
    """Modulos que necesitan BESSER (y B-OCL): abstraction_function y eval_bocl_interpreter.
    Se importan una sola vez; usa el BESSER del repositorio aunque no este instalado (como PYTHONPATH=..)."""
    global _BESSER
    if _BESSER is None:
        repo = os.path.dirname(HERE)
        if repo not in sys.path:
            sys.path.insert(1, repo)
        try:
            import abstraction_function
            import eval_bocl_interpreter
        except ImportError as e:
            raise GenError("hace falta BESSER y B-OCL (%s): ejecutar con el entorno virtual de BESSER, "
                           "p.ej. ../venv/bin/python beapi_gen.py ..." % e)
        _BESSER = types.SimpleNamespace(af=abstraction_function, ev=eval_bocl_interpreter)
    return _BESSER


# =========================================================================== programa principal

def main():
    sys.stdout.reconfigure(line_buffering=True)   # que el progreso se vea mientras corre BEAPI
    args = parse_args()
    try:
        model = load_model(args)
        name, out_dir = model["name"], model["output_dir"]
        args.output_dir = out_dir
        abstraction = write_abstraction(model, os.path.join(out_dir, name + ".abstraction.json"))
        print("[%s] funcion de abstraccion: %s (diagrama de clases '%s') -> %s"
              % (name, os.path.relpath(model["path"]), model["class_diagram"].get("title"),
                 os.path.relpath(abstraction["path"])))
        out = os.path.join(out_dir, name + ".json")
        if args.reuse_json:
            if not os.path.exists(out):
                raise GenError("no existe %s para reutilizar (correr primero sin --reuse-json)" % os.path.relpath(out))
            with open(out, encoding="utf-8") as f:
                result = json.load(f)
            print("[%s] reutilizando %s (%d estructuras)" % (name, os.path.relpath(out), len(result["structures"])))
        else:
            if not os.path.exists(BEAPI_JAR):
                raise GenError("falta %s" % BEAPI_JAR)
            java_home = find_java8(args.java_home)
            print("> Java 8: %s" % java_home)
            result = generate(model, java_home, args, out, abstraction)
        if args.buml:
            print("[%s] agregando los diagramas de objetos al proyecto BESSER" % name)
            projects = write_buml_projects(name, result, model, args)
            if args.conformance:
                print("[%s] verificando los invariantes OCL del modelo sobre los diagramas de objetos" % name)
                check_conformance(name, projects, model["class_diagram"])
    except GenError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1
    return 0


def load_model(args):
    """El modelo B-UML de la linea de comandos: proyecto del editor web, su diagrama de clases activo, las
    clases Java (<carpeta del modelo>/java o --java-dir) y la carpeta de salida (output/<nombre>/)."""
    path = os.path.abspath(args.model)
    if not os.path.isfile(path):
        raise GenError("no existe el modelo B-UML %s" % args.model)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        raise GenError("%s no es un JSON valido: %s" % (args.model, e))
    if not isinstance(data.get("project"), dict) or "diagrams" not in data["project"]:
        raise GenError("%s no es un proyecto del editor web de BESSER (falta project.diagrams)" % args.model)
    try:
        class_diagram = besser().af.class_diagram_json(data)
    except ValueError as e:
        raise GenError("%s: %s" % (args.model, e))
    name = os.path.splitext(os.path.basename(path))[0]
    model_dir = os.path.dirname(path)
    java_dir = os.path.abspath(args.java_dir) if args.java_dir else os.path.join(model_dir, JAVA_DIR)
    if not os.path.isdir(java_dir):
        raise GenError("no existe la carpeta de clases Java %s (indicarla con --java-dir)" % java_dir)
    return {"name": name, "path": path, "dir": model_dir, "project": data, "class_diagram": class_diagram,
            "java_dir": java_dir, "output_dir": os.path.join(args.output_dir, name)}


def generate(model, java_home, args, out, abstraction):
    """Pasos 1-5: escribe <out> (output/<nombre>/<nombre>.json) y devuelve su contenido.

    abstraction: {"path", "data"} de write_abstraction()."""
    name = model["name"]
    cfg = load_config(model["dir"], args)
    work = os.path.join(args.work_dir, name)
    os.makedirs(work, exist_ok=True)
    javac, java = os.path.join(java_home, "bin", "javac"), os.path.join(java_home, "bin", "java")
    t0 = time.time()

    print("[%s] 1/4 preparando fuentes y configuracion BEAPI (scope %d)" % (name, cfg["scope"]))
    info = prepare(model["java_dir"], work, cfg, abstraction["data"])
    print("[%s]     raiz: %s ; otras clases: %s" % (name, info["root"]["fq"], ", ".join(info["extra_classes"]) or "-"))
    for b in info["builders"]:
        print("[%s]     builder: %s" % (name, b))
    for w in info["warnings"]:
        print("[%s]     aviso: %s" % (name, w))

    print("[%s] 2/4 compilando con Java 8" % name)
    classes_dir = os.path.join(work, "classes")
    shutil.rmtree(classes_dir, ignore_errors=True)
    os.makedirs(classes_dir)
    sources = sorted(glob.glob(os.path.join(work, "src", "**", "*.java"), recursive=True))
    run([javac, "-g", "-nowarn", "-encoding", "UTF-8", "-source", "1.8", "-target", "1.8", "-d", classes_dir] + sources)

    # el extractor se compila antes de BEAPI para verificar las clases contra la funcion de abstraccion
    # sin esperar la generacion
    dump_dir = os.path.join(work, "dump")
    shutil.rmtree(dump_dir, ignore_errors=True)
    os.makedirs(dump_dir)
    run([javac, "-nowarn", "-encoding", "UTF-8", "-cp", classes_dir, "-d", dump_dir, DUMP_SRC])
    root_fq = info["root"]["fq"]
    dump_cmd = [java, "-Dbesser.package=" + (root_fq.rsplit(".", 1)[0] if "." in root_fq else ""),
                "-cp", dump_dir + os.pathsep + classes_dir, "BAbstractionDump"]
    print("[%s]     verificando las clases Java contra la funcion de abstraccion" % name)
    res = subprocess.run(dump_cmd + ["verify", abstraction["path"]], stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, universal_newlines=True)
    if res.returncode != 0:
        raise GenError("las clases Java de %s no corresponden a la funcion de abstraccion %s:\n%s"
                       % (os.path.relpath(model["java_dir"]), os.path.relpath(abstraction["path"]),
                          res.stdout.rstrip()))

    print("[%s] 3/4 ejecutando BEAPI (log: %s)" % (name, os.path.relpath(os.path.join(work, "beapi.log"))))
    t1 = time.time()
    ser = run_beapi(java, info, cfg, classes_dir, work)
    beapi_seconds = round(time.time() - t1, 2)

    # el extractor deserializa objects.ser y recorre cada objeto con los getters de la abstraccion
    print("[%s] 4/4 exportando objetos a JSON por reflection (funcion de abstraccion)" % name)
    cmd = dump_cmd + ["dump", abstraction["path"], ser]
    if cfg["max_structures"]:
        cmd.append(str(cfg["max_structures"]))
    # numero de estructura (desde 1): es el que se usa en --buml-structures
    structures = [{"index": i, **s} for i, s in enumerate(json.loads(run(cmd)), 1)]

    result = {
        "example": name,
        "generator": "BEAPI",
        "generatedAt": datetime.datetime.now().isoformat(timespec="seconds"),
        "model": structures[0]["model"] if structures else None,
        "rootClass": info["root"]["fq"],
        "scope": cfg["scope"],
        "structureCount": len(structures),
        "abstractionFile": os.path.relpath(abstraction["path"], HERE),
        "javaDir": os.path.relpath(model["java_dir"], HERE),
        "beapi": {
            "seconds": beapi_seconds,
            "testClasses": [info["root"]["fq"]] + info["extra_classes"],
            "builders": info["builders"],
            "literalsFile": os.path.relpath(info["literals_file"], HERE),
            "canonicalizerFile": os.path.relpath(info["canonicalizer_file"], HERE),
            "omittedFields": info["omit_fields"],
            "serializedObjects": os.path.relpath(ser, HERE),
        },
        "structures": structures,
    }
    write_text(out, json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    if args.keep_ser:
        shutil.copy(ser, os.path.join(args.output_dir, name + ".ser"))
    print("[%s] listo: %d estructuras -> %s (%.1f s)" % (name, len(structures), os.path.relpath(out), time.time() - t0))
    return result


# =========================================================================== paso 0: funcion de abstraccion

def write_abstraction(model, out):
    """Escribe en <out> la funcion de abstraccion del diagrama de clases del modelo (abstraction_function.py)
    y devuelve {"path": out, "data": contenido}."""
    af = besser().af
    try:
        data = af.abstraction_function(af.domain_model_from_json(model["class_diagram"]))
    except Exception as e:
        raise GenError("no se pudo convertir el modelo B-UML %s: %s" % (model["path"], e))
    if not data["classes"]:
        raise GenError("el modelo B-UML %s no tiene clases" % model["path"])
    write_text(out, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return {"path": out, "data": data}


# =========================================================================== pasos 1-2: fuentes y configuracion

def prepare(src_root, work, cfg, abstraction):
    """Copia y adapta los fuentes y escribe la configuracion de BEAPI en work/<nombre>/beapi/.

    Los tipos del modelo salen de la funcion de abstraccion (abstraction: contenido del .abstraction.json).
    Devuelve un dict con los tipos del modelo, la clase raiz, los builders y las rutas de los archivos generados.
    """
    # copia solo los .java, manteniendo la estructura de paquetes
    src_dir = os.path.join(work, "src")
    shutil.rmtree(src_dir, ignore_errors=True)
    shutil.copytree(src_root, src_dir,
                    ignore=lambda d, names: [n for n in names
                                             if not n.endswith(".java") and not os.path.isdir(os.path.join(d, n))])
    types = types_from_abstraction(src_dir, abstraction)
    warnings = shadowed_link_methods(types)

    # --- clases: Serializable + builders (constructores y metodos que crean links)
    used = {"int"}   # tipos que necesitan literales; int siempre (fechas de los constructores auxiliares)
    builders = []
    for t in types.values():
        if t["kind"] != "class":
            continue
        # BEAPI serializa los objetos generados: toda clase del modelo debe ser Serializable
        s = t["src"]
        m = re.search(r"(public\s+(?:abstract\s+|final\s+)*class\s+" + t["name"] + r"\b[^{]*?)(\s*)\{", s)
        if not m:
            raise GenError("no se encontro la declaracion de la clase " + t["name"])
        head = m.group(1)
        if "Serializable" not in head:
            head += ", java.io.Serializable" if re.search(r"\bimplements\b", head) else " implements java.io.Serializable"
        uid = "" if "serialVersionUID" in s else "\n    private static final long serialVersionUID = 1L;"
        t["src"] = s[:m.start()] + head + m.group(2) + "{" + uid + s[m.end():]

        # los add/set de los extremos de asociacion (tambien los heredables de una clase abstracta)
        links = [(meth, params) for meth, params, _ in t["link_methods"]]
        if not t["abstract"]:
            for params in add_int_date_constructors(t, types):
                used.update(ty for ty, _ in params if ty in LITERAL_TYPES)
                java_types = ("java.lang.String" if ty == "String" else types[ty]["fq"] if ty in types else ty
                              for ty, _ in params)
                builders.append("%s.<init>\\(%s\\)" % (t["fq"], ",".join(java_types)))
        for meth, params in links:
            builders.append("%s.%s\\(%s\\)" % (t["fq"], meth, ",".join(types[ty]["fq"] for ty in params)))

    # --- enums: cada literal elegido es un builder "paquete.Enum:CONSTANTE"
    enum_cfg = cfg["enum_literals"]
    for t in types.values():
        if t["kind"] != "enum":
            continue
        # en beapi.json los literales van con su nombre B-UML; el orden es el de declaracion en Java
        constant = t["literals"]   # literal B-UML -> constante Java
        declared = enum_constants(t["src"])
        consts = sorted(constant, key=lambda l: declared.index(constant[l]) if constant[l] in declared
                        else len(declared))
        chosen = enum_cfg.get(t["name"], consts[:2]) if isinstance(enum_cfg, dict) else consts[:int(enum_cfg)]
        unknown = set(chosen) - set(consts)
        if unknown:
            raise GenError("literales inexistentes en %s: %s" % (t["name"], ", ".join(sorted(unknown))))
        builders += ["%s:%s" % (t["fq"], constant[c]) for c in chosen]

    for t in types.values():
        write_text(t["path"], t["src"])

    # --- ajustes manuales de beapi.json
    if cfg["builders"] is not None:
        builders = list(cfg["builders"])
    builders += cfg["extra_builders"]
    builders = [b for b in builders if not any(re.search(x, b) for x in cfg["exclude_builders"])]
    if not builders:
        raise GenError("la lista de builders quedo vacia")

    # --- clase raiz: la que BEAPI serializa (las demas se pasan como --testclass adicionales)
    if cfg["root_class"]:
        root_name = cfg["root_class"].split(".")[-1]
        if root_name not in types or types[root_name]["kind"] != "class":
            raise GenError("clase raiz %s no encontrada entre las clases del modelo" % cfg["root_class"])
        root = types[root_name]
    else:
        root = default_root(types)
        if root is None:
            raise GenError("no hay clases concretas en el modelo para usar como raiz")

    # --- archivos de configuracion de BEAPI
    scope = cfg["scope"]
    beapi_dir = os.path.join(work, "beapi")
    builders_file = os.path.join(beapi_dir, "builders.txt")
    write_text(builders_file, "\n".join(builders) + "\n")

    # el canonicalizador ignora los campos LocalDate (si no, BEAPI descarta esos objetos)
    omit = ["modCount"] + sorted({f for t in types.values() for f in t["date_fields"]})
    canon_file = os.path.join(beapi_dir, "canonicalizer.properties")
    write_text(canon_file, "max.objects=%d\nmax.array.objects=%d\nsave.array.null=true\nomit.fields=%s\n"
               % (scope, scope, "|".join(omit)))

    lits = []
    for ty, (cls, default, fmt) in LITERAL_TYPES.items():
        if ty in used or ty in cfg["literals"]:
            values = cfg["literals"].get(ty, default)
            lits.append("START CLASSLITERALS\nCLASSNAME\n%s\nLITERALS\n%s\nEND CLASSLITERALS\n"
                        % (cls, "\n".join(fmt(v) for v in values)))
    literals_file = os.path.join(beapi_dir, "literals.txt")
    write_text(literals_file, "".join(lits))

    return {
        "types": types, "root": root, "builders": builders, "builders_file": builders_file,
        "canonicalizer_file": canon_file, "literals_file": literals_file, "omit_fields": omit,
        "extra_classes": [t["fq"] for t in types.values() if t is not root], "warnings": warnings,
    }


def types_from_abstraction(src_dir, abstraction):
    """Tipos del modelo: salen de la funcion de abstraccion (.abstraction.json); de cada .java solo se usan
    el paquete y el texto.

    Devuelve {tipo Java: info}; las claves son los tipos Java (los que aparecen en las firmas). info tiene
    la ruta y el texto del fuente, el tipo (class/enum), si es abstracta, el nombre calificado, las clases
    destino de sus extremos de asociacion y sus campos LocalDate. Ademas cada clase tiene "parents" y "link_methods" [(metodo, [tipo del parametro], extremo)] con el add o set
    de cada extremo de asociacion que realiza, y cada enum tiene "literals" {literal B-UML: constante}.
    """
    sources = {}   # tipo Java declarado -> (ruta, texto, match de la declaracion)
    for d, _, files in os.walk(src_dir):
        for f in sorted(files):
            if f.endswith(".java"):
                path = os.path.join(d, f)
                s = read_source(path)
                m = re.search(TYPE_DECLARATION, s)
                if m:
                    sources[m.group(3)] = (path, s, m)
    classes = {c["name"]: c for c in abstraction.get("classes", [])}
    java_type = {name: c["java"]["type"] for name, c in classes.items()}

    def entry(element, kind):
        jt = element["java"]["type"]
        if jt not in sources or sources[jt][2].group(2) != kind:
            raise GenError("falta el fuente Java de %s %s (%s %s) en las clases Java"
                           % ("la clase" if kind == "class" else "la enumeracion", element["name"], kind, jt))
        path, s, m = sources[jt]
        pkg = re.search(r"^\s*package\s+([\w.]+)\s*;", s, re.M)
        return {"path": path, "name": jt, "src": s, "kind": kind, "abstract": "abstract" in m.group(1),
                "fq": (pkg.group(1) + "." if pkg else "") + jt, "assoc_targets": [], "date_fields": []}

    types = {}
    for e in abstraction.get("enumerations", []):
        t = types[e["java"]["type"]] = entry(e, "enum")
        t["literals"] = {lit["name"]: lit["java"]["constant"] for lit in e["literals"]}
    for c in classes.values():
        t = types[c["java"]["type"]] = entry(c, "class")
        t["abstract"] = t["abstract"] or c.get("isAbstract", False)
        t["parents"] = [java_type[p] for p in c.get("parents", []) if p in java_type]
        t["date_fields"] = [a["java"]["field"] for a in c["attributes"] if a["java"]["type"] in DATE_TYPES]
        t["link_methods"] = []
    for assoc in abstraction.get("associations", []):
        for end in assoc["ends"]:
            java = end.get("java")
            if not java:   # extremo que ninguna clase Java contiene (no navegable)
                continue
            owner, target = types[java_type[java["owner"]]], java_type[end["type"]]
            owner["assoc_targets"].append(target)
            method = java.get("add") or java.get("set")
            if method and all((method, [target]) != (m, p) for m, p, _ in owner["link_methods"]):
                owner["link_methods"].append((method, [target], "%s.%s" % (assoc["name"], end["name"])))
    return types


def shadowed_link_methods(types):
    """Avisos de metodos add/set de una clase que redefinen (override) el de un extremo de una superclase:
    en los objetos de la subclase solo se puede crear el link del extremo de la subclase."""
    warnings = []
    for t in types.values():
        if t["kind"] != "class":
            continue
        seen, todo = [], list(t["parents"])
        while todo:   # todas las superclases
            p = todo.pop(0)
            if p not in seen:
                seen.append(p)
                todo += types[p]["parents"]
        for meth, params, end in t["link_methods"]:
            for p in seen:
                for pmeth, pparams, pend in types[p]["link_methods"]:
                    if (pmeth, pparams) == (meth, params) and pend != end:
                        warnings.append("%s.%s(%s) [extremo %s] redefine %s.%s(%s) [extremo %s]: en los objetos %s "
                                        "nunca se crean links de %s" % (t["name"], meth, ", ".join(params), end, p,
                                                                        pmeth, ", ".join(pparams), pend, t["name"], pend))
    return warnings


def enum_constants(src):
    """Constantes de un enum Java en orden de declaracion (el cuerpo hasta ';' o '}')."""
    body = re.search(r"enum\s+\w+[^{]*\{([^;}]*)", src)
    return re.findall(r"(?:^|,)\s*(\w+)", re.sub(r"\([^)]*\)", "", body.group(1))) if body else []


def add_int_date_constructors(t, types):
    """Agrega a la clase t un constructor auxiliar por cada constructor con parametros LocalDate.

    El auxiliar recibe cada fecha como int (dias desde 2000-01-01) y delega en el original con this(...),
    ya que BEAPI solo genera valores de tipos con literales. Modifica t["src"] y devuelve las firmas
    [(tipo, nombre), ...] de los constructores usables como builders (parametros primitivos o del modelo).
    """
    s, name = t["src"], t["name"]
    pattern = re.compile(r"\n([ \t]*)public\s+" + name + r"\s*\(([^)]*)\)\s*(?:throws[^{]*)?\{")
    found = [(m, split_params(m.group(2))) for m in pattern.finditer(s) if "<" not in m.group(2)]   # sin genericos
    existing = {tuple(ty for ty, _ in params) for _, params in found}
    inserts, ctors = [], []
    for m, params in found:
        if any(ty in DATE_TYPES for ty, _ in params):
            new = [("int", n + "Day") if ty in DATE_TYPES else (ty, n) for ty, n in params]
            sig = tuple(ty for ty, _ in new)
            if sig not in existing:   # puede existir ya (o repetirse entre dos constructores)
                indent = m.group(1)
                args = ", ".join("java.time.LocalDate.of(2000, 1, 1).plusDays(%sDay)" % n if ty in DATE_TYPES else n
                                 for ty, n in params)
                inserts.append((m.start(), "\n%s/** Constructor auxiliar para BEAPI: fechas como dias desde 2000-01-01. */"
                                           "\n%spublic %s(%s) {\n%s    this(%s);\n%s}\n" % (
                                               indent, indent, name, ", ".join("%s %s" % p for p in new),
                                               indent, args, indent)))
                existing.add(sig)
            params = new
        if all(ty in LITERAL_TYPES or ty in types for ty, _ in params):
            ctors.append(params)
    # se insertan de atras hacia adelante para no invalidar los offsets
    for off, code in reversed(inserts):
        s = s[:off] + code + s[off:]
    t["src"] = s
    return ctors


def default_root(types):
    """Clase concreta desde la que se alcanzan mas clases del modelo por asociaciones
    (desempate: mas extremos de asociacion). None si no hay clases concretas."""
    def reach(name):
        seen, todo = set(), [name]
        while todo:
            for target in types[todo.pop()]["assoc_targets"]:
                target = target.split(".")[-1]
                if target in types and target not in seen and target != name:
                    seen.add(target)
                    todo.append(target)
        return len(seen)
    classes = [t for t in types.values() if t["kind"] == "class" and not t["abstract"]]
    return max(classes, key=lambda t: (reach(t["name"]), len(t["assoc_targets"]))) if classes else None


# =========================================================================== paso 4: ejecutar BEAPI

def run_beapi(java, info, cfg, classes_dir, work):
    """Ejecuta BEAPI y devuelve la ruta de work/<nombre>/objects.ser con los objetos de la clase raiz."""
    scope = cfg["scope"]
    max_it = 3 * scope           # longitud maxima de la cadena de builders
    max_size = 3 * max_it        # sentencias maximas por secuencia
    ser = os.path.join(work, "objects.ser")
    if os.path.exists(ser):
        os.remove(ser)
    root_fq = info["root"]["fq"]
    package = root_fq.rsplit(".", 1)[0] if "." in root_fq else None
    cmd = [java, "-Xmx" + cfg["max_heap"], "-ea",
           "-cp", classes_dir + os.pathsep + BEAPI_JAR, "randoop.main.Main", "gentests",
           "--testclass=" + root_fq]
    cmd += ["--testclass=" + c for c in info["extra_classes"]]
    cmd += [
        "--junit-output-dir=" + os.path.join(work, "junit"),
        "--usethreads=false",
        "--instance-generics-integer",
        "--disable-contracts",
        "--forbid-null=true",
        "--timelimit=%d" % cfg["timelimit"],
        "--literals-level=ALL",
        "--literals-file=" + info["literals_file"],
        "--max-BE-iterations=%d" % max_it,
        "--all-sequences=true",   # combinar secuencias previas: sin esto no se crean links
        "--BEmaxsize=%d" % max_size,
        "--instance-object-integer",
        "--keep-only-builder-seqs",
        "--efficient-extensions",
        "--only-test-public-members",
        "--filtering=BEALL",
        "--canonicalizer-cfg=" + info["canonicalizer_file"],
        "--builder-methods=" + "|".join(info["builders"]),
        "--discard-generation-seqs",
        "--serialize-objects=" + ser,
        "--omitmethods=.*All\\(\\.*|toString\\(\\)|repO[kK]",
    ]
    if package:
        cmd.append("--junit-package-name=" + package)
    # se guarda el comando para poder repetirlo a mano
    write_text(os.path.join(work, "beapi", "command.txt"), " \\\n  ".join(cmd) + "\n")
    run(cmd, log_file=os.path.join(work, "beapi.log"), cwd=work)
    if not os.path.exists(ser):
        raise GenError("BEAPI termino pero no genero %s (ver %s)" % (ser, os.path.join(work, "beapi.log")))
    return ser


# =========================================================================== paso 6: proyecto BESSER
#
# El editor web de BESSER guarda un proyecto con varios diagramas por tipo
# (project.diagrams.ObjectDiagram es una lista). Un diagrama de objetos referencia su diagrama
# de clases por los ids del editor (classId, attributeId, associationId), que no son los UUID
# de las anotaciones Java: por eso se resuelve todo por nombre de clase, atributo y rol.

def write_buml_projects(name, result, model, args):
    """Escribe output/<nombre>/<nombre>_buml.json: una copia del modelo (el proyecto del editor) mas un
    diagrama de objetos por estructura seleccionada (o un archivo por estructura con --buml-split).

    Los diagramas de objetos referencian el diagrama de clases activo del modelo, el mismo del que sale la
    funcion de abstraccion. Devuelve [(archivo, [diagramas de objetos agregados])]."""
    data = model["project"]
    project = data["project"]
    class_diagram = model["class_diagram"]
    structures = result["structures"]
    if not structures:
        raise GenError("no hay estructuras para agregar al proyecto BESSER")

    numbers = parse_selection(args.buml_structures, len(structures))
    index = class_diagram_index(class_diagram["model"])
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    diagrams = [buml_object_diagram(structures[n - 1], n, class_diagram, index, now) for n in numbers]
    print("[%s]     proyecto base: %s ; diagrama de clases: '%s' ; estructuras: %s"
          % (name, os.path.relpath(model["path"]), class_diagram.get("title"),
             args.buml_structures or "todas (%d)" % len(numbers)))

    # una copia del proyecto con todos los diagramas, o una por diagrama (--buml-split)
    groups = [("_%d" % n, [d]) for n, d in zip(numbers, diagrams)] if args.buml_split else [("", diagrams)]
    outs = []
    for suffix, group in groups:
        existing = project["diagrams"].get("ObjectDiagram", [])
        new_project = dict(project,
                           id="project_%d_%s" % (time.time() * 1000, uuid.uuid4().hex[:9]),
                           name="%s_beapi%s" % (project.get("name", name), suffix),
                           createdAt=now,
                           diagrams=dict(project["diagrams"], ObjectDiagram=existing + group),
                           # el editor abre el primer diagrama agregado
                           currentDiagramIndices=dict(project.get("currentDiagramIndices") or {},
                                                      ObjectDiagram=len(existing)))
        out = os.path.join(args.output_dir, "%s_buml%s.json" % (name, suffix))
        write_text(out, json.dumps(dict(data, project=new_project), indent=2, ensure_ascii=False) + "\n")
        outs.append((out, group))
    print("[%s]     %d diagramas de objetos -> %s" % (name, len(diagrams), os.path.relpath(outs[0][0]) if len(outs) == 1
                                                      else "%d archivos %s_buml_<n>.json" % (len(outs), name)))
    return outs


def class_diagram_index(model):
    """Indices por nombre del diagrama de clases del editor:
      classes:    nombre -> elemento de la clase
      ancestors:  nombre -> [la clase y sus superclases]
      attributes: nombre -> atributos propios y heredados
      ends:       [(relacion, [(clase, rol) del source, (clase, rol) del target])]
    """
    elements, rels = model.get("elements", {}), model.get("relationships", {}).values()
    classes = {e["name"]: e for e in elements.values() if e.get("type") in BUML_CLASS_TYPES}
    by_id = {e["id"]: e["name"] for e in classes.values()}
    parents = {}
    for r in rels:
        if r.get("type") == "ClassInheritance":
            parents.setdefault(by_id.get(r["source"]["element"]), []).append(by_id.get(r["target"]["element"]))

    def lineage(name):   # recorrido en anchura: primero la clase, luego sus superclases
        seen, todo = [], [name]
        while todo:
            c = todo.pop(0)
            if c not in seen:
                seen.append(c)
                todo += parents.get(c, [])
        return seen

    ancestors = {name: lineage(name) for name in classes}
    attributes = {name: [elements[a] for c in ancestors[name] for a in classes[c].get("attributes", [])
                         if a in elements] for name in classes}
    # el rol vacio en el editor equivale al nombre de la clase en minuscula (como en BESSER)
    ends = [(r, [(by_id.get(r[side]["element"]), r[side].get("role") or (by_id.get(r[side]["element"]) or "").lower())
                 for side in ("source", "target")])
            for r in rels if r.get("type") in BUML_ASSOC_TYPES]
    return {"classes": classes, "attributes": attributes, "ancestors": ancestors, "ends": ends}


def find_relationship(index, link):
    """Relacion del diagrama de clases para un link de BEAPI. Devuelve (relacion, invertido).

    En BEAPI, sourceEnd es el rol del extremo que esta en la clase destino y targetEnd el
    del extremo opuesto. 'invertido' indica que el source del link es el target de la relacion.
    Primero se busca por clases y roles; si no hay coincidencia, por clases y nombre de asociacion.
    """
    src = index["ancestors"].get(link["sourceClass"], [link["sourceClass"]])
    dst = index["ancestors"].get(link["targetClass"], [link["targetClass"]])

    def matches(end_at_src, end_at_dst, by_role):
        (sc, sr), (dc, dr) = end_at_src, end_at_dst
        if sc not in src or dc not in dst:
            return False
        return not by_role or (dr == link["sourceEnd"] and (not link.get("targetEnd") or sr == link["targetEnd"]))

    for by_role in (True, False):
        candidates = [(r, False) for r, (s, t) in index["ends"] if matches(s, t, by_role)]
        candidates += [(r, True) for r, (s, t) in index["ends"] if matches(t, s, by_role)]
        if not by_role:
            candidates = [c for c in candidates if c[0].get("name") == link["association"]]
        if candidates:
            return candidates[0]
    raise GenError("ninguna asociacion del diagrama de clases corresponde al link %s.%s -> %s"
                   % (link["sourceClass"], link["sourceEnd"], link["targetClass"]))


def buml_object_diagram(structure, number, class_diagram, index, now):
    """Convierte una estructura de BEAPI en un ObjectDiagram del editor web de BESSER."""
    objects = structure["objects"]

    # disposicion: una columna por distancia (en links) a la raiz; los no alcanzables, en una columna extra
    adjacent = {}
    for l in structure["links"]:
        adjacent.setdefault(l["source"], []).append(l["target"])
        adjacent.setdefault(l["target"], []).append(l["source"])
    level, todo = {structure["root"]: 0}, [structure["root"]]
    while todo:
        o = todo.pop(0)
        for n in adjacent.get(o, []):
            if n not in level:
                level[n] = level[o] + 1
                todo.append(n)
    extra_col = max(level.values()) + 1

    # objetos: un ObjectName por objeto y un ObjectAttribute por cada attribute link
    column_y, counters, elements, boxes = {}, {}, {}, {}
    for o in objects:
        cls = index["classes"].get(o["class"])
        if cls is None:
            raise GenError("la clase %s no esta en el diagrama de clases '%s'" % (o["class"], class_diagram.get("title")))
        values = {a["name"]: a.get("value") for a in o["attributes"]}
        class_attrs = [a for a in index["attributes"][o["class"]] if a["name"] in values]
        missing = set(values) - {a["name"] for a in class_attrs}
        if missing:
            raise GenError("atributos de %s que no estan en el diagrama de clases: %s"
                           % (o["class"], ", ".join(sorted(missing))))
        counters[o["class"]] = counters.get(o["class"], 0) + 1
        col = level.get(o["id"], extra_col)
        box = {"x": col * (OBJ_WIDTH + COL_GAP), "y": column_y.get(col, 0),
               "width": OBJ_WIDTH, "height": OBJ_HEADER + ATTR_HEIGHT * len(class_attrs)}
        column_y[col] = box["y"] + box["height"] + ROW_GAP
        oid = str(uuid.uuid4())
        boxes[o["id"]] = (oid, box)
        attr_ids = []
        for i, a in enumerate(class_attrs):
            aid = str(uuid.uuid4())
            attr_ids.append(aid)
            v = values[a["name"]]
            if isinstance(v, dict):      # literal de enumeracion
                v = v["literal"]
            elif isinstance(v, bool):
                v = "true" if v else "false"
            # se copian las propiedades del atributo de la clase (attributeType, visibility, ...)
            elements[aid] = dict(a, id=aid, type="ObjectAttribute", owner=oid, attributeId=a["id"],
                                 name=a["name"] if v is None else "%s = %s" % (a["name"], v),
                                 bounds={"x": box["x"] + 0.5, "y": box["y"] + OBJ_HEADER + 0.5 + ATTR_HEIGHT * i,
                                         "width": OBJ_WIDTH - 1, "height": ATTR_HEIGHT})
        name = o["class"][0].lower() + o["class"][1:] + str(counters[o["class"]])   # p.ej. book1, book2
        elements[oid] = {"id": oid, "name": name, "type": "ObjectName", "owner": None, "bounds": box,
                         "attributes": attr_ids, "methods": [], "classId": cls["id"], "className": cls["name"]}

    # links: un ObjectLink por link, orientado como la relacion del diagrama de clases
    relationships = {}
    for l in structure["links"]:
        rel, reverse = find_relationship(index, l)
        (sid, sbox), (tid, tbox) = boxes[l["source"]], boxes[l["target"]]
        if reverse:
            (sid, sbox), (tid, tbox) = (tid, tbox), (sid, sbox)
        bounds, path, sdir, tdir = link_geometry(sbox, tbox)
        lid = str(uuid.uuid4())
        # nombre B-UML de la asociacion: en el editor dos relaciones pueden llamarse igual
        relationships[lid] = {"id": lid, "name": l["association"] or rel.get("name"), "type": "ObjectLink",
                              "owner": None, "bounds": bounds, "path": path,
                              "source": {"direction": sdir, "element": sid},
                              "target": {"direction": tdir, "element": tid},
                              "isManuallyLayouted": False, "associationId": rel["id"]}

    all_boxes = [b for _, b in boxes.values()]
    model = class_diagram["model"]
    return {
        "id": str(uuid.uuid4()),
        "title": BEAPI_DIAGRAM_TITLE % number,
        "model": {
            "version": model.get("version", "3.0.0"),
            "type": "ObjectDiagram",
            "size": {"width": max(b["x"] + b["width"] for b in all_boxes) + COL_GAP,
                     "height": max(b["y"] + b["height"] for b in all_boxes) + ROW_GAP},
            "interactive": {"elements": {}, "relationships": {}},
            "elements": elements,
            "relationships": relationships,
            "assessments": {},
            # solo se serializa a JSON: no hace falta copiarlo para cada diagrama
            "referenceDiagramData": model,
        },
        "lastUpdate": now,
        "references": {"ClassDiagram": class_diagram["id"]},
    }


def link_geometry(s, t):
    """Camino ortogonal entre dos objetos: (bounds absolutos, path relativo a ellos, direccion source/target)."""
    sy, ty = s["y"] + s["height"] / 2.0, t["y"] + t["height"] / 2.0
    if s["x"] == t["x"]:    # misma columna: sale y entra por la derecha
        sdir = tdir = "Right"
        p1, p2 = (s["x"] + s["width"], sy), (t["x"] + t["width"], ty)
        mx = max(p1[0], p2[0]) + COL_GAP / 2.0
    else:
        forward = s["x"] < t["x"]
        sdir, tdir = ("Right", "Left") if forward else ("Left", "Right")
        p1 = (s["x"] + s["width"], sy) if forward else (s["x"], sy)
        p2 = (t["x"], ty) if forward else (t["x"] + t["width"], ty)
        mx = (p1[0] + p2[0]) / 2.0
    points = [p1, (mx, p1[1]), (mx, p2[1]), p2]
    x0, y0 = min(p[0] for p in points), min(p[1] for p in points)
    bounds = {"x": x0, "y": y0, "width": max(p[0] for p in points) - x0, "height": max(p[1] for p in points) - y0}
    return bounds, [{"x": p[0] - x0, "y": p[1] - y0} for p in points], sdir, tdir


# =========================================================================== paso 7 (--conformance): invariantes OCL

def check_conformance(name, projects, class_diagram):
    """Evalua los invariantes OCL del diagrama de clases sobre los diagramas de objetos de cada proyecto de
    write_buml_projects() (solo los agregados por BEAPI; los que ya traia el modelo no se evaluan), con
    eval_bocl_interpreter.evaluate() en este mismo proceso. Escribe el informe junto a cada proyecto
    (<proyecto>_conformance.txt), muestra su resumen y devuelve [(informe, resultado de evaluate())].

    Las violaciones son un resultado, no un error: no hacen fallar la ejecucion."""
    ev = besser().ev
    reports = []
    for project_file, diagrams in projects:
        lines = []
        try:
            outcome = ev.evaluate(class_diagram, diagrams, emit=lines.append)
        except Exception as e:
            raise GenError("no se pudieron evaluar los invariantes OCL de %s: %s: %s"
                           % (os.path.relpath(project_file), type(e).__name__, e))
        report = os.path.splitext(project_file)[0] + "_conformance.txt"
        write_text(report, "\n".join(["Archivo: " + project_file] + lines) + "\n")
        print("[%s]     %s -> %s" % (name, os.path.relpath(project_file), os.path.relpath(report)))
        # el bloque final del informe: invariantes violados, no evaluables y la linea "Resumen: ..."
        for line in lines[lines.index("\n" + ev.SUMMARY_HEADER) + 1:]:
            print("[%s]       %s" % (name, line))
        reports.append((report, outcome))
    return reports


# =========================================================================== utilidades

def parse_args():
    ap = argparse.ArgumentParser(
        description="Genera objetos bounded-exhaustive con BEAPI a partir de un modelo B-UML y sus clases Java, "
                    "y los exporta como diagramas de objetos B-UML.")
    ap.add_argument("model", metavar="MODELO.json",
                    help="modelo B-UML: proyecto exportado del editor web de BESSER (p.ej. "
                         "examples/<nombre>/<nombre>.json). Las salidas van a output/<nombre>/")
    ap.add_argument("--java-dir", help="clases Java (por defecto <carpeta del modelo>/java)")
    ap.add_argument("-s", "--scope", type=int, help="scope de BEAPI (por defecto 3 o el de beapi.json)")
    ap.add_argument("-r", "--root-class", help="clase raiz a serializar (por defecto se deduce)")
    ap.add_argument("--timelimit", type=int, help="limite de tiempo de BEAPI en segundos (por defecto 36000)")
    ap.add_argument("--max-heap", help="heap maximo de la JVM de BEAPI (por defecto 4g)")
    ap.add_argument("-n", "--max-structures", type=int, help="exportar como maximo N estructuras al JSON")
    ap.add_argument("--java-home", help="JDK 8 a usar (por defecto: BEAPI_JAVA_HOME, JAVA_HOME o /usr/lib/jvm)")
    ap.add_argument("--work-dir", default=os.path.join(HERE, "work"), help="intermedios (por defecto work/)")
    ap.add_argument("-o", "--output-dir", default=os.path.join(HERE, "output"),
                    help="salidas: <DIR>/<nombre>/ (por defecto output/)")
    ap.add_argument("--keep-ser", action="store_true", help="copiar tambien el .ser a output/<nombre>/")
    ap.add_argument("-b", "--buml", action="store_true",
                    help="generar tambien output/<nombre>/<nombre>_buml.json: el modelo con las estructuras "
                         "agregadas como diagramas de objetos")
    ap.add_argument("--buml-structures", metavar="LISTA",
                    help="estructuras a incluir, p.ej. 1,3,5-8 (campo index del JSON). Por defecto todas")
    ap.add_argument("--buml-split", action="store_true",
                    help="un proyecto por estructura: output/<nombre>/<nombre>_buml_<n>.json")
    ap.add_argument("--conformance", action="store_true",
                    help="evaluar los invariantes OCL del modelo sobre los diagramas de objetos generados; "
                         "el informe va a <proyecto>_conformance.txt. Implica --buml")
    ap.add_argument("--reuse-json", action="store_true",
                    help="no ejecutar BEAPI: usar el output/<nombre>/<nombre>.json existente")
    args = ap.parse_args()
    # --buml-structures, --buml-split y --conformance implican --buml
    if args.buml_structures or args.buml_split or args.conformance:
        args.buml = True
    return args


def load_config(model_dir, args):
    """DEFAULTS, pisados por el beapi.json de la carpeta del modelo y luego por la linea de comandos."""
    cfg = dict(DEFAULTS)
    path = os.path.join(model_dir, CONFIG_NAME)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        unknown = set(data) - set(DEFAULTS) - {"description"}
        if unknown:
            raise GenError("claves desconocidas en %s: %s" % (path, ", ".join(sorted(unknown))))
        cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    for key in ("scope", "root_class", "timelimit", "max_heap", "max_structures"):
        if getattr(args, key) is not None:
            cfg[key] = getattr(args, key)
    cfg["scope"] = int(cfg["scope"])
    if cfg["scope"] < 1:
        raise GenError("el scope debe ser >= 1")
    return cfg


def find_java8(explicit):
    """Devuelve el JAVA_HOME de un JDK 8 (BEAPI usa una version de Randoop que lo requiere)."""
    candidates = [explicit] if explicit else []
    candidates += [os.environ.get("BEAPI_JAVA_HOME"), os.environ.get("JAVA_HOME")]
    candidates += sorted(glob.glob("/usr/lib/jvm/java-8-*")) + sorted(glob.glob("/usr/lib/jvm/java-1.8.0*"))
    candidates += sorted(glob.glob("/Library/Java/JavaVirtualMachines/*1.8*/Contents/Home"))
    candidates += sorted(glob.glob("/Library/Java/JavaVirtualMachines/*-8*/Contents/Home"))
    for home in filter(None, candidates):
        java, javac = os.path.join(home, "bin", "java"), os.path.join(home, "bin", "javac")
        if os.path.exists(java) and os.path.exists(javac):
            try:   # "java -version" escribe en stderr, p.ej.: openjdk version "1.8.0_462"
                out = subprocess.run([java, "-version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     universal_newlines=True).stdout
            except OSError:
                out = ""
            if re.search(r'version "1\.8', out):
                return home
        if home == explicit:
            raise GenError("%s no es un JDK 8 (con javac)" % home)
    raise GenError("no se encontro un JDK 8. Instalarlo (p.ej. openjdk-8-jdk) o indicar --java-home / BEAPI_JAVA_HOME")


def run(cmd, log_file=None, cwd=None):
    """Ejecuta cmd; si falla lanza GenError con la salida. Sin log_file devuelve la salida estandar;
    con log_file la vuelca ahi (BEAPI escribe mucho) y en el error muestra solo las ultimas lineas."""
    if log_file:
        with open(log_file, "w") as f:
            res = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=cwd)
        if res.returncode != 0:
            with open(log_file, errors="replace") as f:
                tail = f.readlines()[-25:]
            raise GenError("fallo (%d): %s\n--- ultimas lineas de %s ---\n%s"
                           % (res.returncode, cmd[0], log_file, "".join(tail)))
        return None
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, cwd=cwd)
    if res.returncode != 0:
        raise GenError("fallo (%d): %s\n%s" % (res.returncode, " ".join(cmd), res.stdout))
    return res.stdout


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_source(path):
    """Texto de un .java (UTF-8 o, si no lo es, ISO-8859-1)."""
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("iso-8859-1")


def split_params(raw):
    """'final int a, @X Book b' -> [('int', 'a'), ('Book', 'b')] (sin final ni anotaciones)."""
    out = []
    for part in raw.split(","):
        words = re.sub(r"\bfinal\b|@\w+(\([^)]*\))?", " ", part).split()
        if words:
            out.append((" ".join(words[:-1]), words[-1]))
    return out


def parse_selection(spec, count):
    """'1,3,5-8' -> [1, 3, 5, 6, 7, 8] (numeros de estructura desde 1, sin repetidos). None -> todas."""
    if not spec:
        return list(range(1, count + 1))
    numbers = []
    for part in spec.split(","):
        m = re.match(r"^\s*(\d+)\s*(?:-\s*(\d+)\s*)?$", part)
        if not m:
            raise GenError("seleccion de estructuras invalida: '%s' (ejemplo: 1,3,5-8)" % spec)
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        if lo < 1 or hi > count or lo > hi:
            raise GenError("rango %s fuera de 1..%d" % (part.strip(), count))
        numbers += range(lo, hi + 1)
    return list(dict.fromkeys(numbers))


if __name__ == "__main__":
    sys.exit(main())
