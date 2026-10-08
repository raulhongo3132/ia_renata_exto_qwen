import sqlite3
import unicodedata
from pathlib import Path

DB = Path("data/tecnoserv.db")

SUCURSALES = ["Centro", "Norte", "Sur", "Oriente", "Poniente", "Aeropuerto",
              "Puerto", "Industrial", "Universidad", "Reforma", "Lomas",
              "Valle", "Mirador", "Plaza Mayor", "Terminal", "Estación",
              "Parque", "Hospital", "Zona Rosa", "Muelle"]

# FICTICIOS (nombres inventados para el proyecto)
TECNICOS = [("Ana Torres", "red"), ("Luis Mendoza", "red"),
            ("Carla Ríos", "servidor"), ("Pedro Salas", "servidor"),
            ("Marta Vega", "aplicacion"), ("Jorge Núñez", "generalista")]


def clave(nombre):
    n = unicodedata.normalize("NFD", nombre)
    return "".join(c for c in n if unicodedata.category(c) != "Mn").lower()


DDL = """
CREATE TABLE IF NOT EXISTS sucursales (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    clave TEXT NOT NULL UNIQUE          -- igual al campo sucursal de casos_bc
);
CREATE TABLE IF NOT EXISTS tecnicos (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    especialidad TEXT NOT NULL
        CHECK (especialidad IN ('red','servidor','aplicacion','generalista')),
    activo INTEGER NOT NULL DEFAULT 1,
    max_carga INTEGER NOT NULL DEFAULT 5
);
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    rol TEXT NOT NULL CHECK (rol IN ('sucursal','tecnico')),
    sucursal_id INTEGER REFERENCES sucursales(id),
    tecnico_id INTEGER REFERENCES tecnicos(id),
    CHECK ((rol = 'sucursal' AND sucursal_id IS NOT NULL AND tecnico_id IS NULL)
        OR (rol = 'tecnico'  AND tecnico_id  IS NOT NULL AND sucursal_id IS NULL))
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- capturados por la sucursal
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id),
    creado_por INTEGER NOT NULL REFERENCES usuarios(id),
    contacto TEXT NOT NULL,
    fecha_creacion TEXT NOT NULL,
    titulo TEXT NOT NULL,
    descripcion_libre TEXT NOT NULL,
    categoria_declarada TEXT
        CHECK (categoria_declarada IN ('red','servidor','aplicacion','otro')),
    equipo_afectado TEXT,
    -- detectado por código
    campos_faltantes_codigo TEXT,       -- lista JSON
    -- generados por el LLM
    tipo TEXT CHECK (tipo IN ('red','servidor','aplicacion','otro')),
    causa_probable TEXT,
    prioridad_sugerida TEXT
        CHECK (prioridad_sugerida IN ('baja','media','alta','critica')),
    accion_sugerida TEXT,
    campos_faltantes_llm TEXT,          -- lista JSON
    confianza_llm REAL,                 -- informativa, NO calibrada
    casos_bc_usados TEXT,               -- lista JSON de ids
    modelo TEXT,
    version_prompt TEXT,
    json_crudo_llm TEXT,
    tiempo_inferencia_ms INTEGER,
    error_llm TEXT,
    -- generados por código / reglas
    confianza_calculada REAL,
    prioridad_final TEXT
        CHECK (prioridad_final IN ('baja','media','alta','critica')),
    regla_aplicada TEXT,
    tecnico_id INTEGER REFERENCES tecnicos(id),
    motivo_asignacion TEXT,
    -- capturados por el técnico
    estado TEXT NOT NULL DEFAULT 'nuevo'
        CHECK (estado IN ('nuevo','interpretado','revision_manual','asignado',
                          'en_atencion','resuelto','cerrado')),
    diagnostico_confirmado TEXT CHECK (diagnostico_confirmado IN ('si','no')),
    causa_real TEXT,
    acciones_realizadas TEXT,
    fecha_resolucion TEXT,
    agregar_a_bc TEXT CHECK (agregar_a_bc IN ('si','no')),
    fecha_actualizacion TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historial_estados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    estado_anterior TEXT,
    estado_nuevo TEXT NOT NULL,
    usuario_id INTEGER REFERENCES usuarios(id),  -- NULL = acción del sistema
    fecha TEXT NOT NULL,
    nota TEXT
);
CREATE INDEX IF NOT EXISTS idx_tickets_estado  ON tickets(estado);
CREATE INDEX IF NOT EXISTS idx_tickets_tecnico ON tickets(tecnico_id);
CREATE INDEX IF NOT EXISTS idx_tickets_sucursal ON tickets(sucursal_id);
"""


def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(DDL)
    for nombre in SUCURSALES:
        con.execute("INSERT OR IGNORE INTO sucursales (nombre, clave) VALUES (?, ?)",
                    (nombre, clave(nombre)))
    for nombre, esp in TECNICOS:
        con.execute("INSERT OR IGNORE INTO tecnicos (nombre, especialidad) VALUES (?, ?)",
                    (nombre, esp))
    for sid, nombre in con.execute("SELECT id, nombre FROM sucursales").fetchall():
        con.execute("""INSERT OR IGNORE INTO usuarios (nombre, rol, sucursal_id)
                       VALUES (?, 'sucursal', ?)""", (f"Encargado {nombre}", sid))
    for tid, nombre in con.execute("SELECT id, nombre FROM tecnicos").fetchall():
        con.execute("""INSERT OR IGNORE INTO usuarios (nombre, rol, tecnico_id)
                       VALUES (?, 'tecnico', ?)""", (nombre, tid))
    con.commit()
    for tabla in ("sucursales", "tecnicos", "usuarios", "tickets", "casos_bc"):
        n = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        print(f"{tabla:12} {n}")
    con.close()


if __name__ == "__main__":
    main()
