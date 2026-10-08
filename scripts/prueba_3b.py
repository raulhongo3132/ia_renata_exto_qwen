import sys
sys.path.insert(0, "app")
from pipeline import procesar

DB = "data/tecnoserv.db"
CASOS = [  # FICTICIOS
    ({"titulo": "Sin internet", "contacto": "Caja 1, ext. 101",
      "descripcion_libre": "Desde temprano no hay internet en toda la sucursal, "
                           "las cajas no cobran. Ya reiniciamos el modem."},
     {"id": 1, "clave": "centro", "nombre": "Centro"}),
    ({"titulo": "Carpeta compartida", "contacto": "Administración, ext. 202",
      "descripcion_libre": "Nadie de contabilidad abre la carpeta compartida, "
                           "dice acceso denegado desde ayer.",
      "categoria_declarada": "servidor"},
     {"id": 3, "clave": "sur", "nombre": "Sur"}),
    ({"titulo": "Impresora", "contacto": "Recepción, ext. 303",
      "descripcion_libre": "La impresora de la oficina atasca el papel a cada rato.",
      "equipo_afectado": "Impresora de oficina"},
     {"id": 2, "clave": "norte", "nombre": "Norte"}),
]

for form, suc in CASOS:
    print("=" * 70)
    print("TICKET:", form["titulo"], "|", suc["nombre"])
    r = procesar(DB, form, suc)
    if not r["ok"]:
        print("ERRORES:", r["errores"]); continue
    print("estado:", r["estado"], "| tiempo:", r["tiempo_inferencia_ms"], "ms")
    print("tipo:", r["tipo"], "| sugerida:", r["prioridad_sugerida"],
          "| FINAL:", r["prioridad_final"])
    print("regla:", r["regla_aplicada"])
    print("causa:", r["causa_probable"])
    print("acción:", r["accion_sugerida"])
    print("faltantes código:", r["campos_faltantes_codigo"],
          "| faltantes LLM:", r["campos_faltantes_llm"])
    print("confianza calculada:", r["confianza_calculada"],
          "| del modelo:", r["confianza_llm"])
    print("casos recuperados:", [c["id"] for c in r["casos_recuperados"]],
          "| usados:", r["casos_bc_usados"])
    print("asignación:", r["motivo_asignacion"])
    print("avisos:", r["avisos"], "| error:", r["error_llm"])
