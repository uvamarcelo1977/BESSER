# beapi-object-generator

Genera objetos con **BEAPI** (generación *bounded-exhaustive*) a partir de un
**modelo B-UML** y de las **clases Java que lo implementan**, y los devuelve en
términos del modelo: cada estructura generada es un diagrama de objetos B-UML
(objetos, *attribute links* y *links*).

La relación entre el modelo y el código es la **función de abstracción** que
calcula `abstraction_function.py` a partir del modelo. Las clases Java no
llevan anotaciones y el script **no las genera ni las modifica**: son la
implementación que se analiza.

Opcionalmente:

- `--buml` agrega las estructuras como diagramas de objetos a una copia del
  modelo (un proyecto del editor web de BESSER, listo para importar);
- `--conformance` evalúa sobre cada uno de esos diagramas los invariantes OCL
  del modelo, para verificar si los objetos que construye el código Java
  **conforman** al modelo (secciones 5.8 y 5.9).

---

## 1. Requisitos

| Requisito | Detalle |
|-----------|---------|
| Python + BESSER | El entorno virtual de BESSER (`venv/` en la raíz del repositorio), con B-OCL (`bocl`). Todos los comandos usan `../venv/bin/python`. Si BESSER no está instalado en el entorno, el script usa el del repositorio. |
| JDK 8 | Obligatorio (`java` **y** `javac` 1.8). El Randoop modificado de BEAPI necesita Java 8. En Ubuntu/Debian: `sudo apt install openjdk-8-jdk`. No hace falta con `--reuse-json`. |
| BEAPI | `libs/beapi.jar` (incluido). |

El script busca el JDK 8 en este orden:

1. `--java-home <dir>`
2. la variable `BEAPI_JAVA_HOME`
3. la variable `JAVA_HOME`, si apunta a un JDK 8
4. `/usr/lib/jvm/java-8-*`, `/usr/lib/jvm/java-1.8.0*` y las rutas habituales de macOS

---

## 2. Estructura

```
beapi-object-generator/
├── beapi_gen.py               script principal
├── abstraction_function.py    modelo B-UML -> función de abstracción (.abstraction.json)
├── eval_bocl_interpreter.py   evalúa con B-OCL los invariantes sobre diagramas de objetos (--conformance)
├── tools/BAbstractionDump.java  verifica las clases contra la abstracción y exporta el .ser a JSON
├── libs/beapi.jar             BEAPI (Randoop modificado)
├── README.md
├── tests/                     tests de los casos de estudio (leen output/)
├── examples/                  CASOS DE ESTUDIO: una carpeta por caso
│   ├── team_ocl/              Team/Player con dos invariantes OCL (ejemplo mínimo, ver 4.2 y 5.9)
│   ├── library/               Library/Book/Author/Genre, diagrama "Library with OCL"
│   ├── school/                Student/Subject/InfoExam/Professor
│   ├── hospital/              HospitalManagementSystem, con herencia (Person) y enums
│   └── nuevo_booking/         reservas de hotel (Booking, Room, Guest, Invoice, ...)
├── work/                      (generado) intermedios de cada caso
└── output/                    (generado) resultados de cada caso, en output/<caso>/
```

Cada caso de estudio tiene la misma forma (ver 4.1):

```
examples/<caso>/
├── <caso>.json    modelo B-UML original (proyecto del editor web de BESSER)
├── beapi.json     (opcional) configuración de BEAPI
└── java/          clases Java, sin anotaciones
```

Los casos de `examples/` **nunca se modifican**. El script trabaja sobre una
copia en `work/<caso>/src`. `output/` y `work/` están en `.gitignore`.

### Organización de `beapi_gen.py`

El archivo se lee de arriba hacia abajo en el mismo orden en que se ejecuta:

| Sección | Funciones | Qué hace |
|---------|-----------|----------|
| Constantes | `LITERAL_TYPES`, `DEFAULTS`, ... | Valores por defecto y claves válidas de `beapi.json`, comentadas. |
| BESSER | `besser()` | Importa una sola vez `abstraction_function` y `eval_bocl_interpreter` (necesitan BESSER y B-OCL). |
| Programa principal | `main()`, `load_model()`, `generate()` | `load_model` lee el modelo y elige su diagrama de clases activo; `generate` recorre los pasos 1/4–4/4. |
| Paso 0 | `write_abstraction()` | Escribe la función de abstracción del modelo (5.1). |
| Pasos 1–2 | `prepare()`, `types_from_abstraction()`, `add_int_date_constructors()`, `default_root()` | Copia y adapta los fuentes y escribe la configuración de BEAPI (5.2). |
| Paso 4 | `run_beapi()` | Arma y ejecuta el comando de BEAPI (5.4). |
| Paso 6 | `write_buml_projects()` y sus funciones | Convierte las estructuras en diagramas de objetos del editor (5.7). |
| Paso 7 | `check_conformance()` | Evalúa los invariantes OCL con `eval_bocl_interpreter.evaluate()` en el mismo proceso (5.8). |
| Utilidades | `parse_args()`, `load_config()`, `find_java8()`, `run()`, ... | Línea de comandos, configuración, Java y archivos. |

---

## 3. Uso rápido

```sh
cd beapi-object-generator

# generar las estructuras de un caso: output/<caso>/<caso>.json
../venv/bin/python beapi_gen.py examples/library/library.json

# además, el proyecto BESSER con las estructuras como diagramas de objetos
../venv/bin/python beapi_gen.py examples/library/library.json --buml

# además, verificar los invariantes OCL del modelo (implica --buml)
../venv/bin/python beapi_gen.py examples/team_ocl/team_ocl.json --conformance

# cambiar el scope o la clase raíz
../venv/bin/python beapi_gen.py examples/school/school.json -s 3 -r Student

# sin volver a correr BEAPI: solo algunas estructuras, un proyecto por estructura
../venv/bin/python beapi_gen.py examples/library/library.json --reuse-json --buml-structures 1,7-8 --buml-split
```

Salida típica (`../venv/bin/python beapi_gen.py examples/team_ocl/team_ocl.json --conformance`):

```
[team_ocl] funcion de abstraccion: examples/team_ocl/team_ocl.json (diagrama de clases 'TeamOCL') -> output/team_ocl/team_ocl.abstraction.json
> Java 8: /usr/lib/jvm/java-8-openjdk-amd64
[team_ocl] 1/4 preparando fuentes y configuracion BEAPI (scope 3)
[team_ocl]     raiz: Team ; otras clases: Player
[team_ocl]     builder: Player.<init>\(java.lang.String,int\)
[team_ocl]     builder: Team.<init>\(java.lang.String,int\)
[team_ocl]     builder: Team.addPlayer\(Player\)
[team_ocl] 2/4 compilando con Java 8
[team_ocl]     verificando las clases Java contra la funcion de abstraccion
[team_ocl] 3/4 ejecutando BEAPI (log: work/team_ocl/beapi.log)
[team_ocl] 4/4 exportando objetos a JSON por reflection (funcion de abstraccion)
[team_ocl] listo: 30 estructuras -> output/team_ocl/team_ocl.json (1.8 s)
[team_ocl] agregando los diagramas de objetos al proyecto BESSER
[team_ocl]     proyecto base: examples/team_ocl/team_ocl.json ; diagrama de clases: 'TeamOCL' ; estructuras: todas (30)
[team_ocl]     30 diagramas de objetos -> output/team_ocl/team_ocl_buml.json
[team_ocl] verificando los invariantes OCL del modelo sobre los diagramas de objetos
[team_ocl]     output/team_ocl/team_ocl_buml.json -> output/team_ocl/team_ocl_buml_conformance.txt
[team_ocl]       Invariantes violados (FALLA):
[team_ocl]         - AdultPlayer: en 22/30 diagrama(s)
[team_ocl]         - TeamNotOverCapacity: en 12/30 diagrama(s)
[team_ocl]       Resumen: 6/30 cumplen, 24 no cumplen, 0 indeterminados (invariantes no evaluables)
```

### Opciones

| Opción | Descripción |
|--------|-------------|
| `MODELO.json` | Modelo B-UML: proyecto exportado del editor web de BESSER (`examples/<caso>/<caso>.json`). El nombre del archivo, sin extensión, es el nombre del caso. |
| `--java-dir DIR` | Clases Java. Por defecto, `<carpeta del modelo>/java`. Útil para probar otra implementación sin tocar el caso. |
| `-s, --scope N` | Scope de BEAPI. Por defecto es 3, o el valor de `beapi.json`. |
| `-r, --root-class C` | Clase raíz: BEAPI serializa solo objetos de esta clase. Por defecto se deduce (ver 5.2). |
| `--timelimit SEG` | Límite de tiempo de BEAPI. Por defecto 36000. |
| `--max-heap 4g` | Heap de la JVM de BEAPI. |
| `-n, --max-structures N` | Exporta al JSON como máximo N estructuras. |
| `--java-home DIR` | JDK 8 que se usa. |
| `-o, --output-dir DIR` | Las salidas van a `DIR/<caso>/`. Por defecto `output/`. |
| `--work-dir DIR` | Los intermedios van a `DIR/<caso>/`. Por defecto `work/`. |
| `--keep-ser` | Copia también el `.ser` a `output/<caso>/<caso>.ser`. |
| `-b, --buml` | Genera también `output/<caso>/<caso>_buml.json`: el modelo con las estructuras agregadas como diagramas de objetos (ver 5.7). `--buml-structures`, `--buml-split` y `--conformance` lo activan solos. |
| `--buml-structures LISTA` | Estructuras a incluir, p.ej. `1,3,5-8`. Son los valores del campo `index` del JSON (desde 1). Por defecto, todas. |
| `--buml-split` | Un proyecto por estructura: `output/<caso>/<caso>_buml_<n>.json`. |
| `--conformance` | Evalúa los invariantes OCL del modelo sobre los diagramas de objetos agregados (ver 5.8). Muestra el resumen y escribe el informe completo en `<proyecto>_conformance.txt` (con `--buml-split`, uno por proyecto). Las violaciones son un resultado: no hacen fallar la ejecución. |
| `--reuse-json` | No ejecuta BEAPI (ni necesita Java): usa el `output/<caso>/<caso>.json` existente. Sirve para volver a armar los diagramas o reevaluar los invariantes después de cambiar el modelo. |

El código de salida es 1 si algún paso falla (modelo inválido, clases que no
corresponden a la abstracción, error de BEAPI, ...) y 0 si no.

---

## 4. Agregar un caso de estudio

El modelo B-UML es la especificación y las clases Java, escritas o modificadas
a mano, son la implementación que se verifica. El script **no genera ni
modifica** los `.java` del caso: trabaja sobre una copia en `work/<caso>/src`
(ver 5.2).

### 4.1 Pasos

**1. Estructura de la carpeta.** Crear `examples/<caso>/` con este contenido:

```
examples/<caso>/
├── <caso>.json      MODELO B-UML ORIGINAL: proyecto exportado del editor web de BESSER
├── <caso>.py        (opcional) el mismo modelo en B-UML Python, si se escribió así
├── beapi.json       (opcional) configuración de BEAPI (sección 6)
└── java/            clases Java SIN anotaciones (respetando la estructura de paquetes)
    ├── ClaseA.java
    └── ClaseB.java
```

- **Dónde va el modelo B-UML original:** en la raíz de la carpeta del caso,
  `examples/<caso>/<caso>.json`. Es el archivo que se pasa a `beapi_gen.py`. Se
  obtiene en el editor web de BESSER exportando el **proyecto** (el `.json` con
  `project.diagrams`). Si el proyecto tiene varios diagramas de clases, se usa
  el activo (`currentDiagramIndices.ClassDiagram`), tanto para la función de
  abstracción como para los diagramas de objetos y los invariantes OCL.
- **El nombre del archivo da nombre al caso:** las salidas van a
  `output/<nombre del archivo sin extensión>/`. Conviene que coincida con el de
  la carpeta.
- Las restricciones OCL que se quieran verificar con `--conformance` deben estar
  **dentro del diagrama de clases** del modelo, como invariantes
  (`context C inv Nombre: ...`).
- Si el modelo se escribió en Python (B-UML), hay que convertirlo a proyecto del
  editor: importándolo en el editor web y exportando el proyecto, o como hace
  `examples/team_ocl/team_ocl.py`, que escribe su propio `.json`.
- Las clases Java van en `examples/<caso>/java/`. Otra carpeta se indica con
  `--java-dir`. `beapi.json` siempre se busca junto al modelo.

**2. Qué deben cumplir las clases Java.** La función de abstracción usa los
mismos nombres que el generador Java de BESSER (`java_template.py.j2`), así que
el código que genera BESSER a partir del modelo cumple todo esto y es un buen
punto de partida. Para ver exactamente qué nombres espera:

```sh
PYTHONPATH=.. ../venv/bin/python abstraction_function.py examples/<caso>/<caso>.json
```

| Elemento del modelo | Lo que debe existir en Java |
|---------------------|-----------------------------|
| Clase `C` | `public class C` (mismo nombre), con al menos un constructor público con parámetros primitivos, `String`, `LocalDate` u otros tipos del modelo. Los constructores con parámetros genéricos (`List<...>`) se ignoran. |
| Enumeración `E` con literal `L` | `public enum E` con la constante `L`. |
| Atributo `a` de `C` | Getter público `getA()` (primera letra en mayúscula, el resto igual: `maxPlayers` → `getMaxPlayers`). |
| Extremo navegable `r` de tipo `T`, múltiple (`*`) | En la clase opuesta: `getR()` que devuelve una colección y `addT(T)` (asociación entre clases distintas) o `addToR(T)` (autoasociación). |
| Extremo navegable `r` de tipo `T`, simple (`0..1`, `1`) | En la clase opuesta: `getR()` y `setR(T)`. |
| Extremo no navegable | Nada (`"java": null` en la abstracción). |

Los valores se leen **solo** con los getters, nunca con los campos. Los
constructores y los métodos `add`/`set` son los builders de BEAPI, así que la
lógica que contengan (validaciones, excepciones) determina qué estados se
generan. En el paso 2/4 se comprueba que exista todo lo de la tabla. Si algo
falta, el script se detiene antes de ejecutar BEAPI e indica qué falta, p.ej.:

```
attribute Student.studentId: Student has no public method getStudentId()
association end Enrollment.students (in Subject): Subject has no public method addStudent(Student)
```

**3. (Opcional) `examples/<caso>/beapi.json`.** Scope, clase raíz y literales
(sección 6). En `enum_literals` los literales van con su nombre B-UML.

**4. Ejecutar** con el entorno virtual de BESSER, desde `beapi-object-generator/`:

```sh
# objetos + proyecto BESSER con los diagramas de objetos
../venv/bin/python beapi_gen.py examples/<caso>/<caso>.json --buml

# además, verificar los invariantes OCL del modelo
../venv/bin/python beapi_gen.py examples/<caso>/<caso>.json --conformance
```

**5. Archivos de salida.** Todo lo que produce el script queda en
`output/<caso>/`; los intermedios, en `work/<caso>/`. `examples/<caso>/` no
se modifica.

```
output/<caso>/
├── <caso>.abstraction.json         función de abstracción del modelo (paso 0)
├── <caso>.json                     estructuras generadas por BEAPI, en términos del modelo (sección 7)
├── <caso>_buml.json                con --buml/--conformance: el modelo + un diagrama de objetos
│                                   "BEAPI structure <n>" por estructura (importable en el editor)
├── <caso>_buml_conformance.txt     con --conformance: informe de los invariantes OCL (5.8)
├── <caso>_buml_<n>.json            con --buml-split: un proyecto por estructura (en lugar de _buml.json)
├── <caso>_buml_<n>_conformance.txt con --buml-split --conformance: un informe por proyecto
└── <caso>.ser                      con --keep-ser: copia de los objetos serializados

work/<caso>/
├── src/                 copia de java/ preparada para BEAPI (Serializable, constructores auxiliares)
├── classes/             clases compiladas con Java 8
├── dump/                BAbstractionDump compilado
├── beapi/               builders.txt, literals.txt, canonicalizer.properties, command.txt
├── beapi.log            salida de BEAPI
└── objects.ser          objetos generados por BEAPI (serializados)
```

Con `-o DIR` las salidas van a `DIR/<caso>/`, y con `--work-dir DIR` los
intermedios van a `DIR/<caso>/`.

### 4.2 Ejecutar el caso de estudio `team_ocl`

`examples/team_ocl/` es el caso mínimo. Tiene dos clases (`Team`, `Player`),
una asociación (`players 0..*`) y dos invariantes OCL (`AdultPlayer`,
`TeamNotOverCapacity`). El modelo y el análisis de los resultados se explican
en 5.9.

```
examples/team_ocl/
├── team_ocl.json        modelo B-UML original (proyecto del editor) -> se pasa a beapi_gen.py
├── team_ocl.py          el mismo modelo en B-UML Python; al ejecutarlo regenera team_ocl.json
├── beapi.json           scope 3, raíz Team, literales int [1, 18] y String ["a"]
└── java/
    ├── Team.java
    └── Player.java
```

**Requisitos:** JDK 8 y el entorno virtual de BESSER con B-OCL (sección 1).

**Ejecución completa** (generación + diagramas de objetos + conformidad OCL):

```sh
cd beapi-object-generator
../venv/bin/python beapi_gen.py examples/team_ocl/team_ocl.json --conformance
```

Desde la raíz del repositorio es lo mismo con las rutas completas:

```sh
venv/bin/python beapi-object-generator/beapi_gen.py \
    beapi-object-generator/examples/team_ocl/team_ocl.json --conformance
```

Tarda unos segundos. Al final la consola muestra el resumen (ver la salida de
la sección 3): `Resumen: 6/30 cumplen, 24 no cumplen, 0 indeterminados`.

**Resultados**, en `beapi-object-generator/output/team_ocl/`:

| Archivo | Qué mirar |
|---------|-----------|
| `team_ocl_buml_conformance.txt` | Resultado de cada invariante (`OK`/`FALLA`/`ERROR`/`OMITIDA`) en cada `BEAPI_structure_<n>`, y el resumen final. |
| `team_ocl_buml.json` | Importarlo como proyecto en el editor web de BESSER para ver los 30 diagramas de objetos `BEAPI structure 1..30`. |
| `team_ocl.json` | Las 30 estructuras de BEAPI (objetos, valores y links). |
| `team_ocl.abstraction.json` | Cómo se relaciona cada elemento del modelo con `Team.java`/`Player.java`. |

**Variantes útiles:**

```sh
# volver a evaluar sin correr BEAPI (p.ej. después de cambiar los invariantes en team_ocl.json)
../venv/bin/python beapi_gen.py examples/team_ocl/team_ocl.json --reuse-json --conformance

# solo algunas estructuras, una por proyecto (un informe por estructura)
../venv/bin/python beapi_gen.py examples/team_ocl/team_ocl.json --reuse-json --conformance \
    --buml-structures 1,13,30 --buml-split

# probar otra implementación sin tocar el ejemplo: copiar java/ a otra carpeta, modificarla y usar --java-dir
cp -r examples/team_ocl/java /tmp/team_ocl_java      # editar Player.java / Team.java
../venv/bin/python beapi_gen.py examples/team_ocl/team_ocl.json --java-dir /tmp/team_ocl_java \
    -o /tmp/team_ocl_out --conformance

# cambiar el modelo desde Python: editar team_ocl.py y regenerar team_ocl.json
PYTHONPATH=.. ../venv/bin/python examples/team_ocl/team_ocl.py
```

Con `--reuse-json` no se ejecuta Java, pero si se cambian las clases o los
literales hay que volver a correr sin esa opción. En el tercer comando, si
`Player(String, int)` rechaza `age < 18` y `addPlayer` rechaza superar
`maxPlayers` (lanzando una excepción), el resultado es `6/6 cumplen` (ver 5.9).

---

## 5. Qué hace el script (paso a paso)

### 5.1 Función de abstracción (paso 0)

`abstraction_function.py` convierte el diagrama de clases activo del modelo a
B-UML (`DomainModel`) con el conversor del editor de BESSER y escribe
`output/<caso>/<caso>.abstraction.json`. Para cada clase, atributo, extremo de
asociación, enumeración y literal registra su id (un UUID derivado del nombre
calificado, estable entre ejecuciones) y cómo se realiza en Java: tipo, campo,
getter y, para los extremos navegables, el `add` o `set` y la clase que lo
contiene. Las reglas replican las de la plantilla del generador Java de BESSER.
Los extremos que ninguna clase realiza (no navegables) quedan con `"java": null`.

`abstraction_function.py` también se puede usar solo; sin `-o` escribe el JSON
en la salida estándar.

### 5.2 Preparación (pasos 1–2: `work/<caso>/src`, `work/<caso>/beapi/`)

Las secciones del informe que se mencionan corresponden a cada ajuste.

| Paso | Detalle | Informe |
|------|---------|---------|
| Copia de fuentes | Solo los `.java` de la carpeta de clases. El original no se toca. | Fase 0.2 |
| Tipos del modelo | Salen de la abstracción. Cada clase y enum de la abstracción debe tener su `.java`. | — |
| `Serializable` | Agrega `implements java.io.Serializable` y `serialVersionUID = 1L` a cada clase del modelo. | Fase 0.3 |
| Constructores auxiliares | Por cada constructor con `LocalDate` agrega otro que recibe la fecha como `int` (días desde 2000-01-01) y llama al original con `this(...)`. No agrega campos ni métodos. | B.2, problema 2.a |
| Builders (`builders.txt`) | Constructores utilizables (en su versión `int` si tenían fecha), el `add` o `set` de cada extremo de asociación de la abstracción (también los heredados de una clase abstracta) y constantes de enum (`Genre:Romance`). No incluye los setters de atributos. | B.3 |
| Literales (`literals.txt`) | Pocos valores por tipo, solo para los tipos que usan los builders (`int` siempre). Por defecto: `int:1`, `long:1`, `float:1.0`, `double:1.0`, `boolean:true`, `String:"a"` y `String:"b"`. | B.4 |
| Canonicalizador (`canonicalizer.properties`) | `max.objects=S`, `max.array.objects=S`, `save.array.null=true`, `omit.fields=modCount|<campos LocalDate>`. | B.5 |
| Clase raíz | Por defecto, la clase concreta desde la que se alcanzan más clases del modelo por extremos de asociación realizados. Si hay empate, la que tiene más extremos. Las demás clases (y los enums) se pasan como `--testclass` extra. | problema 2.c, B.7 |

Avisos de 1/4: si un método `add`/`set` de una subclase **redefine** el de un
extremo de una superclase (p.ej. `Guest.addBooking(Booking)` para `staying` y
`Person.addBooking(Booking)` para `bookings`), en los objetos de la subclase solo
se pueden crear los links del extremo de la subclase. Es una limitación de los
nombres que pone el generador Java (`add<TipoOpuesto>`).

### 5.3 Compilación y verificación (paso 2/4)

Usa `javac` 1.8 (`-source 1.8 -target 1.8 -encoding UTF-8`) y deja las clases
en `work/<caso>/classes`. Si un fuente no es UTF-8 válido, se lee como
ISO-8859-1 y se reescribe en UTF-8 en la copia.

Después compila `tools/BAbstractionDump.java` y ejecuta
`BAbstractionDump verify <caso>.abstraction.json`: comprueba que las clases
compiladas tengan cada clase, constante, getter, `add` y `set` que nombra la
abstracción (sección 4.1, tabla). Si falta algo, se detiene antes de ejecutar
BEAPI.

### 5.4 Ejecución de BEAPI (paso 3/4)

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
  --serialize-objects=work/<caso>/objects.ser
  --omitmethods=".*All\(\.*|toString\(\)|repO[kK]"   <- cubre repOk y repOK
```

El comando completo queda en `work/<caso>/beapi/command.txt` y la salida de
BEAPI en `work/<caso>/beapi.log`.

### 5.5 Por qué hacen falta estos ajustes

Sin ellos BEAPI nunca construye un `Book` (informe, sección 4):

- **LocalDate**: el canonicalizador descarta todo objeto que contiene un
  `LocalDate`. Por eso se agregan los constructores con fecha `int` y se omiten
  los campos de fecha en el canonicalizador. Consecuencia: dos objetos que solo
  difieren en la fecha se consideran el mismo.
- **`--all-sequences=true`**: con `false`, cada iteración combina solo los
  objetos nuevos de la iteración anterior. Así nunca se juntan un `Book` y una
  `Library` ya construidos en `addLibrary(Library)`, y no aparecen links. Por
  eso es fijo (ya no hay opción para cambiarlo).

### 5.6 Exportación a JSON (paso 4/4)

`BAbstractionDump dump <caso>.abstraction.json objects.ser` lee el `.ser` con
`readObject()` hasta EOF. Recorre cada grafo desde la raíz por reflection,
**solo** con los getters de la abstracción, y lo escribe en términos del
modelo: clases, atributos y asociaciones B-UML, con los ids de la abstracción.
El script agrega metadatos y escribe `output/<caso>/<caso>.json` (sección 7).

### 5.7 Proyecto BESSER (`--buml`, paso 6)

El proyecto que exporta el editor web de BESSER guarda varios diagramas por
tipo: `project.diagrams.ClassDiagram` y `project.diagrams.ObjectDiagram` son
listas. Con `--buml` el script copia **el propio modelo** y agrega al final de
`ObjectDiagram` un diagrama por estructura seleccionada, titulado
`BEAPI structure <n>`. Los diagramas de objetos que ya tenía el modelo se
conservan. La copia recibe un `id` nuevo y el nombre `<proyecto>_beapi`, para
que no choque con el original al importarla.

Los diagramas de objetos referencian el **diagrama de clases activo** del
modelo, el mismo del que sale la función de abstracción: cada uno lleva
`references.ClassDiagram` con su id y una copia del modelo de clases en
`referenceDiagramData`, como los que crea el editor.

**El formato no es el mismo que el JSON de BEAPI**, así que se convierte:

| JSON de BEAPI | Diagrama de objetos de BESSER |
|---------------|-------------------------------|
| `classId` = id de la abstracción | `classId` = id del elemento `Class` en el diagrama del editor |
| atributo `{name, type, value}` | elemento `ObjectAttribute` con `name: "pages = 1"` y `attributeId` |
| enum `{enumeration, literal}` | `"genre = Romance"` |
| link `{association, sourceEnd, targetEnd}` | `ObjectLink` con `associationId` = id de la relación del editor |
| (no tiene) | `bounds` de objetos y atributos, `path` de los links |

Los ids de la abstracción no coinciden con los del editor. Por eso la
conversión resuelve por nombre:

- **Clase** por su nombre. Los atributos se ordenan como en el diagrama de
  clases, incluidos los heredados (`ClassInheritance`).
- **Asociación** por los roles de sus extremos, no por su nombre. En el
  diagrama "Library with OCL" las dos relaciones se llaman `books`. Un rol
  vacío equivale al nombre de la clase en minúscula, como en BESSER. El source y
  el target del `ObjectLink` siguen la orientación de la relación del
  diagrama de clases. El link se nombra con la asociación B-UML (`books`,
  `books_1`).

Los objetos se llaman `book1`, `author1`, `author2`, ... y se disponen en
columnas según su distancia (en links) a la raíz.

**¿Un archivo o uno por diagrama?** Pueden ir todos en un solo proyecto. El
conversor de BESSER procesa todos los diagramas de objetos y genera un
`ObjectModel` por cada uno. La desventaja es el tamaño: cada diagrama incluye
una copia del diagrama de clases (las 1053 estructuras de `library` ocupan
~65 MB). Con muchas estructuras conviene elegir algunas con
`--buml-structures`, o usar `--buml-split` para obtener un proyecto por
estructura.

### 5.8 Conformidad OCL (`--conformance`, paso 7)

Objetivo: verificar si los estados que el código Java permite construir,
vistos a través de la función de abstracción, **conforman al modelo B-UML**, es
decir, cumplen sus invariantes OCL. Las clases Java no se generan a partir del
modelo: son las del caso, eventualmente escritas o modificadas a mano, y son
justamente lo que se verifica.

Procedimiento completo de `beapi_gen.py MODELO.json --conformance`:

1. **Función de abstracción** (5.1): `output/<caso>/<caso>.abstraction.json`.
2. **Preparación y verificación de las clases** (5.2, 5.3): copia las clases a
   `work/<caso>/src`, arma la configuración de BEAPI a partir de la
   abstracción, compila con Java 8 y comprueba que las clases tengan todo lo
   que nombra la abstracción.
3. **Generación** (5.4): BEAPI construye en forma *bounded-exhaustive* todos los
   objetos de la clase raíz que se obtienen con los builders dentro del scope, y
   los serializa en `work/<caso>/objects.ser`.
4. **Abstracción de los objetos** (5.6): cada estructura se recorre **solo** con
   los getters de la abstracción y queda en `output/<caso>/<caso>.json`.
5. **Diagramas de objetos** (5.7): cada estructura se agrega como diagrama de
   objetos `BEAPI structure <n>` a una copia del modelo,
   `output/<caso>/<caso>_buml.json`.
6. **Evaluación OCL**: `check_conformance()` llama, en el mismo proceso, a
   `eval_bocl_interpreter.evaluate(diagrama de clases, diagramas de objetos)`
   con los diagramas agregados por BEAPI (los que ya traía el modelo no se
   evalúan). Para cada diagrama de objetos, convierte el diagrama de clases y el
   de objetos a B-UML (`DomainModel` y `ObjectModel`) y evalúa con B-OCL cada
   invariante (`inv`) del modelo. Las pre/postcondiciones no se evalúan. El
   informe completo queda en `output/<caso>/<caso>_buml_conformance.txt`, y en
   la consola se muestra su bloque final.

Resultado de cada invariante en cada diagrama:

| Resultado | Significado |
|-----------|-------------|
| `OK` | Se cumple. |
| `FALLA` | El evaluador devolvió falso: el diagrama **viola** el invariante. |
| `ERROR` | B-OCL no pudo evaluarlo (expresión no soportada, error interno, ...). No se sabe si se cumple y **no** se cuenta como violación. |
| `OMITIDA` | No hay instancias de la clase de contexto: se cumple trivialmente. |

Resultado de cada diagrama de objetos: **CUMPLE** (todos `OK` u `OMITIDA`),
**NO CUMPLE** (al menos una `FALLA`) o **INDETERMINADO** (ninguna `FALLA`, pero
al menos un `ERROR`). El resumen final lista los invariantes violados y los no
evaluables (con el primer mensaje de error) y cuenta los diagramas de cada tipo:

```
Invariantes violados (FALLA):
  - AdultPlayer: en 22/30 diagrama(s)
  - TeamNotOverCapacity: en 12/30 diagrama(s)
Resumen: 6/30 cumplen, 24 no cumplen, 0 indeterminados (invariantes no evaluables)
```

Un `ERROR` indica una limitación del evaluador, no del modelo ni del código.
Por ejemplo, en `nuevo_booking` B-OCL no acepta la sintaxis de
`NoRoomDoubleBooking` y en `NumberOfGuestsDoesNotExceedRoomCapacity` evalúa `r`
dentro de `collect(r | r.max_people)` como si fuera un `Booking`. Por eso sus
152 diagramas quedan INDETERMINADOS.

`beapi_gen.py` termina con código 0 aunque haya violaciones: son un resultado,
no un error de ejecución.

`eval_bocl_interpreter.py` también se puede usar solo, sobre cualquier
proyecto BESSER con diagramas de objetos:

```sh
PYTHONPATH=.. ../venv/bin/python eval_bocl_interpreter.py PROYECTO.json \
    [-c "TITULO DEL DIAGRAMA DE CLASES"] [-p "PREFIJO DEL TITULO"]
```

Sin `-c` usa el diagrama de clases activo del proyecto; sin `-p` evalúa todos los
diagramas de objetos (con `-p "BEAPI structure "`, solo los generados). Código
de salida: 0 todos cumplen, 1 alguno no cumple, 3 ninguno viola un invariante
pero hay indeterminados, 2 error de uso.

Lo que esta verificación **no** cubre: multiplicidades, consistencia de los
extremos opuestos de asociaciones bidireccionales y composición. Esos aspectos
solo se controlan si se escriben como invariantes OCL en el modelo.

### 5.9 Ejemplo: conformidad OCL con un modelo mínimo (`examples/team_ocl/`)

Un modelo con dos clases, una asociación y dos invariantes OCL:

```
Team (name: str, maxPlayers: int)  --players 0..*-->  Player (name: str, age: int)

context Player inv AdultPlayer:         self.age >= 18
context Team   inv TeamNotOverCapacity: self.players->size() <= self.maxPlayers
```

Archivos del ejemplo:

| Archivo | Contenido |
|---------|-----------|
| `team_ocl.py` | El modelo en B-UML (Python): clases, asociación unidireccional `team_players` y los dos `Constraint`. Al ejecutarlo escribe `team_ocl.json`. |
| `team_ocl.json` | El modelo B-UML original, como proyecto del editor web de BESSER: es el que se pasa a `beapi_gen.py` y la base de `--buml`. También se puede crear dibujando el diagrama en el editor y exportando el proyecto. |
| `java/Team.java`, `java/Player.java` | Las implementaciones Java, sin anotaciones: constructores `Team(String, int)` y `Player(String, int)`, getters y setters, `getPlayers()` y `addPlayer(Player)`. |
| `beapi.json` | Scope 3, raíz `Team` y literales `int: [1, 18]`, `String: ["a"]`, para que haya jugadores menores (`age = 1`) y equipos con `maxPlayers = 1`. |

Cómo ejecutarlo: ver 4.2.

La función de abstracción relaciona el extremo `players` con
`Team.getPlayers()`/`Team.addPlayer(Player)`. El extremo `team` no es navegable
y por eso ninguna clase Java lo realiza (`"java": null`). Los builders de BEAPI
son los dos constructores y `addPlayer` (ver la salida de la sección 3).

Las 30 estructuras son un equipo con `maxPlayers` 1 o 18 y de 0 a 3 jugadores de
edad 1 o 18. Cumplen las 6 que no tienen jugadores de edad 1 y no superan
`maxPlayers`: el equipo vacío (2), un jugador de 18 (2), dos jugadores de 18
con `maxPlayers = 18` (1) y tres jugadores de 18 con `maxPlayers = 18` (1). Por
ejemplo, en `team_ocl_buml_conformance.txt`:

```
=== Modelo de objetos: BEAPI_structure_13 ===
Objetos: a:Player, a:Team, a:Player
  Evaluando [AdultPlayer] context Player inv AdultPlayer: self.age >= 18
    -> OK
  Evaluando [TeamNotOverCapacity] context Team inv TeamNotOverCapacity: self.players->size() <= self.maxPlayers
    -> FALLA
Resultado BEAPI_structure_13: NO CUMPLE (1 violada(s))
```

Es decir, `Team.addPlayer` permite agregar más jugadores que `maxPlayers` y los
constructores aceptan cualquier edad: el código no garantiza los invariantes. Si
se agrega la validación correspondiente (que `Player(String, int)` lance
`IllegalArgumentException` si `age < 18` y que `addPlayer` lance una excepción si
el equipo ya tiene `maxPlayers` jugadores), BEAPI descarta esas secuencias y
quedan 6 estructuras, todas conformes (`Resumen: 6/6 cumplen`). Para probarlo
sin tocar el ejemplo, se pueden copiar las clases modificadas a otra carpeta y
pasarla con `--java-dir`. Así se comprueba si una implementación respeta el
modelo.

---

## 6. Configuración por caso: `beapi.json`

Es un archivo opcional junto al modelo (`examples/<caso>/beapi.json`). Todas
las claves son opcionales, y las opciones de línea de comandos tienen prioridad
sobre el archivo. Una clave desconocida es un error.

```json
{
  "description": "texto libre",
  "scope": 3,
  "root_class": "Library",
  "literals": {"int": [1], "String": ["a"], "float": [1.0]},
  "enum_literals": {"Genre": ["Romance", "Horror"]},
  "extra_builders": [],
  "exclude_builders": [],
  "builders": null,
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
| `enum_literals` | Un número N (los primeros N literales de cada enum, en el orden de declaración en Java; por defecto 2) o un objeto `{enum: [literales B-UML]}`. |
| `builders` | Si se define, **reemplaza** la lista deducida de la abstracción. Usa el formato regex de BEAPI, p.ej. `"Book.addAuthor\\(Author\\)"`. |
| `extra_builders` | Builders que se agregan a los deducidos. |
| `exclude_builders` | Expresiones regulares: se quitan los builders que coinciden. |
| `max_structures` | Límite de estructuras exportadas al JSON. |

> **Tamaño del espacio de búsqueda.** Cada literal extra multiplica todas las
> combinaciones de los parámetros de cada constructor (`Book` tiene 6
> parámetros), y cada `add`/`set` de una asociación bidireccional suma
> builders en los dos extremos. Conviene subir el scope y agregar valores de a
> uno y medir.

---

## 7. Formato del JSON de salida

`output/<caso>/<caso>.json` (ejemplo real de `team_ocl`, abreviado):

```json
{
  "example": "team_ocl",
  "generator": "BEAPI",
  "generatedAt": "2026-11-12T22:43:17",
  "model": "TeamOCL",
  "rootClass": "Team",
  "scope": 3,
  "structureCount": 30,
  "abstractionFile": "output/team_ocl/team_ocl.abstraction.json",
  "javaDir": "examples/team_ocl/java",
  "beapi": {
    "seconds": 0.37,
    "testClasses": ["Team", "Player"],
    "builders": ["Player.<init>\\(java.lang.String,int\\)", "Team.<init>\\(java.lang.String,int\\)",
                 "Team.addPlayer\\(Player\\)"],
    "literalsFile": "work/team_ocl/beapi/literals.txt",
    "canonicalizerFile": "work/team_ocl/beapi/canonicalizer.properties",
    "omittedFields": ["modCount"],
    "serializedObjects": "work/team_ocl/objects.ser"
  },
  "structures": [
    {
      "index": 3,
      "model": "TeamOCL",
      "root": "o1",
      "objects": [
        {"id": "o1", "class": "Team", "classId": "147e77f6-...",
         "attributes": [
           {"id": "d5246785-...", "name": "maxPlayers", "type": "int", "value": 1},
           {"id": "6ee3d737-...", "name": "name", "type": "str", "value": "a"}]},
        {"id": "o2", "class": "Player", "classId": "81cd7bd2-...",
         "attributes": [
           {"id": "87c9f3f2-...", "name": "age", "type": "int", "value": 1},
           {"id": "817a5e4f-...", "name": "name", "type": "str", "value": "a"}]}
      ],
      "links": [
        {
          "associationId": "7de9a508-...", "association": "team_players",
          "source": "o1", "sourceClass": "Team",
          "sourceEndId": "cf418f6a-...", "sourceEnd": "players",
          "sourceEndLower": 0, "sourceEndUpper": -1,
          "target": "o2", "targetClass": "Player", "targetEnd": "team"
        }
      ]
    }
  ]
}
```

- Cada elemento de `structures` es un diagrama de objetos: un objeto raíz
  serializado por BEAPI y todo lo que alcanza.
- `index` numera las estructuras desde 1, en el orden del `.ser`. Es el número
  que se usa en `--buml-structures`.
- Los `id`, `classId`, `associationId` y `sourceEndId` son los ids de la
  función de abstracción y sirven como trazabilidad hacia el modelo B-UML.
- En cada link, `sourceEnd` es el extremo por el que se navega desde `source`
  hasta `target` (de tipo `targetClass`); `targetEnd`, el extremo opuesto.
  `sourceEndUpper = -1` significa `*`.
- Los links se deduplican por (asociación, par de objetos).
- Las fechas se exportan en formato ISO y los enums como `{enumeration, literal}`.

---

## 8. Resultados de referencia (Java 8)

Cada caso se corrió con su `beapi.json` actual
(`../venv/bin/python beapi_gen.py examples/<caso>/<caso>.json --conformance`).

| Caso | Scope | Raíz | Estructuras | Links que aparecen | BEAPI | Conformidad OCL |
|------|-------|------|-------------|--------------------|-------|-----------------|
| `team_ocl` | 3 | Team | 30 | `team_players` | <1 s | 6 cumplen, 24 no cumplen |
| `school` | 4 | Student | 54 | `Enrollment`, `StudentExams`, `SubjectExams` | ~3 s | 1 cumple, 53 no cumplen |
| `hospital` | 3 | Doctor | 10 | `DoctorAppointments`, `AppointmentRecord`, `Patient_Doctor`, `PatientAppointments` | ~13 s | 1 cumple, 9 no cumplen |
| `library` | 3 | Library | 1053 | `books` (Library–Book) | ~240 s | 972 cumplen, 81 no cumplen (`library_has_books`) |
| `nuevo_booking` | 3 | Booking | 152 | `Booking_Invoice`, `Booking_Person`, `Room_Booking` | ~16 s | 152 indeterminados (5.8) |

Observaciones:

- `hospital` con scope 4 no termina en un tiempo razonable (más de 5 millones
  de secuencias): cada asociación bidireccional aporta builders en sus dos
  extremos.
- `library` con scope 2 no genera ningún link: cada extremo múltiple es una
  `ArrayList`, que también cuenta para el scope (ver 9). Con scope 3 aparecen
  los links `books`; los de `books_1` (Author–Book) necesitan un scope mayor.
- En `school` y `hospital`, varios invariantes dan `ERROR` en algunos diagramas
  por expresiones que B-OCL no acepta (`SyntaxError`); ver el informe de cada
  caso.

---

## 9. Limitaciones y consejos

- **Explosión combinatoria**: subir el scope o agregar literales hace crecer
  el espacio muy rápido. Para diagramas conviene scope 2–3 con dominios
  mínimos.
- **Scope y listas**: el canonicalizador de BEAPI limita la cantidad de objetos
  de **cada** clase, incluida `java.util.ArrayList`. Cada extremo múltiple es
  una lista, así que con scope 2 un objeto que ya tiene 2 listas no puede
  enlazarse por un tercer extremo múltiple. En `nuevo_booking`, con scope 2
  solo hay links `Booking_Invoice`; con scope 3 aparecen también
  `Booking_Person` y `Room_Booking`; los links `Booking_Guest` necesitan un
  scope mayor.
- **Fechas**: los campos `LocalDate` no se canonicalizan. Conviene un único
  valor (`int: [1]`); si no, las variantes que solo cambian la fecha se
  descartan como repetidas. Solo se trata `java.time.LocalDate`; otros tipos de
  fecha (`Date`, `LocalDateTime`) no tienen soporte.
- **Asociaciones bidireccionales**: los `add`/`set` que genera BESSER no
  actualizan el extremo opuesto. BEAPI puede generar grafos inconsistentes, por
  ejemplo un libro en `l.getBooks()` cuyo `getLibrary()` no incluye a `l`. La
  verificación OCL no lo detecta salvo que haya un invariante que lo exprese.
- **Duplicados**: las listas permiten agregar el mismo objeto dos veces. El
  JSON deduplica los links.
- **Análisis de fuentes**: la declaración de las clases y los constructores se
  detectan con expresiones regulares. Funciona con código como el que genera
  BESSER. Con código más complejo, revisar `work/<caso>/beapi/builders.txt` y,
  si hace falta, fijar la lista con `builders` en `beapi.json`.
- **repOk**: BEAPI lo ignora (`--omitmethods`). Para quedarse solo con los
  objetos válidos de un modelo con repOk, hay que expresarlo como invariante
  OCL y usar `--conformance`, o filtrar el JSON después.
- **Nombres de objetos en BESSER**: al convertir a B-UML, BESSER renombra los
  objetos de las clases que tienen un atributo `name` con el valor de ese
  atributo. Con los literales mínimos, todos quedan como `a` (se ve en los
  informes de conformidad). En el editor se ven `book1`, `author1`, etc.

---

## 10. Cambios respecto de la versión con anotaciones

Versiones anteriores del generador leían la relación modelo ↔ Java de
anotaciones en los `.java` (`@BClass`, `@BAttribute`, `@BAssociationEnd`,
`@BEnumeration`, `@BLiteral`). Ese modo se eliminó: la función de abstracción
lo reemplaza. En concreto:

- Ya no existen `tools/BObjectDump.java`, `support/besser/trace/` ni las
  carpetas `besser/trace/` de los ejemplos.
- La línea de comandos recibe el modelo (`beapi_gen.py examples/<caso>/<caso>.json`)
  en lugar de nombres de ejemplos; se quitaron `-m/--model`, `-l`,
  `--examples-dir`, `--buml-base`, `--buml-class-diagram` y
  `--all-sequences`/`--no-all-sequences`.
- Los casos `hospital`, `school` y `library` (antes `library_without_repok`)
  se migraron al formato de 4.1: el proyecto que estaba en `buml_model/` pasó a
  `<caso>.json` y las clases, a `java/`. Las clases anotadas venían de una
  versión anterior del generador Java de BESSER (otros nombres de getters, como
  `getStudentid`, y cada asociación realizada en un solo extremo) y no tenían
  lógica propia, así que se reemplazaron por las que genera el generador
  actual a partir del mismo modelo. Por eso cambian las estructuras y los
  scopes respecto de las versiones anteriores (sección 8).
- Se eliminaron `library_with_repok` (no tenía modelo B-UML) y `generico` (no
  tenía clases Java), que no se podían ejecutar en este modo.

Para migrar otro caso con anotaciones: exportar su proyecto del editor a
`examples/<caso>/<caso>.json`, mover las clases a `java/`, quitar las
anotaciones y `import besser.trace.*`, y ajustar los nombres que indique el
paso de verificación (o regenerar las clases con el generador Java de BESSER).
