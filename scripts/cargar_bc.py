import json
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

MD_DIR = Path("historicos/md")
DB = Path("data/tecnoserv.db")

SUCURSALES = {
    "centro", "norte", "sur", "oriente", "poniente", "aeropuerto", "puerto",
    "industrial", "universidad", "reforma", "lomas", "valle", "mirador",
    "plaza mayor", "terminal", "estacion", "parque", "hospital", "zona rosa",
    "muelle",
}
TIPOS = {"red", "servidor", "aplicacion", "otro"}
PRIORIDADES = {"baja", "media", "alta", "critica"}
VACIOS = {"", "n/d", "nd", "n/a", "na", "-", "--", "ninguno", "ninguna",
          "sin dato", "desconocido"}

ETIQUETAS = {
    "id": "id",
    "fecha": "fecha",
    "sucursal": "sucursal",
    "reportado por": "reportado_por",
    "tipo": "tipo",
    "prioridad": "prioridad",
    "descripcion del problema": "descripcion",
    "causa encontrada": "causa",
    "solucion aplicada": "solucion",
    "tecnico": "tecnico",
    "tiempo de resolucion": "tiempo",
}
NUCLEO = ["descripcion", "tipo", "solucion"]
SECUNDARIOS = ["fecha", "sucursal", "reportado_por", "prioridad",
               "causa", "tecnico", "tiempo"]


def sin_acentos(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def limpiar(valor):
    """Devuelve texto limpio o None si el valor es vacío/N/D."""
    if valor is None:
        return None
    v = re.sub(r"\s+", " ", valor.replace("**", "").replace("\\", "")).strip()
    return None if sin_acentos(v).lower() in VACIOS else v


ADVERTENCIAS = []  # grupos de etiquetas cuyos valores no coincidieron


def es_pie(linea):
    t = sin_acentos(linea).lower()
    return bool(re.match(r"^(reporte\s+rep-\d+|pagina\s+\d+)", t))


def etiqueta_de(linea):
    t = sin_acentos(linea).lower().strip().rstrip(":").strip()
    return ETIQUETAS.get(t)


def parsear(texto, nombre="?"):
    """Formato en bloques: etiquetas en una línea, valores en las siguientes.
    Varias etiquetas seguidas forman un grupo; sus valores se asignan por
    posición solo si el conteo coincide."""
    lineas = [l.replace("**", "").lstrip("#").strip() for l in texto.splitlines()]
    lineas = [l for l in lineas if l]
    campos, i, n = {}, 0, len(lineas)

    while i < n:
        if es_pie(lineas[i]) or not etiqueta_de(lineas[i]):
            i += 1  # título, subtítulo, pie o texto suelto
            continue
        grupo = []
        while i < n and etiqueta_de(lineas[i]):
            grupo.append(etiqueta_de(lineas[i]))
            i += 1
        valores = []
        while i < n and not etiqueta_de(lineas[i]) and not es_pie(lineas[i]):
            valores.append(lineas[i])
            i += 1

        if len(grupo) == 1:
            campos[grupo[0]] = " ".join(valores)
        elif len(valores) == len(grupo):
            for k, v in zip(grupo, valores):
                campos[k] = v
        else:
            ADVERTENCIAS.append((nombre, grupo, len(valores)))
    return campos

def normalizar(campos):
    r = {k: limpiar(campos.get(k)) for k in list(ETIQUETAS.values())}
    # Catálogos: lo que no pertenece al catálogo cuenta como faltante
    if r["tipo"] and sin_acentos(r["tipo"]).lower() not in TIPOS:
        r["tipo"] = None
    elif r["tipo"]:
        r["tipo"] = sin_acentos(r["tipo"]).lower()
    if r["prioridad"] and sin_acentos(r["prioridad"]).lower() not in PRIORIDADES:
        r["prioridad"] = None
    elif r["prioridad"]:
        r["prioridad"] = sin_acentos(r["prioridad"]).lower()
    if r["sucursal"]:
        s = re.sub(r"^sucursal\s+", "", sin_acentos(r["sucursal"]).lower())
        r["sucursal"] = s if s in SUCURSALES else None
    if r["fecha"]:
        try:
            datetime.strptime(r["fecha"], "%Y-%m-%d")
        except ValueError:
            r["fecha"] = None
    if r["descripcion"] and len(r["descripcion"]) < 10:
        r["descripcion"] = None
    return r


def crear_tablas(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS casos_bc (
        id TEXT PRIMARY KEY,
        origen TEXT NOT NULL,            -- 'historico' o 'ticket'
        archivo_md TEXT,
        fecha TEXT, sucursal TEXT, tipo TEXT, prioridad TEXT,
        descripcion TEXT NOT NULL,
        causa TEXT, solucion TEXT NOT NULL,
        tecnico TEXT, tiempo TEXT, reportado_por TEXT,
        confiabilidad TEXT NOT NULL,     -- alta | media | baja
        campos_faltantes TEXT NOT NULL,  -- lista JSON
        ficticio INTEGER NOT NULL DEFAULT 1,
        fecha_carga TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bc_descartados (
        archivo TEXT PRIMARY KEY,
        motivo TEXT NOT NULL
    );
    """)


def main():
    DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    crear_tablas(con)
    con.execute("DELETE FROM bc_descartados")
    con.execute("DELETE FROM casos_bc WHERE origen = 'historico'")

    ahora = datetime.now().isoformat(timespec="seconds")
    cuenta_conf, cuenta_tipo, descartados = Counter(), Counter(), []

    for md in sorted(MD_DIR.glob("REP-*.md")):
        r = normalizar(parsear(md.read_text(encoding="utf-8"), md.name))
        falta_nucleo = [c for c in NUCLEO if not r[c]]
        if falta_nucleo:
            motivo = "falta núcleo: " + ", ".join(falta_nucleo)
            con.execute("INSERT OR REPLACE INTO bc_descartados VALUES (?, ?)",
                        (md.name, motivo))
            descartados.append((md.name, motivo))
            continue

        faltantes = [c for c in SECUNDARIOS if not r[c]]
        n = len(faltantes)
        conf = "alta" if n == 0 else "media" if n <= 2 else "baja"

        valores = {k: (r[k] or "desconocido") for k in SECUNDARIOS}
        con.execute("""
            INSERT OR REPLACE INTO casos_bc
            (id, origen, archivo_md, fecha, sucursal, tipo, prioridad,
             descripcion, causa, solucion, tecnico, tiempo, reportado_por,
             confiabilidad, campos_faltantes, ficticio, fecha_carga)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
            (md.stem, "historico", md.name, valores["fecha"],
             valores["sucursal"], r["tipo"], valores["prioridad"],
             r["descripcion"], valores["causa"], r["solucion"],
             valores["tecnico"], valores["tiempo"], valores["reportado_por"],
             conf, json.dumps(faltantes, ensure_ascii=False), ahora))
        cuenta_conf[conf] += 1
        cuenta_tipo[r["tipo"]] += 1

    con.commit()
    con.close()

    print(f"Cargados: {sum(cuenta_conf.values())}")
    print(f"Por confiabilidad: {dict(cuenta_conf)}")
    print(f"Por tipo: {dict(cuenta_tipo)}")
    print(f"Descartados: {len(descartados)}")
    print(f"Grupos ambiguos (valores != etiquetas): {len(ADVERTENCIAS)}")
    for nombre, grupo, nval in ADVERTENCIAS[:10]:
       print(f"  {nombre}: etiquetas {grupo} con {nval} valores")
    for nombre, motivo in descartados[:10]:
        print(f"  {nombre}: {motivo}")


if __name__ == "__main__":
    main()
