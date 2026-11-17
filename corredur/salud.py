"""Salud de la cartera: revisión automática de todos los errores detectables.
Cada revisión abre las incidencias nuevas y cierra solas las que ya no se detectan."""
from collections import Counter
from datetime import date
from .db import ahora, registrar
from .validadores import nif_valido, email_valido, movil_valido

REGLAS = {
 "NIF_INVALIDO":            ("alta",  "cliente", "NIF/CIF con formato o dígito de control incorrecto"),
 "NIF_DUPLICADO":           ("alta",  "cliente", "Mismo NIF/CIF en varias fichas de cliente"),
 "CLIENTE_DUPLICADO_POSIBLE": ("media","cliente", "Mismo nombre y fecha de nacimiento con NIF distinto"),
 "SIN_CONTACTO":            ("alta",  "cliente", "Sin correo ni móvil válidos: no se le puede avisar"),
 "EMAIL_INVALIDO":          ("media", "cliente", "Correo con formato incorrecto"),
 "MOVIL_INVALIDO":          ("media", "cliente", "Móvil con formato incorrecto"),
 "WHATSAPP_SIN_MOVIL":      ("media", "cliente", "Acepta WhatsApp pero no tiene móvil válido"),
 "POLIZA_VIGENTE_VENCIDA":  ("alta",  "poliza", "Figura en vigor pero su vencimiento ya pasó"),
 "POLIZA_ANULADA_SUSPENDIDA": ("media","poliza", "Póliza anulada o suspendida (aviso visible)"),
 "POLIZA_SIN_CLIENTE":      ("alta",  "poliza", "Póliza cuyo cliente no existe"),
 "POLIZA_FECHAS_INCOHERENTES": ("alta","poliza", "El vencimiento no es posterior al efecto"),
 "POLIZA_PRIMA_INCOHERENTE": ("media","poliza", "Prima neta + impuestos no suma la prima total"),
 "POLIZA_COMISION_INCOHERENTE": ("media","poliza","Comisión anual no coincide con prima neta × %"),
 "POLIZA_NO_EN_EXPORT":     ("media", "poliza", "No aparece en el último export"),
 "CLIENTE_NO_EN_EXPORT":    ("media", "cliente", "No aparece en el último export"),
 "RECIBO_DEVUELTO":         ("alta",  "recibo", "Recibo devuelto o impagado sin gestión registrada"),
 "RECIBO_SIN_POLIZA":       ("alta",  "recibo", "Recibo de una póliza que no existe"),
 "SINIESTRO_SIN_POLIZA":    ("alta",  "siniestro", "Siniestro de una póliza que no existe"),
}

def _nombre(c):
    return (c["razon_social"] or " ".join(x for x in (c["nombre"], c["apellido1"], c["apellido2"]) if x)).strip()

def detectar(con, despacho_id, hoy=None):
    """Devuelve la lista de problemas actuales: (regla, entidad, ref, detalle)."""
    hoy = (hoy or date.today()).isoformat()
    p = []
    add = lambda regla, ref, det: p.append((regla, REGLAS[regla][1], ref, det))
    clientes = con.execute("SELECT * FROM cliente WHERE despacho_id=?", (despacho_id,)).fetchall()
    cods = {c["cod"] for c in clientes}
    polizas = con.execute("SELECT * FROM poliza WHERE despacho_id=?", (despacho_id,)).fetchall()
    nums = {x["num_poliza"] for x in polizas}

    nif_cuenta = Counter((c["nif"] or "").replace(" ", "").upper() for c in clientes if c["nif"])
    clave_nombre = {}
    for c in clientes:
        nom = _nombre(c)
        if c["nif"] and not nif_valido(c["nif"]):
            add("NIF_INVALIDO", c["cod"], f"{nom}: {c['nif']}")
        n = (c["nif"] or "").replace(" ", "").upper()
        if n and nif_cuenta[n] > 1:
            add("NIF_DUPLICADO", c["cod"], f"{nom}: {c['nif']} repetido en {nif_cuenta[n]} fichas")
        if c["fecha_nacimiento"]:
            clave_nombre.setdefault((nom.lower(), c["fecha_nacimiento"]), []).append(c)
        mov_ok, mail_ok = movil_valido(c["telefono_movil"]), email_valido(c["email"])
        if c["email"] and not mail_ok:
            add("EMAIL_INVALIDO", c["cod"], f"{nom}: {c['email']}")
        if c["telefono_movil"] and not mov_ok:
            add("MOVIL_INVALIDO", c["cod"], f"{nom}: {c['telefono_movil']}")
        if not mov_ok and not mail_ok:
            add("SIN_CONTACTO", c["cod"], nom)
        if c["acepta_whatsapp"] == 1 and not mov_ok:
            add("WHATSAPP_SIN_MOVIL", c["cod"], nom)
        if c["no_en_ultimo_export"]:
            add("CLIENTE_NO_EN_EXPORT", c["cod"], nom)
    for grupo in clave_nombre.values():
        nifs = {(g["nif"] or "").upper() for g in grupo}
        if len(grupo) > 1 and len(nifs) > 1:
            for g in grupo:
                add("CLIENTE_DUPLICADO_POSIBLE", g["cod"], f"{_nombre(g)} (misma persona en {len(grupo)} fichas)")

    for x in polizas:
        ref = x["num_poliza"]
        if x["cod_cliente"] not in cods:
            add("POLIZA_SIN_CLIENTE", ref, f"cliente {x['cod_cliente']} no existe")
        if x["estado"] == "En vigor" and x["fecha_vencimiento"] and x["fecha_vencimiento"] < hoy:
            add("POLIZA_VIGENTE_VENCIDA", ref, f"venció el {x['fecha_vencimiento']}")
        if x["estado"] in ("Anulada", "Suspendida"):
            add("POLIZA_ANULADA_SUSPENDIDA", ref, f"{x['estado']}" + (f" ({x['motivo_anulacion']})" if x["motivo_anulacion"] else ""))
        if x["fecha_efecto"] and x["fecha_vencimiento"] and x["fecha_vencimiento"] <= x["fecha_efecto"]:
            add("POLIZA_FECHAS_INCOHERENTES", ref, f"efecto {x['fecha_efecto']}, vencimiento {x['fecha_vencimiento']}")
        if None not in (x["prima_neta"], x["impuestos"], x["prima_total"]) and abs(x["prima_neta"] + x["impuestos"] - x["prima_total"]) > 1.0:
            add("POLIZA_PRIMA_INCOHERENTE", ref, f"{x['prima_neta']} + {x['impuestos']} ≠ {x['prima_total']}")
        if None not in (x["prima_neta"], x["comision_pct"], x["comision_anual"]) and abs(x["prima_neta"] * x["comision_pct"] / 100 - x["comision_anual"]) > 1.0:
            add("POLIZA_COMISION_INCOHERENTE", ref, f"{x['prima_neta']} × {x['comision_pct']} % ≠ {x['comision_anual']}")
        if x["no_en_ultimo_export"]:
            add("POLIZA_NO_EN_EXPORT", ref, "")

    for r in con.execute("SELECT * FROM recibo WHERE despacho_id=?", (despacho_id,)):
        if r["estado_cobro"] in ("Devuelto", "Impagado"):
            add("RECIBO_DEVUELTO", r["cod"], f"{r['num_recibo']} · {r['estado_cobro']} · {r['prima_total']} €")
        if r["num_poliza"] not in nums:
            add("RECIBO_SIN_POLIZA", r["cod"], f"póliza {r['num_poliza']} no existe")
    for s in con.execute("SELECT * FROM siniestro WHERE despacho_id=?", (despacho_id,)):
        if s["num_poliza"] not in nums:
            add("SINIESTRO_SIN_POLIZA", s["cod"], f"póliza {s['num_poliza']} no existe")
    return p

def revisar(con, despacho_id, hoy=None, motivo="diaria", usuario_id=None):
    """Ejecuta la revisión: abre incidencias nuevas, mantiene las abiertas y cierra las resueltas."""
    ahora_ = ahora()
    actuales = {(r, e, ref): d for r, e, ref, d in detectar(con, despacho_id, hoy)}
    previas = {(r["regla"], r["entidad"], r["ref"]): r for r in
               con.execute("SELECT * FROM incidencia_salud WHERE despacho_id=?", (despacho_id,))}
    nuevas = resueltas = 0
    for (regla, entidad, ref), det in actuales.items():
        ant = previas.get((regla, entidad, ref))
        if ant is None:
            con.execute("INSERT INTO incidencia_salud(despacho_id,regla,severidad,entidad,ref,detalle,estado,detectada) VALUES (?,?,?,?,?,?, 'abierta', ?)",
                        (despacho_id, regla, REGLAS[regla][0], entidad, ref, det, ahora_)); nuevas += 1
        elif ant["estado"] == "resuelta":
            con.execute("UPDATE incidencia_salud SET estado='abierta', resuelta=NULL, detalle=?, detectada=? WHERE id=?", (det, ahora_, ant["id"])); nuevas += 1
        else:
            con.execute("UPDATE incidencia_salud SET detalle=? WHERE id=?", (det, ant["id"]))
    for clave, ant in previas.items():
        if clave not in actuales and ant["estado"] == "abierta":
            con.execute("UPDATE incidencia_salud SET estado='resuelta', resuelta=? WHERE id=?", (ahora_, ant["id"])); resueltas += 1
    abiertas = con.execute("SELECT COUNT(*) FROM incidencia_salud WHERE despacho_id=? AND estado='abierta'", (despacho_id,)).fetchone()[0]
    con.execute("INSERT INTO revision_salud(despacho_id,fecha,motivo,abiertas,nuevas,resueltas) VALUES (?,?,?,?,?,?)",
                (despacho_id, ahora_, motivo, abiertas, nuevas, resueltas))
    registrar(con, despacho_id, usuario_id, "revision_salud", "cartera", f"{motivo}: {abiertas} abiertas, {nuevas} nuevas, {resueltas} resueltas")
    con.commit()
    return {"abiertas": abiertas, "nuevas": nuevas, "resueltas": resueltas}

def resumen(con, despacho_id):
    """Contador para el administrador: abiertas por regla y severidad."""
    filas = con.execute("""SELECT regla, severidad, COUNT(*) n FROM incidencia_salud
                           WHERE despacho_id=? AND estado='abierta' GROUP BY regla, severidad
                           ORDER BY CASE severidad WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, n DESC""", (despacho_id,)).fetchall()
    return [(f["regla"], f["severidad"], f["n"], REGLAS[f["regla"]][2]) for f in filas]
