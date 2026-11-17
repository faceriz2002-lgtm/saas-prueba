"""Pantallas de la aplicación (Flask). Rol 'administrador': ve salud de la cartera y comisiones.
Rol 'empleado': ve clientes y pólizas, sin comisiones ni salud.
AVISO: el cambio de usuario por /entrar es solo para la demo; el acceso real con contraseña llega después."""
import json
from datetime import date
from flask import Flask, render_template, abort, session, redirect, request, url_for
from flask import Response
from . import salud as S, renovaciones as R, comunicaciones as C
from .documentos import pdf_documento, TIPOS_DESCARGABLES
from .formato import eur as _eur, fecha as _fecha

def crear_app(con, despacho_id, hoy=None):
    app = Flask(__name__)
    app.secret_key = "solo-demo"
    hoy = hoy or date.today()
    app.jinja_env.filters["fecha"] = _fecha
    app.jinja_env.filters["eur"] = _eur
    app.jinja_env.globals["descargables"] = TIPOS_DESCARGABLES

    def usuario():
        uid = session.get("uid")
        u = con.execute("SELECT * FROM usuario WHERE id=? AND despacho_id=?", (uid, despacho_id)).fetchone() if uid else None
        return u

    def es_admin():
        u = usuario()
        return bool(u and u["rol"] == "administrador")

    @app.before_request
    def exigir_usuario():
        if request.endpoint in ("entrar", "static", "respuesta"):
            return
        if not usuario():
            u = con.execute("SELECT id FROM usuario WHERE despacho_id=? AND rol='administrador' ORDER BY id LIMIT 1", (despacho_id,)).fetchone()
            session["uid"] = u["id"] if u else None   # demo: entra como administrador

    @app.context_processor
    def contexto():
        u = usuario()
        d = con.execute("SELECT nombre FROM despacho WHERE id=?", (despacho_id,)).fetchone()
        abiertas = con.execute("SELECT COUNT(*) FROM incidencia_salud WHERE despacho_id=? AND estado='abierta'", (despacho_id,)).fetchone()[0]
        n_prep = con.execute("SELECT COUNT(*) FROM renovacion WHERE despacho_id=? AND estado='preparada'", (despacho_id,)).fetchone()[0]
        return dict(usuario=u, admin=es_admin(), despacho=d["nombre"], hoy=hoy, n_abiertas=abiertas, n_prep=n_prep,
                    usuarios=con.execute("SELECT * FROM usuario WHERE despacho_id=?", (despacho_id,)).fetchall())

    def solo_admin():
        if not es_admin():
            abort(403)

    def incidencias(entidad, ref):
        return con.execute("SELECT * FROM incidencia_salud WHERE despacho_id=? AND entidad=? AND ref=? AND estado='abierta' ORDER BY severidad",
                           (despacho_id, entidad, ref)).fetchall()

    def nombre_cliente(c):
        return (c["razon_social"] or " ".join(x for x in (c["nombre"], c["apellido1"], c["apellido2"]) if x)).strip()
    app.jinja_env.globals["nombre_cliente"] = nombre_cliente

    def destino(inc):
        """A qué ficha lleva una incidencia."""
        if inc["entidad"] == "cliente":
            return url_for("cliente", cod=inc["ref"])
        if inc["entidad"] == "poliza":
            return url_for("poliza", num=inc["ref"])
        tabla = {"recibo": "recibo", "siniestro": "siniestro"}[inc["entidad"]]
        r = con.execute(f"SELECT num_poliza FROM {tabla} WHERE despacho_id=? AND cod=?", (despacho_id, inc["ref"])).fetchone()
        if r and con.execute("SELECT 1 FROM poliza WHERE despacho_id=? AND num_poliza=?", (despacho_id, r["num_poliza"])).fetchone():
            return url_for("poliza", num=r["num_poliza"])
        return None
    app.jinja_env.globals["destino"] = destino

    def hace_dos_anios():
        return date(hoy.year - 2, hoy.month, min(hoy.day, 28)).isoformat()

    @app.route("/entrar/<int:uid>", endpoint="entrar")
    def entrar(uid):
        if con.execute("SELECT 1 FROM usuario WHERE id=? AND despacho_id=?", (uid, despacho_id)).fetchone():
            session["uid"] = uid
        return redirect(url_for("inicio"))

    @app.route("/")
    def inicio():
        return redirect(url_for("salud") if es_admin() else url_for("clientes"))

    @app.route("/salud")
    def salud():
        solo_admin()
        resumen = S.resumen(con, despacho_id)
        por_sev = {"alta": 0, "media": 0, "baja": 0}
        for _, sev, n, _ in resumen:
            por_sev[sev] += n
        rev = con.execute("SELECT * FROM revision_salud WHERE despacho_id=? ORDER BY id DESC LIMIT 1", (despacho_id,)).fetchone()
        n_clientes = con.execute("SELECT COUNT(*) FROM cliente WHERE despacho_id=?", (despacho_id,)).fetchone()[0]
        n_polizas = con.execute("SELECT COUNT(*) FROM poliza WHERE despacho_id=?", (despacho_id,)).fetchone()[0]
        return render_template("salud.html", resumen=resumen, por_sev=por_sev, rev=rev, n_clientes=n_clientes, n_polizas=n_polizas)

    @app.route("/salud/<regla>")
    def salud_regla(regla):
        solo_admin()
        if regla not in S.REGLAS:
            abort(404)
        filas = con.execute("SELECT * FROM incidencia_salud WHERE despacho_id=? AND regla=? AND estado='abierta' ORDER BY ref", (despacho_id, regla)).fetchall()
        return render_template("salud_regla.html", regla=regla, sev=S.REGLAS[regla][0], desc=S.REGLAS[regla][2], filas=filas)

    @app.route("/clientes")
    def clientes():
        q = (request.args.get("q") or "").strip().lower()
        filas = []
        for c in con.execute("SELECT * FROM cliente WHERE despacho_id=? ORDER BY apellido1, razon_social, nombre", (despacho_id,)):
            nombre = nombre_cliente(c)
            if q and q not in nombre.lower() and q not in (c["nif"] or "").lower() and q not in c["cod"].lower():
                continue
            npol = con.execute("SELECT COUNT(*) FROM poliza WHERE despacho_id=? AND cod_cliente=?", (despacho_id, c["cod"])).fetchone()[0]
            nincid = len(incidencias("cliente", c["cod"]))
            filas.append((c, nombre, npol, nincid))
        return render_template("clientes.html", filas=filas, q=q)

    @app.route("/cliente/<cod>")
    def cliente(cod):
        c = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, cod)).fetchone()
        if not c:
            abort(404)
        pols = con.execute("SELECT * FROM poliza WHERE despacho_id=? AND cod_cliente=? ORDER BY fecha_vencimiento", (despacho_id, cod)).fetchall()
        sin = con.execute("SELECT * FROM siniestro WHERE despacho_id=? AND cod_cliente=? AND fecha_ocurrencia>=? ORDER BY fecha_ocurrencia DESC",
                          (despacho_id, cod, hace_dos_anios())).fetchall()
        vinc = con.execute("""SELECT v.relacion, c.cod, c.nombre, c.apellido1, c.apellido2, c.razon_social FROM vinculo v
                              JOIN cliente c ON c.despacho_id=v.despacho_id AND c.cod=v.cod_destino
                              WHERE v.despacho_id=? AND v.cod_origen=?""", (despacho_id, cod)).fetchall()
        vinc += con.execute("""SELECT v.relacion_inversa AS relacion, c.cod, c.nombre, c.apellido1, c.apellido2, c.razon_social FROM vinculo v
                               JOIN cliente c ON c.despacho_id=v.despacho_id AND c.cod=v.cod_origen
                               WHERE v.despacho_id=? AND v.cod_destino=?""", (despacho_id, cod)).fetchall()
        docs = con.execute("SELECT * FROM documento WHERE despacho_id=? AND cod_cliente=? ORDER BY fecha DESC", (despacho_id, cod)).fetchall()
        recibos_dev = con.execute("SELECT * FROM recibo WHERE despacho_id=? AND cod_cliente=? AND estado_cobro IN ('Devuelto','Impagado')", (despacho_id, cod)).fetchall()
        return render_template("cliente.html", c=c, nombre=nombre_cliente(c), pols=pols, sin=sin, vinc=vinc, docs=docs,
                               recibos_dev=recibos_dev, incid=incidencias("cliente", cod))

    @app.route("/poliza/<num>")
    def poliza(num):
        p = con.execute("SELECT * FROM poliza WHERE despacho_id=? AND num_poliza=?", (despacho_id, num)).fetchone()
        if not p:
            abort(404)
        c = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, p["cod_cliente"])).fetchone()
        gar = con.execute("SELECT * FROM garantia WHERE despacho_id=? AND num_poliza=? ORDER BY id", (despacho_id, num)).fetchall()
        riesgos = [(r["tipo"], json.loads(r["datos_json"] or "{}")) for r in con.execute("SELECT * FROM riesgo WHERE despacho_id=? AND num_poliza=?", (despacho_id, num))]
        recibos = con.execute("SELECT * FROM recibo WHERE despacho_id=? AND num_poliza=? ORDER BY fecha_emision", (despacho_id, num)).fetchall()
        sin = con.execute("SELECT * FROM siniestro WHERE despacho_id=? AND num_poliza=? AND fecha_ocurrencia>=? ORDER BY fecha_ocurrencia DESC",
                          (despacho_id, num, hace_dos_anios())).fetchall()
        ofertas = con.execute("SELECT * FROM oferta_manual WHERE despacho_id=? AND num_poliza=? ORDER BY prima_total_anual", (despacho_id, num)).fetchall()
        docs = con.execute("SELECT * FROM documento WHERE despacho_id=? AND num_poliza=? AND tipo='Póliza'", (despacho_id, num)).fetchall()
        dias = None
        if p["fecha_vencimiento"]:
            y, m, d = map(int, p["fecha_vencimiento"].split("-"))
            dias = (date(y, m, d) - hoy).days
        incid = incidencias("poliza", num) + [i for i in incidencias("recibo", "") if False]
        return render_template("poliza.html", p=p, c=c, nombre=nombre_cliente(c) if c else "(cliente no encontrado)", gar=gar,
                               riesgos=riesgos, recibos=recibos, sin=sin, ofertas=ofertas, dias=dias, incid=incid, docs=docs)

    TIPOS = {"oferta": "Con ofertas", "sin_mejora": "Sigue siendo buena opción", "aviso": "Aviso (salud/vida)",
             "bloqueada": "Retenida", "fuera_plazo": "Fuera de plazo", "sin_tarificar": "Falta tarificar"}
    ESTADOS = {"pendiente": "Pendiente", "preparada": "Lista para aprobar", "enviada": "Enviada", "respondida": "Respondida", "cerrada": "Cerrada"}
    app.jinja_env.globals["TIPOS"] = TIPOS
    app.jinja_env.globals["ESTADOS"] = ESTADOS

    @app.route("/renovaciones")
    def renovaciones():
        filas = []
        for r, dias in R.listar(con, despacho_id, hoy):
            c = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, r["cod_cliente"])).fetchone()
            filas.append((r, dias, nombre_cliente(c) if c else "—"))
        cuenta = {e: sum(1 for f in filas if f[0]["estado"] == e) for e in ESTADOS}
        ahorro = sum(f[0]["ahorro_max"] or 0 for f in filas if f[0]["tipo"] == "oferta")
        return render_template("renovaciones.html", filas=filas, cuenta=cuenta, ahorro=ahorro)

    def _datos_renovacion(rid):
        r = con.execute("SELECT * FROM renovacion WHERE id=? AND despacho_id=?", (rid, despacho_id)).fetchone()
        if not r:
            abort(404)
        p = con.execute("SELECT * FROM poliza WHERE despacho_id=? AND num_poliza=?", (despacho_id, r["num_poliza"])).fetchone()
        c = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, p["cod_cliente"])).fetchone()
        return r, p, c

    @app.route("/renovacion/<int:rid>")
    def renovacion(rid):
        r, p, c = _datos_renovacion(rid)
        dias = (date.fromisoformat(r["fecha_vencimiento"]) - hoy).days
        msg = C.componer(con, despacho_id, r) if r["tipo"] in C.TEXTOS else None
        envios = con.execute("SELECT * FROM envio WHERE despacho_id=? AND renovacion_id=? ORDER BY canal", (despacho_id, rid)).fetchall()
        val = C.plantilla_validada(con, despacho_id, r["tipo"]) if r["tipo"] in C.TEXTOS else None
        validador = con.execute("SELECT nombre FROM usuario WHERE id=?", (val["validada_por"],)).fetchone() if val else None
        return render_template("renovacion.html", r=r, p=p, c=c, nombre=nombre_cliente(c) if c else "—", dias=dias, msg=msg,
                               envios=envios, canales=R.canales(c), val=val, validador=validador["nombre"] if validador else None,
                               impedimento=C.puede_enviarse(con, despacho_id, r) if r["estado"] == "preparada" else "",
                               ops=json.loads(r["opciones_json"] or "[]"), limite=R.limite_respuesta(r["fecha_vencimiento"]),
                               umbral=R.UMBRAL_AHORRO_PCT, mensaje=request.args.get("m"))

    @app.route("/renovacion/<int:rid>/aprobar", methods=["POST"])
    def aprobar(rid):
        _datos_renovacion(rid)
        try:
            res = C.aprobar_y_enviar(con, despacho_id, rid, session.get("uid"), hoy)
            m = "Enviado en modo simulado (" + " y ".join(res["canales"]) + "): no ha salido nada real."
        except C.ErrorNegocio as e:
            m = "No se envió: " + str(e)
        return redirect(url_for("renovacion", rid=rid, m=m))

    @app.route("/texto/<tipo>/validar", methods=["POST"])
    def validar_texto(tipo):
        solo_admin()
        try:
            C.validar_plantilla(con, despacho_id, tipo, session.get("uid"))
            m = "Texto validado."
        except C.ErrorNegocio as e:
            m = str(e)
        rid = request.form.get("volver")
        return redirect(url_for("renovacion", rid=int(rid), m=m) if rid else url_for("renovaciones"))

    @app.route("/salida")
    def salida():
        solo_admin()
        filas = con.execute("""SELECT e.*, r.num_poliza FROM envio e JOIN renovacion r ON r.id=e.renovacion_id
                               WHERE e.despacho_id=? ORDER BY e.id DESC""", (despacho_id,)).fetchall()
        return render_template("salida.html", filas=filas)

    @app.route("/r/<token>", methods=["GET", "POST"], endpoint="respuesta")
    def respuesta(token):
        """Página pública a la que lleva cada botón del correo. El GET solo muestra y pide confirmar
        (los antivirus de correo abren los enlaces); solo el POST registra la respuesta."""
        if request.method == "POST":
            try:
                info = C.responder(con, token, hoy)
                return render_template("respuesta.html", info=info, hecho=True, token=token), 200
            except C.ErrorNegocio as e:
                return render_template("respuesta.html", info={"ok": False, "error": str(e), "despacho": ""}, hecho=False, token=token), 410
        info = C.consultar_token(con, token, hoy)
        return render_template("respuesta.html", info=info, hecho=False, token=token), (200 if info["ok"] else 410)

    @app.route("/documento/<cod>/descargar")
    def descargar_documento(cod):
        r = pdf_documento(con, despacho_id, cod)
        if not r:
            abort(404)
        nombre, datos = r
        registrar_descarga(cod)
        return Response(datos, mimetype="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{__import__('urllib.parse').parse.quote(nombre)}"})

    def registrar_descarga(cod):
        from .db import registrar
        registrar(con, despacho_id, session.get("uid"), "documento_descargado", "documento", cod)
        con.commit()

    @app.errorhandler(403)
    def prohibido(_):
        return render_template("error.html", titulo="Solo para el administrador", texto="Tu usuario no tiene acceso a esta pantalla."), 403

    @app.errorhandler(404)
    def no_encontrado(_):
        return render_template("error.html", titulo="No encontrado", texto="Esta ficha no existe."), 404

    return app
