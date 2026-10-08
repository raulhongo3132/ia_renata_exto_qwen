"""Orquesta el flujo de un ticket. No escribe en la BD."""
import json
from busqueda import buscar_casos
from llm import interpretar, MODELO, VERSION_PROMPT
from reglas import validar_ticket, calcular_prioridad, calcular_confianza
from asignacion import asignar


def procesar(db, form, sucursal):
    """form: dict del formulario. sucursal: dict con id, clave, nombre."""
    errores, faltantes = validar_ticket(form)
    if errores:
        return {"ok": False, "errores": errores}

    texto = f"{form['titulo']}. {form['descripcion_libre']}"
    categoria = form.get("categoria_declarada") or None
    casos = buscar_casos(db, texto, sucursal["clave"], categoria, k=3)

    r = interpretar(dict(form, sucursal_nombre=sucursal["nombre"]), casos)
    d = r["datos"]
    pr = calcular_prioridad(texto, d["prioridad_sugerida"] if d else None)
    tipo = d["tipo"] if d else categoria
    conf = calcular_confianza(d is not None, casos, tipo, categoria, len(faltantes))
    asign = asignar(db, tipo or "otro", pr["prioridad_final"], sucursal["clave"])

    if d is None:
        estado = "revision_manual"      # el técnico atiende sin sugerencia del modelo
    else:
        estado = "asignado" if asign else "interpretado"

    return {
        "ok": True, "estado": estado,
        "campos_faltantes_codigo": json.dumps(faltantes, ensure_ascii=False),
        "tipo": tipo,
        "causa_probable": d["causa_probable"] if d else None,
        "prioridad_sugerida": d["prioridad_sugerida"] if d else None,
        "accion_sugerida": d["accion_sugerida"] if d else None,
        "campos_faltantes_llm": json.dumps(d["campos_faltantes"] if d else [], ensure_ascii=False),
        "confianza_llm": d["confianza"] if d else None,
        "casos_bc_usados": json.dumps(d["casos_bc_usados"] if d else []),
        "modelo": MODELO, "version_prompt": VERSION_PROMPT,
        "json_crudo_llm": r["json_crudo"], "tiempo_inferencia_ms": r["tiempo_ms"],
        "error_llm": r["error"],
        "confianza_calculada": conf,
        "prioridad_final": pr["prioridad_final"], "regla_aplicada": pr["regla_aplicada"],
        "tecnico_id": asign["tecnico_id"] if asign else None,
        "motivo_asignacion": asign["motivo"] if asign else "sin técnicos disponibles",
        "avisos": r["avisos"],
        "casos_recuperados": casos,
    }
