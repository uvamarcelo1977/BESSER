# beapi-object-generator

Genera objetos con **BEAPI** (generación *bounded-exhaustive*) para modelos Java
anotados con BESSER (`@BClass`, `@BAttribute`, `@BAssociationEnd`,
`@BEnumeration`, `@BLiteral`). Escribe cada estructura generada en un **JSON**
como diagrama de objetos B-UML: objetos, *attribute links* y *links*.
Opcionalmente (`--buml`) agrega esas estructuras como diagramas de objetos a una
copia del proyecto del editor web de BESSER del ejemplo, listo para importar.

---

## 1. Requisitos

| Requisito | Detalle |
|-----------|---------|
| Python    | 3.8 o superior. Solo usa la biblioteca estándar. |
| JDK 8     | Obligatorio (`java` **y** `javac` 1.8). El Randoop modificado de BEAPI necesita Java 8. En Ubuntu/Debian: `sudo apt install openjdk-8-jdk` |

El script busca el JDK 8 en este orden:

1. `--java-home <dir>`
2. la variable `BEAPI_JAVA_HOME`
3. la variable `JAVA_HOME`, si apunta a un JDK 8
4. `/usr/lib/jvm/java-8-*`, `/usr/lib/jvm/java-1.8.0*` y las rutas habituales de macOS

---

## 2. Estructura

```
beapi-object-generator/
├── beapi_gen.py          script principal
├── validar_bocl.py       valida con B-OCL los invariantes sobre los diagramas de objetos (ver 5.7)
├── README.md
├── libs/beapi.jar        BEAPI (Randoop modificado)
├── tools/BObjectDump.java  extractor .ser -> JSON por reflection (anotaciones BESSER)
├── support/besser/trace/ anotaciones BESSER (se usan si un ejemplo no las trae)
├── examples/             CASOS DE ESTUDIO: una carpeta por ejemplo
│   ├── library_without_repok/   modelo Library SIN repOk (+ beapi.json)
│   │   └── buml_model/          proyecto del editor web de BESSER (LibraryLoan_v2.json)
│   ├── library_with_repok/      modelo Library CON repOk (sin beapi.json ni buml_model/)
│   └── hospital/                modelo HospitalManagementSystem, con herencia (+ beapi.json)
│       └── buml_model/          proyecto del editor web de BESSER (HospitalManagementSystem.json)
├── work/                 (generado) copias de trabajo, configuración BEAPI, logs, .ser
└── output/               (generado) un <ejemplo>.json por cada ejemplo procesado
                          y, con --buml, <ejemplo>_buml.json (proyecto BESSER)
```

Los ejemplos de `examples/` **nunca se modifican**. El script trabaja sobre una
copia en `work/<ejemplo>/src`.

### Organización de `beapi_gen.py`

El archivo se lee de arriba hacia abajo en el mismo orden en que se ejecuta:

| Sección | Funciones | Qué hace |
|---------|-----------|----------|
| Constantes | `LITERAL_TYPES`, `DEFAULTS`, ... | Valores por defecto y claves válidas de `beapi.json`, comentadas. |
| Programa principal | `main()`, `generate()` | `main` elige los ejemplos y busca Java; `generate` recorre los pasos 1/4–4/4 de un ejemplo. |
| Pasos 1–2 | `prepare()`, `parse_model()`, `add_int_date_constructors()`, `default_root()` | Copia y adapta los fuentes y escribe la configuración de BEAPI (5.1). |
| Paso 4 | `run_beapi()` | Arma y ejecuta el comando de BEAPI (5.3). |
| Paso 6 | `write_buml_projects()` y sus funciones | Convierte las estructuras en diagramas de objetos del editor (5.6). |
| Utilidades | `parse_args()`, `load_config()`, `find_java8()`, `run()`, ... | Línea de comandos, configuración, Java y archivos. |

---

## 3. Uso rápido

```sh
cd beapi-object-generator

# procesar todos los ejemplos de examples/
python3 beapi_gen.py

# procesar uno (o varios) por nombre de carpeta
python3 beapi_gen.py library_without_repok

# cambiar el scope o la clase raíz
python3 beapi_gen.py library_with_repok -s 2 -r Library

# listar los ejemplos disponibles
python3 beapi_gen.py -l

# además, generar el proyecto BESSER con todas las estructuras como diagramas de objetos
python3 beapi_gen.py library_without_repok --buml

# solo algunas estructuras (campo "index" del JSON), sin volver a correr BEAPI
python3 beapi_gen.py library_without_repok --reuse-json --buml-structures 1,7-8,13
```

Salida típica (`python3 beapi_gen.py library_without_repok --buml`, con el
`beapi.json` del ejemplo):

```
> Java 8: /usr/lib/jvm/java-8-openjdk-amd64
[library_without_repok] 1/4 preparando fuentes y configuracion BEAPI (scope 2)
[library_without_repok]     raiz: Library ; otras clases: Author, Book, Genre
[library_without_repok]     builder: Author.<init>\(java.lang.String,int\)
[library_without_repok]     builder: Book.<init>\(java.lang.String,int,int,int,float,Genre\)
[library_without_repok]     builder: Book.addLibrary\(Library\)
[library_without_repok]     builder: Book.addAuthor\(Author\)
[library_without_repok]     builder: Library.<init>\(java.lang.String,java.lang.String,java.lang.String,java.lang.String\)
[library_without_repok]     builder: Genre:Romance
[library_without_repok]     builder: Genre:Horror
[library_without_repok] 2/4 compilando con Java 8
[library_without_repok] 3/4 ejecutando BEAPI (log: work/library_without_repok/beapi.log)
[library_without_repok] 4/4 exportando objetos a JSON por reflection (anotaciones BESSER)
[library_without_repok] listo: 81 estructuras -> output/library_without_repok.json (1.8 s)
[library_without_repok] agregando los diagramas de objetos al proyecto BESSER
[library_without_repok]     proyecto base: examples/library_without_repok/buml_model/LibraryLoan_v2.json ; diagrama de clases: 'Library with OCL' ; estructuras: todas (81)
[library_without_repok]     81 diagramas de objetos -> output/library_without_repok_buml.json
```

### Opciones

| Opción | Descripción |
|--------|-------------|
| `ejemplos...` | Nombres de carpetas de `examples/` o rutas a carpetas. Sin argumentos se procesan todas. |
| `-s, --scope N` | Scope de BEAPI. Por defecto es 3, o el valor de `beapi.json`. |
| `-r, --root-class C` | Clase raíz: BEAPI serializa solo objetos de esta clase. Por defecto se deduce (ver 5.1). |
| `--no-all-sequences` | Vuelve a `--all-sequences=false`, el valor fijo de `gen_objects_beapi.sh`. Con esa opción no se crean links (ver 5.4). |
| `--timelimit SEG` | Límite de tiempo de BEAPI. Por defecto 36000. |
| `--max-heap 4g` | Heap de la JVM de BEAPI. |
| `-n, --max-structures N` | Exporta al JSON como máximo N estructuras. |
| `--java-home DIR` | JDK 8 que se usa. |
| `--keep-ser` | Copia también el `.ser` a `output/<ejemplo>.ser`. |
| `-o, --output-dir DIR` | Carpeta de los JSON. Por defecto `output/`. |
| `--examples-dir DIR`, `--work-dir DIR` | Cambian las carpetas de entrada y de trabajo. |
| `-b, --buml` | Genera también `output/<ejemplo>_buml.json`: el proyecto BESSER del ejemplo con las estructuras agregadas como diagramas de objetos (ver 5.6). Las opciones `--buml-*` lo activan solas. |
| `--buml-base PROYECTO.json` | Proyecto BESSER base. Por defecto, el único `.json` de `examples/<ejemplo>/buml_model/`. |
| `--buml-structures LISTA` | Estructuras a incluir, p.ej. `1,3,5-8`. Son los valores del campo `index` del JSON (desde 1). Por defecto, todas. |
| `--buml-class-diagram D` | Diagrama de clases que referencian los diagramas de objetos: título, id o posición (desde 0). Por defecto, el de título igual al modelo de las anotaciones. |
| `--buml-split` | Un proyecto por estructura: `output/<ejemplo>_buml_<n>.json`. |
| `--reuse-json` | No ejecuta BEAPI (ni necesita Java): usa el `output/<ejemplo>.json` existente. Pensado para usar con `--buml`. |

Si algún ejemplo falla, el código de salida es 1. Los demás ejemplos se
procesan igual.

---

## 4. Agregar un caso de estudio

1. Crear `examples/<nombre>/` y copiar ahí las clases Java anotadas. Se
   respeta la estructura de paquetes y se admite el paquete por defecto.
2. Incluir la carpeta `besser/trace/` con las anotaciones. Si no está, el
   script copia la de `support/`.
3. (Opcional) Agregar `examples/<nombre>/beapi.json` para ajustar la
   generación (sección 6).
4. (Opcional) Guardar en `examples/<nombre>/buml_model/` el proyecto exportado
   del editor web de BESSER (un único `.json`), para poder usar `--buml`.
5. Ejecutar `python3 beapi_gen.py <nombre>`. El resultado queda en
   `output/<nombre>.json`.

Qué deben cumplir las clases:

- Las clases del modelo llevan `@BClass` y los enums `@BEnumeration`. Las
  constantes del enum, `@BLiteral`. Si un enum no usa `@BLiteral`, sus
  constantes se leen del cuerpo del enum (hasta el primer `;` o `}`).
- Los valores se leen con los **getters** anotados con `@BAttribute` y
  `@BAssociationEnd`, con `@Retention(RUNTIME)`. El extractor no mira los
  campos.
- Cada clase necesita al menos un constructor público cuyos parámetros sean
  primitivos (`int`, `long`, `float`, `double`, `boolean`), `String`,
  `LocalDate` u otros tipos del modelo. Los constructores con parámetros
  genéricos (`List<...>`, `ArrayList<...>`) se ignoran.
- Las asociaciones se construyen con métodos `public void add*/put*/link*/attach*/register*(...)`
  cuyos parámetros sean tipos del modelo. Ejemplos: `addBook(Book)` y
  `addAuthor(Author)`.
- Todo objeto alcanzable desde la raíz por los `@BAssociationEnd` debe tener
  `@BClass`.

---

## 5. Qué hace el script (paso a paso)

Por cada ejemplo:

### 5.1 Preparación (`work/<ejemplo>/src`, `work/<ejemplo>/beapi/`)

Las secciones del informe que se mencionan corresponden a cada ajuste.

| Paso | Detalle | Informe |
|------|---------|---------|
| Copia de fuentes | Solo los `.java`. El original no se toca. | Fase 0.2 |
| `Serializable` | Agrega `implements java.io.Serializable` y `serialVersionUID = 1L` a cada `@BClass`. | Fase 0.3 |
| Constructores auxiliares | Por cada constructor con `LocalDate` agrega otro que recibe la fecha como `int` (días desde 2000-01-01): `Book(String,int,int releaseDay,int,float,Genre)`. No agrega atributos ni anotaciones, así que la traza BESSER no cambia. | B.2, problema 2.a |
| Builders (`builders.txt`) | Constructores utilizables (en su versión `int` si tenían fecha), métodos `add*...` entre tipos del modelo y constantes de enum (`Genre:Romance`). No incluye setters ni `repOk`. | B.3 |
| Literales (`literals.txt`) | Pocos valores por tipo, solo para los tipos que usan los builders (`int` siempre). Por defecto: `int:1`, `long:1`, `float:1.0`, `double:1.0`, `boolean:true`, `String:"a"` y `String:"b"`. | B.4 |
| Canonicalizador (`canonicalizer.properties`) | `max.objects=S`, `max.array.objects=S`, `save.array.null=true`, `omit.fields=modCount|<campos LocalDate>`. | B.5 |
| Clase raíz | Por defecto, la clase concreta desde la que se alcanzan más clases del modelo siguiendo los `@BAssociationEnd`. Si hay empate, la que tiene más extremos. Las demás clases (y los enums) se pasan como `--testclass` extra. | problema 2.c, B.7 |

### 5.2 Compilación

Usa `javac` 1.8 (`-source 1.8 -target 1.8 -encoding UTF-8`) y deja las clases
en `work/<ejemplo>/classes`. Si un fuente no es UTF-8 válido, se lee como
ISO-8859-1 y se reescribe en UTF-8 en la copia.

### 5.3 Ejecución de BEAPI

Las opciones son las de `gen_objects_beapi.sh` (sección 2 del informe), con los
cambios de la Fase B:

```
java -Xmx4g -ea -cp classes:libs/beapi.jar randoop.main.Main gentests
  --testclass=<raíz> --testclass=<otras clases...>
  --filtering=BEALL --canonicalizer-cfg=<canonicalizer.properties>
  --literals-file=<literals.txt> --literals-level=ALL
  --builder-methods="<builders unidos con |>"
  --max-BE-iterations=3*S  --BEmaxsize=9*S  --timelimit=36000
  --all-sequences=true                       <- era false (fijo) en el script original
  --forbid-null=true --keep-only-builder-seqs --discard-generation-seqs
  --efficient-extensions --only-test-public-members
  --instance-generics-integer --instance-object-integer
  --disable-contracts --usethreads=false
  --serialize-objects=work/<ejemplo>/objects.ser
  --omitmethods=".*All\(\.*|toString\(\)|repO[kK]"   <- cubre repOk y repOK
```

El comando completo queda en `work/<ejemplo>/beapi/command.txt` y la salida de
BEAPI en `work/<ejemplo>/beapi.log`.

### 5.4 Por qué hacen falta estos ajustes

Sin ellos BEAPI nunca construye un `Book` (informe, sección 4):

- **LocalDate**: el canonicalizador descarta todo objeto que contiene un
  `LocalDate`. Por eso se agregan los constructores con fecha `int` y se omiten
  los campos de fecha en el canonicalizador. Consecuencia: dos objetos que solo
  difieren en la fecha se consideran el mismo.
- **`--all-sequences=true`**: con `false`, cada iteración combina solo los
  objetos nuevos de la iteración anterior. Así nunca se juntan un `Book` y una
  `Library` ya construidos en `addLibrary(Library)`, y no aparecen links.

### 5.5 Exportación a JSON

`tools/BObjectDump.java` lee el `.ser` con `readObject()` hasta EOF. Recorre
cada grafo desde la raíz por reflection, usando **solo** las anotaciones
BESSER, de modo que no depende de los nombres Java. El script agrega metadatos
y escribe `output/<ejemplo>.json`.

### 5.6 Proyecto BESSER (`--buml`)

El proyecto que exporta el editor web de BESSER (p.ej.
`examples/library_without_repok/buml_model/LibraryLoan_v2.json`) guarda varios
diagramas por tipo: `project.diagrams.ClassDiagram` y
`project.diagrams.ObjectDiagram` son listas. Con `--buml` el script copia el
proyecto y agrega al final de `ObjectDiagram` un diagrama por estructura
seleccionada, titulado `BEAPI structure <n>`. Los diagramas que ya tenía el
proyecto se conservan. La copia recibe un `id` nuevo y el nombre
`<proyecto>_beapi`, para que no choque con el original al importarla.

**El formato no es el mismo que el JSON de BEAPI**, así que se convierte:

| JSON de BEAPI | Diagrama de objetos de BESSER |
|---------------|-------------------------------|
| `classId` = UUID de `@BClass` | `classId` = id del elemento `Class` en el diagrama del editor |
| atributo `{name, type, value}` | elemento `ObjectAttribute` con `name: "pages = 1"` y `attributeId` |
| enum `{enumeration, literal}` | `"genre = Romance"` |
| link `{association, sourceEnd, targetEnd}` | `ObjectLink` con `associationId` = id de la relación del editor |
| (no tiene) | `bounds` de objetos y atributos, `path` de los links |

Los UUID de las anotaciones Java no coinciden con los ids del editor. Por eso
la conversión resuelve por nombre:

- **Clase** por su nombre. Los atributos se ordenan como en el diagrama de
  clases, incluidos los heredados (`ClassInheritance`).
- **Asociación** por los roles de sus extremos, no por su nombre. En el
  diagrama "Library with OCL" las dos relaciones se llaman `books`. Un rol
  vacío equivale al nombre de la clase en minúscula, como en BESSER. El source y
  el target del `ObjectLink` siguen la orientación de la relación del
  diagrama de clases. El link se nombra con la asociación B-UML (`books`,
  `books_1`).
- **Diagrama de clases referenciado**: por defecto, el que tiene como título el
  modelo de las anotaciones con espacios en lugar de `_` (`Library_with_OCL`
  → "Library with OCL"). Si no hay ninguno, se usa el activo del proyecto. Cada
  diagrama de objetos lleva `references.ClassDiagram` con el id de ese diagrama
  y una copia del modelo de clases en `referenceDiagramData`, como los que crea
  el editor.

Los objetos se llaman `book1`, `author1`, `author2`, ... y se disponen en
columnas según su distancia (en links) a la raíz.

**¿Un archivo o uno por diagrama?** Pueden ir todos en un solo proyecto. El
conversor de BESSER (`json_to_buml_project`) procesa todos los diagramas de
objetos y genera un `ObjectModel` por cada uno. La desventaja es el tamaño:
cada diagrama incluye una copia del diagrama de clases (las 81 estructuras de
`library_without_repok` ocupan ~4,6 MB; las 16 de `hospital`, ~1,3 MB). Con
muchas estructuras conviene elegir algunas con `--buml-structures`, o usar
`--buml-split` para obtener un proyecto por estructura.

Validación: los proyectos generados se importaron con el conversor JSON → B-UML
de BESSER 7.8.3. Cada `ObjectModel` tiene los mismos objetos y links que la
estructura de BEAPI, y cada link queda en el extremo de asociación correcto.

### 5.7 Validación con B-OCL (`validar_bocl.py`)

`validar_bocl.py` es un script aparte que evalúa los invariantes OCL del
diagrama de clases sobre cada diagrama de objetos de un proyecto BESSER (por
ejemplo, un `output/<ejemplo>_buml.json`):

```sh
python3 validar_bocl.py output/library_without_repok_buml.json [-c "Library with OCL"]
```

A diferencia de `beapi_gen.py`, **no** usa solo la biblioteca estándar: importa
los conversores de BESSER (`besser.utilities.web_modeling_editor...`) y
`bocl`, así que hay que correrlo en un entorno con BESSER y B-OCL instalados.

---

## 6. Configuración por ejemplo: `beapi.json`

Es un archivo opcional en `examples/<nombre>/beapi.json`. Todas las claves son
opcionales, y las opciones de línea de comandos tienen prioridad sobre el
archivo.

```json
{
  "description": "texto libre",
  "scope": 3,
  "root_class": "Book",
  "literals": {"int": [1], "String": ["a"], "float": [1.0]},
  "enum_literals": {"Genre": ["Romance", "Horror"]},
  "extra_builders": [],
  "exclude_builders": [],
  "builders": null,
  "all_sequences": true,
  "timelimit": 36000,
  "max_heap": "4g",
  "max_structures": null
}
```

| Clave | Significado |
|-------|-------------|
| `scope` | Cota de BEAPI. Define `max.objects`, las iteraciones (3·S) y el tamaño de las secuencias (9·S). |
| `root_class` | Clase raíz, con nombre simple o calificado. |
| `literals` | Valores por tipo Java (`int`, `long`, `float`, `double`, `boolean`, `String`). Reemplazan a los valores por defecto. |
| `enum_literals` | Un número N (las primeras N constantes de cada enum; por defecto 2) o un objeto `{enum: [constantes]}`. |
| `builders` | Si se define, **reemplaza** la lista generada automáticamente. Usa el formato regex de BEAPI, p.ej. `"Book.addAuthor\\(Author\\)"`. |
| `extra_builders` | Builders que se agregan a los generados. |
| `exclude_builders` | Expresiones regulares: se quitan los builders que coinciden. |
| `all_sequences` | `true` por defecto (ver 5.4). |
| `max_structures` | Límite de estructuras exportadas al JSON. |

El ejemplo `library_without_repok/beapi.json` reproduce la configuración del
**Apéndice A** del informe.

> **Tamaño del espacio de búsqueda.** Cada literal extra multiplica todas las
> combinaciones de los parámetros de cada constructor. `Book` tiene 6
> parámetros. Conviene agregar valores de a uno y medir.

---

## 7. Formato del JSON de salida

```json
{
  "example": "library_without_repok",
  "generator": "BEAPI",
  "generatedAt": "2026-10-29T12:00:00",
  "model": "Library_with_OCL",
  "rootClass": "Book",
  "scope": 3,
  "structureCount": 14,
  "beapi": {
    "seconds": 3.1,
    "allSequences": true,
    "testClasses": ["Book", "Author", "Genre", "Library"],
    "builders": ["..."],
    "literalsFile": "work/library_without_repok/beapi/literals.txt",
    "canonicalizerFile": "work/library_without_repok/beapi/canonicalizer.properties",
    "omittedFields": ["modCount", "birth", "release"],
    "serializedObjects": "work/library_without_repok/objects.ser"
  },
  "structures": [
    {
      "index": 1,
      "model": "Library_with_OCL",
      "root": "o1",
      "objects": [
        {
          "id": "o1", "class": "Book", "classId": "8e8061d7-...",
          "attributes": [
            {"id": "779ec665-...", "name": "genre", "type": "Genre",
             "value": {"enumeration": "Genre", "literal": "Romance"}},
            {"id": "c6e22ddc-...", "name": "pages", "type": "int", "value": 1},
            {"id": "83a38881-...", "name": "release", "type": "date", "value": "2000-01-02"},
            {"id": "d149ff8a-...", "name": "title", "type": "str", "value": "a"}
          ]
        },
        {"id": "o2", "class": "Library", "classId": "7608dad3-...", "attributes": ["..."]}
      ],
      "links": [
        {
          "associationId": "0b70af27-...", "association": "books",
          "source": "o1", "sourceClass": "Book",
          "sourceEndId": "3ad214ad-...", "sourceEnd": "library",
          "sourceEndLower": 1, "sourceEndUpper": -1,
          "target": "o2", "targetClass": "Library", "targetEnd": "books"
        }
      ]
    }
  ]
}
```

- Cada elemento de `structures` es un diagrama de objetos: un objeto raíz
  serializado por BEAPI y todo lo que alcanza.
- `index` numera las estructuras desde 1, en el orden del `.ser`. Es el número
  que se usa en `--buml-structures`. Los JSON generados antes de este campo
  siguen sirviendo con `--reuse-json`: se usa la posición en la lista.
- Los `id` y `classId` son los UUID de las anotaciones y sirven como
  trazabilidad hacia el DomainModel B-UML.
- Los links se deduplican por (asociación, par de objetos).
- Las fechas se exportan en formato ISO y los enums como `{enumeration, literal}`.

---

## 8. Resultados de referencia (Java 8)

Cada ejemplo se corrió con su configuración actual: el `beapi.json` del
ejemplo si existe y, si no, los valores por defecto (scope 3, `String` con
`"a"` y `"b"`).

| Ejemplo | Scope | Raíz | Estructuras | Contenido | Tiempo |
|---------|-------|------|-------------|-----------|--------|
| `library_without_repok` | 2 | Library | 81 | Una `Library` por estructura, sin links: solo varían sus 4 atributos `String`. | ~2 s |
| `library_with_repok` | 3 | Book | 76 | `Book` solo (4), con 1 `Library` (64) o con 1 `Author` (8). | ~3 s |
| `library_with_repok -r Library` | 3 | Library | 80 | `Library` sola (16) o con 1 `Book` (64). | ~3 s |
| `hospital` | 4 | Doctor | 16 | Hasta 5 objetos y 4 links: `Doctor` con `MedicalAppointment` y `Patient`. | ~30 s |

Con su `beapi.json` actual (3 valores de `String`), `library_without_repok`
no llega a generar links. Ver la sección 9 sobre scope y literales.

---

## 9. Limitaciones y consejos

- **Explosión combinatoria**: subir el scope o agregar literales hace crecer
  el espacio muy rápido. Para diagramas conviene scope 2–3 con dominios
  mínimos. Con scope 2 todavía no aparecen links en `library_without_repok`.
- **Fechas**: los campos `LocalDate` no se canonicalizan. Conviene un único
  valor (`int: [1]`); si no, las variantes que solo cambian la fecha se
  descartan como repetidas. Solo se trata `java.time.LocalDate`; otros tipos de
  fecha (`Date`, `LocalDateTime`) no tienen soporte.
- **Asociaciones bidireccionales**: los `add*()` del modelo no actualizan el
  extremo opuesto. En un modelo navegable desde ambos lados (como
  `library_with_repok`), BEAPI puede generar grafos inconsistentes. Por
  ejemplo, un libro con `addLibrary(l)` que no aparece en `l.getBooks()`.
- **Duplicados**: las listas permiten agregar el mismo objeto dos veces. El
  JSON deduplica los links.
- **Análisis de fuentes**: la detección de constructores y métodos usa
  expresiones regulares. Funciona con código generado como el de los ejemplos.
  Con código más complejo, revisar `work/<ejemplo>/beapi/builders.txt` y, si
  hace falta, fijar la lista con `builders` en `beapi.json`.
- **repOk**: BEAPI lo ignora. Para quedarse solo con los objetos válidos de un
  modelo con repOk, hay que filtrar el JSON o el `.ser` después.
- **Nombres de objetos en BESSER**: al convertir a B-UML, BESSER renombra los
  objetos de las clases que tienen un atributo `name` con el valor de ese
  atributo. Con los literales mínimos, todos quedan como `a`. También les pasa
  a los diagramas creados en el editor (los del ejemplo quedan como `Sample`).
  En el editor se ven `book1`, `author1`, etc.
- **Proyecto BESSER y modelo Java**: las clases, atributos y roles del JSON
  deben existir en el diagrama de clases elegido. Si el Java se generó de otra
  versión del diagrama, la conversión falla con un mensaje que nombra lo que
  falta.
