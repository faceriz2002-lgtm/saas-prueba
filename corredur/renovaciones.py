"""Motor de renovaciones: detecta las pólizas que hay que renovar y decide qué comunicación corresponde.
Reglas (documento de diseño): el proceso empieza 60 días antes del vencimiento o cuando llega el aviso de precio
de la compañía; el último día para cambiar de compañía es 30 días antes; salud y vida solo reciben aviso, sin ofertas;
hasta 3 opciones ordenadas por precio; nada se envía sin aprobación."""
import json
from datetime import date, timedelta
from .db import ahora, registrar
from .validadores import email_valido, movil_valido

DIAS_INICIO = 60            # empieza 60 días antes del vencimiento
DIAS_AVISO_COMPANIA = 90    # o antes, si ya llegó el precio de renovación de la compañía
DIAS_LIMITE_CAMBIO = 30     # último día para cambiar de compañía: 30 días antes
UMBRAL_AHORRO_PCT = 7.0     # ahorro mínimo para proponer un cambio (supuesto a confirmar por el despacho)
MAX_OPCIONES = 3
RAMOS_SIN_OFERTA = ("Salud", "Vida")
ESTADOS_CERRADOS = ("enviada", "respondida", "cerrada")

def _d(v):
    return date.fromisoformat(v)

def canales(cliente):
    """Canales disponibles: correo si hay correo válido; WhatsApp solo con consentimiento y móvil válido."""
    if not cliente:
        return {"email": False, "whatsapp": False}
    return {"email": email_valido(cliente["email"]),
            "whatsapp": cliente["acepta_whatsapp"] == 1 and movil_valido(cliente["telefono_movil"])}

def limite_respuesta(fecha_vencimiento):
    return (_d(fecha_vencimiento) - timedelta(days=DIAS_LIMITE_CAMBIO)).isoformat()

def opciones(con, despacho_id, poliza, referencia):
    """Hasta 3 ofertas anotadas, de otras compañías, al menos UMBRAL % por debajo de la referencia, por precio."""
    ult = {}
    for o in con.execute("SELECT * FROM oferta_manual WHERE despacho_id=? AND num_poliza=? ORDER BY fecha_oferta", (despacho_id, poliza["num_poliza"])):
        if o["prima_total_anual"] is None or (o["compania_oferta"] or "").lower() == (poliza["compania"] or "").lower():
            continue
        ult[o["compania_oferta"]] = o          # la más reciente de cada compañía
    res = []
    for o in ult.values():
        ahorro = referencia - o["prima_total_anual"]
        pct = ahorro / referencia * 100 if referencia else 0
        if pct >= UMBRAL_AHORRO_PCT:
            res.append({"compania": o["compania_oferta"], "prima": round(o["prima_total_anual"], 2),
                        "ahorro_eur": round(ahorro, 2), "ahorro_pct": round(pct, 1), "notas": o["notas_cobertura"] or ""})
    res.sort(key=lambda x: (x["prima"], x["compania"]))
    return res[:MAX_OPCIONES]

def evaluar(con, despacho_id, p, hoy):
    """Decide qué toca hacer con una póliza que entra en renovación."""
    cli = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, p["cod_cliente"])).fetchone()
    dias = (_d(p["fecha_vencimiento"]) - hoy).days
    ref = p["prima_renovacion"] if p["prima_renovacion"] else p["prima_total"]
    r = {"tipo": None, "motivo": "", "referencia": ref, "opciones": [], "dias": dias}
    if not cli:
        r.update(tipo="bloqueada", motivo="El cliente de la póliza no existe en la cartera.")
    elif con.execute("SELECT 1 FROM recibo WHERE despacho_id=? AND num_poliza=? AND estado_cobro IN ('Devuelto','Impagado')",
                     (despacho_id, p["num_poliza"])).fetchone():
        r.update(tipo="bloqueada", motivo="Tiene un recibo devuelto o impagado: no se avisa hasta que el empleado decida.")
    elif not any(canales(cli).values()):
        r.update(tipo="bloqueada", motivo="El cliente no tiene correo válido ni WhatsApp utilizable: hay que contactarle por teléfono.")
    elif dias < DIAS_LIMITE_CAMBIO:
        r.update(tipo="fuera_plazo", motivo=f"Faltan {dias} días: ya no se puede cambiar de compañía. Se gestiona a mano.")
    elif p["ramo"] in RAMOS_SIN_OFERTA:
        r.update(tipo="aviso", motivo="Salud y vida: el cliente recibe el aviso de renovación, sin ofertas.")
    elif not ref:
        r.update(tipo="sin_tarificar", motivo="No hay precio de referencia: falta tarificar.")
    else:
        ops = opciones(con, despacho_id, p, ref)
        hay_datos = bool(p["prima_renovacion"]) or con.execute(
            "SELECT 1 FROM oferta_manual WHERE despacho_id=? AND num_poliza=?", (despacho_id, p["num_poliza"])).fetchone()
        if ops:
            r.update(tipo="oferta", opciones=ops, motivo=f"{len(ops)} opción(es) con al menos {UMBRAL_AHORRO_PCT:g} % de ahorro.")
        elif hay_datos:
            r.update(tipo="sin_mejora", motivo=f"Ninguna alternativa mejora el precio en {UMBRAL_AHORRO_PCT:g} % o más.")
        else:
            r.update(tipo="sin_tarificar", motivo="Todavía no hay ofertas ni precio de renovación: falta tarificar.")
    r["estado"] = "preparada" if r["tipo"] in ("oferta", "sin_mejora", "aviso") else "pendiente"
    return r

def detectar(con, despacho_id, hoy=None, usuario_id=None):
    """Crea o actualiza las renovaciones. No toca las ya enviadas ni respondidas. Nunca borra."""
    hoy = hoy or date.today()
    hasta = (hoy + timedelta(days=DIAS_AVISO_COMPANIA)).isoformat()
    nuevas = actualizadas = cerradas = 0
    vistas = set()
    for p in con.execute("""SELECT * FROM poliza WHERE despacho_id=? AND estado='En vigor' AND COALESCE(renovable,1)=1
                            AND fecha_vencimiento>=? AND fecha_vencimiento<=? ORDER BY fecha_vencimiento""",
                         (despacho_id, hoy.isoformat(), hasta)):
        dias = (_d(p["fecha_vencimiento"]) - hoy).days
        if dias > DIAS_INICIO and not p["prima_renovacion"]:
            continue
        vistas.add((p["num_poliza"], p["fecha_vencimiento"]))
        ev = evaluar(con, despacho_id, p, hoy)
        ex = con.execute("SELECT * FROM renovacion WHERE despacho_id=? AND num_poliza=? AND fecha_vencimiento=?",
                         (despacho_id, p["num_poliza"], p["fecha_vencimiento"])).fetchone()
        ahorro_max = max((o["ahorro_eur"] for o in ev["opciones"]), default=None)
        if ex is None:
            con.execute("""INSERT INTO renovacion(despacho_id,num_poliza,fecha_vencimiento,tipo,estado,motivo,referencia,opciones_json,ahorro_max,creada)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (despacho_id, p["num_poliza"], p["fecha_vencimiento"], ev["tipo"], ev["estado"], ev["motivo"], ev["referencia"],
                         json.dumps(ev["opciones"], ensure_ascii=False), ahorro_max, ahora())); nuevas += 1
        elif ex["estado"] not in ESTADOS_CERRADOS:
            con.execute("UPDATE renovacion SET tipo=?,estado=?,motivo=?,referencia=?,opciones_json=?,ahorro_max=? WHERE id=?",
                        (ev["tipo"], ev["estado"], ev["motivo"], ev["referencia"], json.dumps(ev["opciones"], ensure_ascii=False), ahorro_max, ex["id"]))
            actualizadas += 1
    for ex in con.execute("SELECT * FROM renovacion WHERE despacho_id=? AND estado IN ('pendiente','preparada')", (despacho_id,)).fetchall():
        if (ex["num_poliza"], ex["fecha_vencimiento"]) not in vistas:
            con.execute("UPDATE renovacion SET estado='cerrada', motivo=? WHERE id=?", ("Ya no aplica: la póliza cambió de estado o de fecha.", ex["id"])); cerradas += 1
    registrar(con, despacho_id, usuario_id, "renovaciones_detectadas", "renovacion", f"{nuevas} nuevas, {actualizadas} actualizadas, {cerradas} cerradas")
    con.commit()
    return {"nuevas": nuevas, "actualizadas": actualizadas, "cerradas": cerradas}

def listar(con, despacho_id, hoy=None):
    hoy = hoy or date.today()
    filas = []
    for r in con.execute("""SELECT r.*, p.ramo, p.compania, p.producto, p.cod_cliente, p.prima_total FROM renovacion r
                            JOIN poliza p ON p.despacho_id=r.despacho_id AND p.num_poliza=r.num_poliza
                            WHERE r.despacho_id=? AND r.estado<>'cerrada' ORDER BY r.fecha_vencimiento, r.num_poliza""", (despacho_id,)):
        filas.append((r, (_d(r["fecha_vencimiento"]) - hoy).days))
    return filas
