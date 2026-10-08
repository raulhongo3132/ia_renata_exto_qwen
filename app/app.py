"""App web de tickets (Flask). Orquesta pantallas; la lógica está en pipeline.py."""
import json
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from esquema import TIPOS
from pipeline import procesar

DB = str(Path(__file__).resolve().parent.parent / "data" / "tecnoserv.db")
ABIERTOS = ("asignado", "en_atencion", "revision_manual")
app = Flask(__name__)
app.secret_key = "clave-solo-para-demo-academica"   # limitación: no es secreta

SEL = """SELECT k.*, s.nombre AS sucursal_nombre, s.clave AS sucursal_clave,
                tc.nombre AS tecnico_nombre
         FROM tickets k JOIN sucursales s ON s.id = k.sucursal_id
         LEFT JOIN tecnicos tc ON tc.id = k.tecnico_id """
ORDEN = (" ORDER BY CASE k.prioridad_final WHEN 'critica' THEN 0 WHEN 'alta' THEN 1 "
         "WHEN 'media' THEN 2 ELSE 3 END, k.fecha_creacion")
COLS_R = ["estado", "campos_faltantes_codigo", "tipo", "causa_probable",
          "prioridad_sugerida", "accion_sugerida", "campos_faltantes_llm",
          "confianza_llm", "casos_bc_usados", "modelo", "version_prompt",
          "json_crudo_llm", "tiempo_inferencia_ms", "error_llm",
          "confianza_calculada", "prioridad_final", "regla_aplicada",
          "tecnico_id", "motivo_asignacion"]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")   # hay que activarlo por conexión
    return g.db


@app.teardown_appcontext
def cerrar_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def ahora():
    return datetime.now().isoformat(timespec="seconds")


def lista_json(txt):
    try:
        return json.loads(txt or "[]")
    except ValueError:
        return []


@app.before_request
def cargar_usuario():
    g.user = None
    if session.get("uid"):
        g.user = db().execute(
            """SELECT u.*, s.nombre AS sucursal_nombre, s.clave AS sucursal_clave
               FROM usuarios u LEFT JOIN sucursales s ON s.id = u.sucursal_id
               WHERE u.id = ?""", (session["uid"],)).fetchone()


@app.context_processor
def inyectar():
    return {"usuario": g.get("user")}


def rol(r):
    def deco(fn):
        @wraps(fn)
        def w(*a, **k):
            if g.user is None:
                return redirect(url_for("entrada"))
            if g.user["rol"] != r:
                abort(403)
            return fn(*a, **k)
        return w
    return deco


def cambiar_estado(con, tid, nuevo, nota=None):
    ant = con.execute("SELECT estado FROM tickets WHERE id = ?", (tid,)).fetchone()[0]
    ts = ahora()
    con.execute("UPDATE tickets SET estado = ?, fecha_actualizacion = ? WHERE id = ?",
                (nuevo, ts, tid))
    con.execute("""INSERT INTO historial_estados
                   (ticket_id, estado_anterior, estado_nuevo, usuario_id, fecha, nota)
                   VALUES (?,?,?,?,?,?)""",
                (tid, ant, nuevo, g.user["id"] if g.user else None, ts, nota))


def traer_ticket(con, tid):
    return con.execute(SEL + "WHERE k.id = ?", (tid,)).fetchone()


def ticket_propio(con, tid):
    """Ticket asignado al técnico actual, o 404/403."""
    t = traer_ticket(con, tid)
    if t is None:
        abort(404)
    if t["tecnico_id"] != g.user["tecnico_id"]:
        abort(403)
    return t


# ---------------- Entrada ----------------
@app.get("/")
def inicio():
    if g.user is None:
        return redirect(url_for("entrada"))
    return redirect(url_for("tickets" if g.user["rol"] == "sucursal" else "cola"))


@app.route("/entrada", methods=["GET", "POST"])
def entrada():
    con = db()
    if request.method == "POST":
        u = con.execute("SELECT id FROM usuarios WHERE id = ?",
                        (request.form.get("uid"),)).fetchone()
        if u:
            session.clear()
            session["uid"] = u["id"]
            return redirect(url_for("inicio"))
        flash("Usuario no válido.", "err")
    usuarios = con.execute("SELECT id, nombre, rol FROM usuarios ORDER BY rol, nombre").fetchall()
    return render_template("entrada.html", usuarios=usuarios)


@app.get("/salir")
def salir():
    session.clear()
    return redirect(url_for("entrada"))


# ---------------- Sucursal ----------------
@app.get("/tickets")
@rol("sucursal")
def tickets():
    filas = db().execute(SEL + "WHERE k.sucursal_id = ? ORDER BY k.id DESC",
                         (g.user["sucursal_id"],)).fetchall()
    return render_template("lista.html", titulo="Mis tickets", filas=filas, libres=None)


@app.route("/nuevo", methods=["GET", "POST"])
@rol("sucursal")
def nuevo():
    if request.method == "GET":
        return render_template("nuevo.html", f={})
    campos = ("titulo", "descripcion_libre", "contacto", "categoria_declarada",
              "equipo_afectado")
    form = {k: (request.form.get(k) or "").strip() for k in campos}
    suc = {"id": g.user["sucursal_id"], "clave": g.user["sucursal_clave"],
           "nombre": g.user["sucursal_nombre"]}
    r = procesar(DB, form, suc)            # tarda unos segundos (LLM)
    if not r["ok"]:
        for e in r["errores"]:
            flash(e, "err")
        return render_template("nuevo.html", f=request.form)

    con, ts = db(), ahora()
    cols = ["sucursal_id", "creado_por", "contacto", "fecha_creacion", "titulo",
            "descripcion_libre", "categoria_declarada", "equipo_afectado",
            "fecha_actualizacion"] + COLS_R
    vals = [suc["id"], g.user["id"], form["contacto"], ts, form["titulo"],
            form["descripcion_libre"], form["categoria_declarada"] or None,
            form["equipo_afectado"] or None, ts] + [r[c] for c in COLS_R]
    cur = con.execute(f"INSERT INTO tickets ({','.join(cols)}) "
                      f"VALUES ({','.join('?' * len(cols))})", vals)
    tid = cur.lastrowid
    con.execute("""INSERT INTO historial_estados
        (ticket_id, estado_anterior, estado_nuevo, usuario_id, fecha, nota)
        VALUES (?,NULL,'nuevo',?,?,'ticket creado')""", (tid, g.user["id"], ts))
    con.execute("""INSERT INTO historial_estados
        (ticket_id, estado_anterior, estado_nuevo, usuario_id, fecha, nota)
        VALUES (?,'nuevo',?,NULL,?,?)""",
        (tid, r["estado"], ts, "interpretación, reglas y asignación automáticas"))
    con.commit()
    flash(f"Ticket #{tid} creado.", "aviso")
    return redirect(url_for("detalle", tid=tid))


@app.post("/ticket/<int:tid>/cerrar")
@rol("sucursal")
def cerrar(tid):
    con = db()
    t = traer_ticket(con, tid)
    if t is None or t["sucursal_id"] != g.user["sucursal_id"]:
        abort(404)
    if t["estado"] == "resuelto":
        cambiar_estado(con, tid, "cerrado", "la sucursal confirmó la solución")
        con.commit()
    return redirect(url_for("detalle", tid=tid))


# ---------------- Técnico ----------------
@app.get("/cola")
@rol("tecnico")
def cola():
    con = db()
    propios = con.execute(SEL + "WHERE k.tecnico_id = ? AND k.estado IN (?,?,?)" + ORDEN,
                          (g.user["tecnico_id"], *ABIERTOS)).fetchall()
    libres = con.execute(SEL + "WHERE k.tecnico_id IS NULL AND "
                         "k.estado IN ('interpretado','revision_manual')" + ORDEN).fetchall()
    return render_template("lista.html", titulo="Mi cola", filas=propios, libres=libres)


@app.post("/ticket/<int:tid>/tomar")
@rol("tecnico")
def tomar(tid):
    con = db()
    t = traer_ticket(con, tid)
    if t is None or t["tecnico_id"] is not None:
        abort(404)
    con.execute("UPDATE tickets SET tecnico_id = ?, motivo_asignacion = ? WHERE id = ?",
                (g.user["tecnico_id"], "tomado manualmente por el técnico", tid))
    if t["estado"] == "interpretado":
        cambiar_estado(con, tid, "asignado", "tomado por el técnico")
    con.commit()
    return redirect(url_for("detalle", tid=tid))


@app.post("/ticket/<int:tid>/iniciar")
@rol("tecnico")
def iniciar(tid):
    con = db()
    t = ticket_propio(con, tid)
    if t["estado"] in ("asignado", "revision_manual"):
        cambiar_estado(con, tid, "en_atencion")
        con.commit()
    return redirect(url_for("detalle", tid=tid))


@app.post("/ticket/<int:tid>/resolver")
@rol("tecnico")
def resolver(tid):
    con = db()
    t = ticket_propio(con, tid)
    if t["estado"] not in ABIERTOS:
        abort(409)
    f = request.form
    diag = "no" if t["causa_probable"] is None else f.get("diagnostico_confirmado")
    causa = (f.get("causa_real") or "").strip()
    acciones = (f.get("acciones_realizadas") or "").strip()
    tipo, bc = f.get("tipo"), f.get("agregar_a_bc", "no")
    errs = []
    if diag not in ("si", "no"):
        errs.append("Indica si el diagnóstico es correcto.")
    if diag == "si":
        causa = t["causa_probable"]
    elif len(causa) < 5:
        errs.append("Describe la causa real (mínimo 5 caracteres).")
    if len(acciones) < 10:
        errs.append("Describe las acciones realizadas (mínimo 10 caracteres).")
    if tipo not in TIPOS:
        errs.append("Tipo no válido.")
    if bc not in ("si", "no"):
        errs.append("Indica si se agrega a la BC.")
    if errs:
        for e in errs:
            flash(e, "err")
        return redirect(url_for("detalle", tid=tid))

    ts = ahora()
    nota = f"diagnóstico confirmado: {diag}"
    if tipo != t["tipo"]:
        nota += f"; tipo corregido {t['tipo']} → {tipo}"
    con.execute("""UPDATE tickets SET tipo=?, diagnostico_confirmado=?, causa_real=?,
                   acciones_realizadas=?, agregar_a_bc=?, fecha_resolucion=? WHERE id=?""",
                (tipo, diag, causa, acciones, bc, ts, tid))
    cambiar_estado(con, tid, "resuelto", nota)
    if bc == "si":
        minutos = int((datetime.fromisoformat(ts) -
                       datetime.fromisoformat(t["fecha_creacion"])).total_seconds() // 60)
        con.execute("""INSERT OR IGNORE INTO casos_bc
            (id, origen, archivo_md, fecha, sucursal, tipo, prioridad, descripcion,
             causa, solucion, tecnico, tiempo, reportado_por, confiabilidad,
             campos_faltantes, ficticio, fecha_carga)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (f"TCK-{tid:05d}", "ticket", None, t["fecha_creacion"][:10],
             t["sucursal_clave"], tipo, t["prioridad_final"],
             f"{t['titulo']}. {t['descripcion_libre']}", causa, acciones,
             g.user["nombre"], f"{minutos} min", t["contacto"], "alta", "[]",
             1,   # 1 = dato de demostración; en producción real sería 0
             ts))
    con.commit()
    flash("Ticket resuelto." + (" Caso agregado a la BC." if bc == "si" else ""), "aviso")
    return redirect(url_for("cola"))


# ---------------- Detalle (ambos roles) ----------------
@app.get("/ticket/<int:tid>")
def detalle(tid):
    if g.user is None:
        return redirect(url_for("entrada"))
    con = db()
    t = traer_ticket(con, tid)
    if t is None:
        abort(404)
    casos, hist = [], []
    if g.user["rol"] == "sucursal":
        if t["sucursal_id"] != g.user["sucursal_id"]:
            abort(403)
    else:
        if t["tecnico_id"] not in (None, g.user["tecnico_id"]):
            abort(403)
        ids = lista_json(t["casos_bc_usados"])
        if ids:
            casos = con.execute(
                f"SELECT * FROM casos_bc WHERE id IN ({','.join('?' * len(ids))})",
                ids).fetchall()
        hist = con.execute("SELECT * FROM historial_estados WHERE ticket_id = ? ORDER BY id",
                           (tid,)).fetchall()
    return render_template("detalle.html", t=t, casos=casos, hist=hist,
                           fc=lista_json(t["campos_faltantes_codigo"]),
                           fl=lista_json(t["campos_faltantes_llm"]), abiertos=ABIERTOS)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
