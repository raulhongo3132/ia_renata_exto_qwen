"""Asignación voraz de técnicos por puntaje (código, sin IA)."""
import sqlite3
from contextlib import closing

PESOS = {"normal": (3.0, 2.0, 1.0), "critica": (3.0, 4.0, 0.5)}  # esp, carga, afin
ABIERTOS = ("asignado", "en_atencion", "revision_manual")


def asignar(db, tipo, prioridad_final, sucursal_clave):
    """Devuelve {'tecnico_id','nombre','motivo'} o None si nadie está disponible."""
    w_esp, w_car, w_afi = PESOS["critica" if prioridad_final == "critica" else "normal"]
    marcas = ",".join("?" * len(ABIERTOS))
    cand = []
    with closing(sqlite3.connect(db)) as con:
        con.row_factory = sqlite3.Row
        tecs = con.execute("SELECT id, nombre, especialidad, max_carga "
                           "FROM tecnicos WHERE activo = 1").fetchall()
        for t in tecs:
            carga = con.execute(
                f"SELECT COUNT(*) FROM tickets WHERE tecnico_id = ? AND estado IN ({marcas})",
                (t["id"], *ABIERTOS)).fetchone()[0]
            if carga >= t["max_carga"]:
                continue                                   # filtro duro
            previos = con.execute(
                "SELECT COUNT(*) FROM casos_bc WHERE tecnico = ? AND sucursal = ?",
                (t["nombre"], sucursal_clave)).fetchone()[0]
            ultima = con.execute(
                """SELECT MAX(h.fecha) FROM historial_estados h
                   JOIN tickets k ON k.id = h.ticket_id
                   WHERE k.tecnico_id = ?
                     AND h.estado_nuevo IN ('asignado','revision_manual')""",
                (t["id"],)).fetchone()[0] or ""
            if t["especialidad"] == tipo or (tipo == "otro" and t["especialidad"] == "generalista"):
                esp = 1.0
            else:
                esp = 0.5 if t["especialidad"] == "generalista" else 0.0
            c_esp = w_esp * esp
            c_car = w_car * (1 - carga / t["max_carga"])
            c_afi = w_afi * min(1.0, previos / 3)
            total = round(c_esp + c_car + c_afi, 3)
            cand.append((-total, ultima, t["id"], t["nombre"], carga,
                         t["max_carga"], c_esp, c_car, c_afi, total))
    if not cand:
        return None
    cand.sort()                      # mayor puntaje; empate: el más antiguo; luego id
    _, _, tid, nombre, carga, mx, c_esp, c_car, c_afi, total = cand[0]
    motivo = (f"{nombre}: puntaje {total} = especialidad {c_esp:.2f} + carga {c_car:.2f} "
              f"+ afinidad {c_afi:.2f} (carga {carga}/{mx}; tipo {tipo}; "
              f"prioridad {prioridad_final})")
    return {"tecnico_id": tid, "nombre": nombre, "motivo": motivo}
