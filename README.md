# TecnoServ: tickets con LLM local (sistema híbrido)

Proyecto universitario. Los reportes, sucursales y técnicos son **FICTICIOS** (datos sintéticos); no provienen de ninguna empresa real.

## Idea central

Una sucursal escribe un ticket en texto libre. El **código** hace todo lo verificable y el **LLM** (qwen2.5:3b en Ollama, local) solo interpreta el texto y devuelve un JSON de esquema fijo. La decisión final es de un técnico.

```
Ticket → validación (código) → búsqueda de casos en la BC (código)
       → LLM interpreta → JSON validado (código)
       → reglas de producción fijan la prioridad (gana la regla)
       → asignación de técnico (código) → técnico confirma/corrige
       → si aprueba, el caso entra a la base de conocimientos (BC)
```

| Lo hace el código | Lo hace el LLM |
|---|---|
| Validar campos, buscar casos, reglas de prioridad, confianza, asignación | Interpretar el texto libre: tipo, causa probable, acción sugerida |

## Requisitos

- Linux (probado en Zorin OS 18 / Ubuntu 24.04), Python 3.12
- GPU NVIDIA opcional (probado con RTX 3060 de 6 GB); sin GPU funciona más lento
- ~2 GB libres para el modelo

## Instalación y ejecución

```bash
# 1. Ollama y modelo
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b

# 2. Entorno virtual y librerías
python3 -m venv .venv
source .venv/bin/activate
pip install flask requests jsonschema reportlab "markitdown[pdf]"

# 3. Base de conocimientos (una sola vez)
#    Coloca los PDFs REP-00001.pdf ... REP-00200.pdf en historicos/pdf/
python scripts/convertir_pdfs.py    # PDF -> .md (historicos/md/)
python scripts/cargar_bc.py         # .md -> SQLite (data/tecnoserv.db)
python scripts/crear_tablas_app.py  # tablas, sucursales y técnicos

# 4. Arrancar la app
python app/app.py
```

Abre http://127.0.0.1:5000 y entra con el selector de usuario (sin contraseña).

## Uso rápido

1. Entra como `Encargado <sucursal>` → **Nuevo ticket** (la sucursal no ve la sugerencia del modelo).
2. Entra como el técnico asignado → **Mi cola** → revisa la sugerencia, la regla aplicada y los casos de la BC.
3. Resuelve el ticket y marca **agregar a la BC**: el caso quedará disponible para búsquedas futuras.

## Pruebas

```bash
python scripts/prueba_3b.py      # 3 tickets de ejemplo (no escribe tickets)
python scripts/prueba_fase4.py   # 11 casos + 4 de robustez -> data/resultados_fase4.md
```

## Estructura

```
app/        app.py, pipeline.py, llm.py, esquema.py, reglas.py, busqueda.py, asignacion.py, templates/
scripts/    convertir_pdfs.py, cargar_bc.py, crear_tablas_app.py, pruebas
historicos/ pdf/ (entrada), md/ (convertidos)
data/       tecnoserv.db (SQLite)
```

## Limitaciones

- Datos sintéticos: las métricas son ilustrativas y optimistas.
- Reglas y búsqueda por palabras: no entienden negaciones ni sinónimos.
- El modelo de 3B puede clasificar mal el tipo; por eso el técnico decide y las reglas fijan la prioridad.
- Seguridad solo de demostración: sin contraseñas ni protección CSRF; no usar en producción.
- Verifica la licencia de qwen2.5:3b en https://ollama.com/library/qwen2.5.
