"""Esquema fijo de la salida del LLM y su validación (código, sin IA)."""
import json
from jsonschema import Draft202012Validator

TIPOS = ["red", "servidor", "aplicacion", "otro"]
PRIORIDADES = ["baja", "media", "alta", "critica"]
FALTANTES_PERMITIDOS = ["equipo_afectado", "ubicacion_exacta", "hora_inicio",
                        "alcance", "mensaje_de_error", "acciones_previas"]

ESQUEMA = {
    "type": "object",
    "properties": {
        "tipo": {"type": "string", "enum": TIPOS},
        "causa_probable": {"type": "string", "minLength": 5, "maxLength": 300},
        "prioridad_sugerida": {"type": "string", "enum": PRIORIDADES},
        "accion_sugerida": {"type": "string", "minLength": 5, "maxLength": 400},
        "campos_faltantes": {"type": "array", "maxItems": 6,
                             "items": {"type": "string", "enum": FALTANTES_PERMITIDOS}},
        "confianza": {"type": "number", "minimum": 0, "maximum": 1},
        "casos_bc_usados": {"type": "array", "maxItems": 3,
                            "items": {"type": "string"}},
    },
    "required": ["tipo", "causa_probable", "prioridad_sugerida",
                 "accion_sugerida", "campos_faltantes", "confianza",
                 "casos_bc_usados"],
    "additionalProperties": False,
}
_VALIDADOR = Draft202012Validator(ESQUEMA)


def extraer_json(texto):
    texto = (texto or "").strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    i, j = texto.find("{"), texto.rfind("}")   # rescate: JSON dentro de texto
    if i != -1 and j > i:
        return json.loads(texto[i:j + 1])
    raise ValueError("no se encontró un objeto JSON")


def validar_salida(texto, ids_validos):
    """Devuelve (datos, error, avisos). Si datos es None, error dice por qué."""
    avisos = []
    try:
        datos = extraer_json(texto)
    except ValueError as e:        # JSONDecodeError hereda de ValueError
        return None, f"JSON inválido: {e}", avisos
    errores = [f"{'/'.join(map(str, e.path)) or 'raíz'}: {e.message}"
               for e in _VALIDADOR.iter_errors(datos)]
    if errores:
        return None, "; ".join(errores[:3]), avisos
    limpios = [i for i in datos["casos_bc_usados"] if i in ids_validos]
    if len(limpios) != len(datos["casos_bc_usados"]):
        avisos.append("el modelo citó ids de casos que no se le enviaron; se descartaron")
    datos["casos_bc_usados"] = limpios
    datos["campos_faltantes"] = list(dict.fromkeys(datos["campos_faltantes"]))
    return datos, None, avisos
