"""Validación de campos, reglas de producción y confianza (código, sin IA)."""
import re
import unicodedata
from esquema import TIPOS

ORDEN = ["baja", "media", "alta", "critica"]


def norm(s):
    n = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()


# ---------- Paso 3 del diseño: validar campos y detectar faltantes ----------
def validar_ticket(f):
    """Devuelve (errores, faltantes). Los errores bloquean; los faltantes informan."""
    errores, faltantes = [], []
    titulo = (f.get("titulo") or "").strip()
    desc = (f.get("descripcion_libre") or "").strip()
    if not titulo:
        errores.append("El título es obligatorio.")
    elif len(titulo) > 120:
        errores.append("El título no puede pasar de 120 caracteres.")
    if len(desc) < 15:
        errores.append("La descripción es obligatoria (mínimo 15 caracteres).")
    elif len(desc) > 2000:
        errores.append("La descripción no puede pasar de 2000 caracteres.")
    if not (f.get("contacto") or "").strip():
        errores.append("El contacto es obligatorio.")
    cat = f.get("categoria_declarada")
    if cat and cat not in TIPOS:
        errores.append("Categoría no válida.")
    if not (f.get("equipo_afectado") or "").strip():
        faltantes.append("equipo_afectado")
    if 15 <= len(desc) < 40:
        faltantes.append("descripcion_breve")
    return errores, faltantes


# ---------- Reglas de producción ----------
FALLA = [r"\bno (hay|funciona|funcionan|responde|responden|abre|abren|entra|entran|"
         r"puede|pueden|podemos|puedo|conecta|conectan|carga|cargan|enciende)",
         r"\bcaid[oa]s?\b", r"\bsin\b", r"\bfall(a|o|ando|aron)\b", r"apagad"]

REGLAS = [  # (id, prioridad, descripción, [grupos]); grupos = AND, patrones = OR
    ("R1", "critica", "posible incidente de seguridad",
     [[r"ransomware", r"malware", r"\bvirus\b", r"hackeo|hackearon|hackeado",
       r"archivos? cifrados?", r"secuestr"]]),
    ("R2", "critica", "toda la sucursal sin servicio",
     [[r"toda la sucursal", r"toda la tienda", r"todas las cajas",
       r"todos los equipos", r"nadie (puede|tiene|logra)"], FALLA]),
    ("R3", "alta", "servidor caído o sin respuesta",
     [[r"servidor(es)?", r"\bserver\b"], FALLA]),
    ("R4", "alta", "punto de venta o cajas afectadas",
     [[r"\bcajas?\b", r"punto de venta", r"\bpos\b", r"\bpdv\b",
       r"terminal de cobro"], FALLA]),
    ("R5", "alta", "posible pérdida de datos o respaldo fallido",
     [[r"perdimos|perdieron|se perdio|perdida de (datos|informacion)",
       r"respaldos? (fallo|fallido|no)"]]),
]


def _hay(texto, patrones):
    return any(re.search(p, texto) for p in patrones)


def calcular_prioridad(texto, sugerida):
    t = norm(texto)
    disparadas = [(i, p, d) for i, p, d, grupos in REGLAS
                  if all(_hay(t, g) for g in grupos)]
    sug = sugerida if sugerida in ORDEN else None
    if disparadas:
        i, final, d = max(disparadas, key=lambda x: ORDEN.index(x[1]))
        regla = f"{i}: {d}"
    elif sug:
        final = "media" if sug in ("alta", "critica") else sug
        regla = "R8: sin regla de negocio; se acepta la sugerencia del modelo (tope: media)"
    else:
        final, regla = "media", "R9: sin regla ni sugerencia válida; prioridad por defecto"
    contradice = sug is not None and sug != final
    if contradice:
        regla += f" [el modelo sugirió {sug}]"
    return {"prioridad_final": final, "regla_aplicada": regla,
            "ids_reglas": [x[0] for x in disparadas],
            "contradice_modelo": contradice}


# ---------- Confianza calculada (heurística, NO calibrada) ----------
def calcular_confianza(json_valido, casos, tipo_llm, categoria, n_faltantes):
    if not json_valido:
        return 0.0
    c = 0.30
    if casos:
        c += 0.30 * min(1.0, casos[0]["cobertura"])
        if tipo_llm == casos[0]["tipo"]:
            c += 0.20
    c += (0.20 if tipo_llm == categoria else 0.0) if categoria else 0.10
    c -= min(0.30, 0.10 * n_faltantes)
    return round(max(0.0, min(1.0, c)), 2)
