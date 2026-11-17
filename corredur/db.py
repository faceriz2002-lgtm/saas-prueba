import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "schema.sql"

def conectar(ruta=":memory:"):
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    return con

def ahora():
    return datetime.now().isoformat(timespec="seconds")

def crear_despacho(con, nombre, admin_nombre="Administrador", admin_email="admin@despacho.test"):
    cur = con.execute("INSERT INTO despacho(nombre, creado) VALUES (?,?)", (nombre, ahora()))
    did = cur.lastrowid
    uid = con.execute("INSERT INTO usuario(despacho_id,nombre,email,rol) VALUES (?,?,?,'administrador')",
                      (did, admin_nombre, admin_email)).lastrowid
    registrar(con, did, uid, "despacho_creado", "despacho", nombre)
    con.commit()
    return did, uid

def registrar(con, despacho_id, usuario_id, accion, entidad=None, detalle=None):
    con.execute("INSERT INTO registro_actividad(despacho_id,usuario_id,fecha,accion,entidad,detalle) VALUES (?,?,?,?,?,?)",
                (despacho_id, usuario_id, ahora(), accion, entidad, detalle))

def crear_usuario(con, despacho_id, nombre, email, rol, creado_por=None):
    uid = con.execute("INSERT INTO usuario(despacho_id,nombre,email,rol) VALUES (?,?,?,?)",
                      (despacho_id, nombre, email, rol)).lastrowid
    registrar(con, despacho_id, creado_por, "usuario_creado", "usuario", f"{nombre} ({rol})")
    con.commit()
    return uid
