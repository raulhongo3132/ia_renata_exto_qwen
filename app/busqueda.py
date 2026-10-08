"""Búsqueda de casos parecidos en la BC (código, sin IA)."""
import math
import re
import sqlite3
import unicodedata
from collections import Counter
from contextlib import closing

PREFIJO = 6          # raíz cruda: primeras 6 letras (internet/internas ~ "intern")
BONO_SUCURSAL = 0.15
BONO_TIPO = 0.20
PENAL_MEDIA = 0.05
MIN_COBERTURA = 0.10

STOPWORDS = {
    "los", "las", "del", "con", "para", "por", "una", "uno", "unos", "unas",
    "que", "como", "pero", "sin", "hay", "desde", "hasta", "cuando", "porque",
    "esta", "este", "esto", "estan", "estamos", "ese", "esa", "son", "fue",
    "ser", "sus", "nos", "les", "muy", "mas", "tiene", "tienen", "tambien",
    "todo", "toda", "todos", "todas", "hoy", "ayer", "favor", "sigue",
    "sucursal", "desconocido", "solo", "algo", "otra", "otro", "cada",
    "manana", "temprano", "tarde", "noche", "hora", "horas", "dia", "dias",
    "urgente", "ahora", "momento",
}


def sin_acentos(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokens(texto):
    t = sin_acentos(texto or "").lower()
    salida = []
    for w in re.findall(r"[a-z0-9]+", t):
        if len(w) < 3 or w in STOPWORDS:
            continue
        salida.append(w[:PREFIJO])
    return salida


def buscar_casos(db_path, descripcion, sucursal_clave=None, tipo=None, k=3):
    """Devuelve hasta k casos de la BC, ordenados por puntaje (mayor primero)."""
    consulta = set(tokens(descripcion))
    if not consulta:
        return []

    with closing(sqlite3.connect(db_path)) as con:
        con.row_factory = sqlite3.Row
        filas = con.execute(
            """SELECT id, sucursal, tipo, prioridad, descripcion, causa,
                      solucion, confiabilidad
               FROM casos_bc WHERE confiabilidad != 'baja'""").fetchall()
    if not filas:
        return []

    docs = [(f, set(tokens(f["descripcion"] + " " + (f["causa"] or ""))))
            for f in filas]
    df = Counter()
    for _, t in docs:
        df.update(t)
    n = len(docs)

    def idf(w):
        return math.log((n + 1) / (df.get(w, 0) + 1)) + 1

    total = sum(idf(w) for w in consulta)
    resultados = []
    for f, t in docs:
        comunes = consulta & t
        if not comunes:
            continue
        cobertura = sum(idf(w) for w in comunes) / total
        if cobertura < MIN_COBERTURA:
            continue
        puntaje = cobertura
        if sucursal_clave and f["sucursal"] == sucursal_clave:
            puntaje += BONO_SUCURSAL
        if tipo and f["tipo"] == tipo:
            puntaje += BONO_TIPO
        if f["confiabilidad"] == "media":
            puntaje -= PENAL_MEDIA
        d = dict(f)
        d["puntaje"] = round(puntaje, 3)
        d["cobertura"] = round(cobertura, 3)
        d["palabras_comunes"] = sorted(comunes)
        resultados.append(d)

    resultados.sort(key=lambda d: (-d["puntaje"], d["id"]))
    return resultados[:k]
