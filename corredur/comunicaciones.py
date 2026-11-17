"""Textos de los avisos al cliente, aprobación, envío y respuesta.
Reglas: nada sale sin aprobación de una persona; el texto debe estar validado por el administrador del despacho;
el cliente solo ve la marca del despacho; los botones son enlaces únicos con caducidad.
El envío real (correo y WhatsApp) se conectará en la clase Emisor; en la prueba solo hay un emisor simulado."""
import hashlib
import json
import secrets
from datetime import date, timedelta
from jinja2 import Environment
from .db import ahora, registrar
from .formato import eur, fecha
from . import renovaciones as R

BASE_URL = "https://respuestas.ejemplo.test/r/"   # dominio de pruebas

class ErrorNegocio(Exception):
    """Una regla de negocio impide la acción; el mensaje se puede mostrar al empleado."""

_BTN = "display:inline-block;margin:4px 6px 4px 0;padding:10px 14px;border-radius:8px;background:#1f4e79;color:#fff;text-decoration:none;font-weight:600"
_BTN2 = "display:inline-block;margin:4px 6px 4px 0;padding:10px 14px;border-radius:8px;border:1px solid #1f4e79;color:#1f4e79;text-decoration:none;font-weight:600"

_MARCO = ("<div style=\"font-family:Arial,sans-serif;color:#1f2430;max-width:560px;margin:auto\">"
          "<div style=\"background:#1f4e79;color:#fff;padding:14px 18px;font-size:18px;font-weight:700\">{{ despacho }}</div>"
          "<div style=\"padding:18px;border:1px solid #e5e3dd;border-top:0\">{% block cuerpo %}{% endblock %}"
          "<p style=\"margin-top:22px\">Un saludo,<br><b>{{ despacho }}</b></p></div></div>")

_RECUERDO = ("{% if garantias %}<p><b>Lo que tienes contratado:</b></p><ul>{% for g, cap in garantias %}<li>{{ g }}{% if cap %}: {{ cap }}{% endif %}</li>{% endfor %}</ul>{% endif %}")

TEXTOS = {
 "oferta": {
  "asunto": "Tu seguro de {{ ramo }} vence el {{ fecha }}: hemos comparado alternativas",
  "html": ("<p>Hola {{ nombre }},</p><p>Tu seguro de {{ ramo|lower }} con {{ compania }} (póliza {{ num_poliza }}) vence el <b>{{ fecha }}</b>. "
           "Lo hemos revisado y estas son las alternativas que hemos comparado para ti, de menor a mayor precio:</p>"
           "<p>{{ ref_txt }}: <b>{{ referencia }}</b>.</p>"
           "<table style=\"width:100%;border-collapse:collapse\">{% for o in opciones %}<tr><td style=\"padding:8px;border-bottom:1px solid #e5e3dd\"><b>Opción {{ loop.index }} · {{ o.compania }}</b>"
           "{% if o.notas %}<br><span style=\"color:#6b7280;font-size:13px\">Ten en cuenta: {{ o.notas }}</span>{% endif %}</td>"
           "<td style=\"padding:8px;border-bottom:1px solid #e5e3dd;text-align:right\"><b>{{ o.prima_txt }}</b><br><span style=\"color:#1a7f4b;font-size:13px\">ahorras {{ o.ahorro_txt }} ({{ o.ahorro_pct }} %)</span></td></tr>{% endfor %}</table>"
           "<p>Si quieres cambiar, necesitamos tu respuesta antes del <b>{{ limite }}</b>.</p><p>"
           "{% for o in opciones %}<a href=\"{{ enlaces['cambiar_' ~ loop.index] }}\" style=\"" + _BTN + "\">Cambiar a la opción {{ loop.index }}</a>{% endfor %}"
           "<a href=\"{{ enlaces['no_cambiar'] }}\" style=\"" + _BTN2 + "\">No cambiar</a>"
           "<a href=\"{{ enlaces['llamar'] }}\" style=\"" + _BTN2 + "\">Prefiero que me llamen</a></p>"),
  "wa": ("Hola {{ nombre }}, soy {{ despacho }}. Tu seguro de {{ ramo|lower }} ({{ compania }}) vence el {{ fecha }}. {{ ref_txt }}: {{ referencia }}.\n"
         "Alternativas, de menor a mayor precio:\n{% for o in opciones %}{{ loop.index }}) {{ o.compania }}: {{ o.prima_txt }} (ahorras {{ o.ahorro_txt }})\n{% endfor %}"
         "Responde antes del {{ limite }}:\n{% for o in opciones %}Cambiar a la opción {{ loop.index }}: {{ enlaces['cambiar_' ~ loop.index] }}\n{% endfor %}"
         "No cambiar: {{ enlaces['no_cambiar'] }}\nPrefiero que me llamen: {{ enlaces['llamar'] }}")},
 "sin_mejora": {
  "asunto": "Tu seguro de {{ ramo }} se renueva el {{ fecha }}: sigue siendo una buena opción",
  "html": ("<p>Hola {{ nombre }},</p><p>Tu seguro de {{ ramo|lower }} con {{ compania }} (póliza {{ num_poliza }}) se renueva el <b>{{ fecha }}</b>. "
           "Lo hemos revisado y <b>sigue siendo una buena opción</b>: no hemos encontrado una alternativa claramente mejor.</p>"
           "<p>{{ ref_txt }}: <b>{{ referencia }}</b>.</p>" + _RECUERDO +
           "<p>Si prefieres comentarlo con nosotros:</p><p><a href=\"{{ enlaces['llamar'] }}\" style=\"" + _BTN + "\">Prefiero que me llamen</a></p>"),
  "wa": ("Hola {{ nombre }}, soy {{ despacho }}. Tu seguro de {{ ramo|lower }} ({{ compania }}) se renueva el {{ fecha }}. "
         "Lo hemos revisado y sigue siendo una buena opción. {{ ref_txt }}: {{ referencia }}.\nSi prefieres que te llamemos: {{ enlaces['llamar'] }}")},
 "aviso": {
  "asunto": "Tu seguro de {{ ramo }} se renueva el {{ fecha }}",
  "html": ("<p>Hola {{ nombre }},</p><p>Te avisamos de que tu seguro de {{ ramo|lower }} con {{ compania }} (póliza {{ num_poliza }}) se renueva el <b>{{ fecha }}</b>.</p>"
           "<p>{{ ref_txt }}: <b>{{ referencia }}</b>.</p>" + _RECUERDO +
           "<p>Si tienes cualquier duda, o quieres revisar tu cobertura:</p><p><a href=\"{{ enlaces['llamar'] }}\" style=\"" + _BTN + "\">Prefiero que me llamen</a></p>"),
  "wa": ("Hola {{ nombre }}, soy {{ despacho }}. Tu seguro de {{ ramo|lower }} ({{ compania }}) se renueva el {{ fecha }}. {{ ref_txt }}: {{ referencia }}.\n"
         "Si tienes dudas o prefieres que te llamemos: {{ enlaces['llamar'] }}")},
}

_env = Environment(autoescape=True)
_env_texto = Environment(autoescape=False)
def _plantilla_html(tipo):
    return _env.from_string(_MARCO.replace("{% block cuerpo %}{% endblock %}", TEXTOS[tipo]["html"]))

def version(tipo):
    t = TEXTOS[tipo]
    return hashlib.sha1((t["asunto"] + _MARCO + t["html"] + t["wa"]).encode()).hexdigest()[:10]

# ---------- validación de textos (la da el administrador del despacho) ----------
def plantilla_validada(con, despacho_id, tipo):
    r = con.execute("SELECT * FROM plantilla_validacion WHERE despacho_id=? AND tipo=?", (despacho_id, tipo)).fetchone()
    return r if r and r["version"] == version(tipo) else None

def validar_plantilla(con, despacho_id, tipo, usuario_id):
    u = con.execute("SELECT rol FROM usuario WHERE id=? AND despacho_id=?", (usuario_id, despacho_id)).fetchone()
    if not u or u["rol"] != "administrador":
        raise ErrorNegocio("Solo el administrador puede validar los textos.")
    if tipo not in TEXTOS:
        raise ErrorNegocio("Texto desconocido.")
    con.execute("INSERT OR REPLACE INTO plantilla_validacion(despacho_id,tipo,version,validada_por,validada_en) VALUES (?,?,?,?,?)",
                (despacho_id, tipo, version(tipo), usuario_id, ahora()))
    registrar(con, despacho_id, usuario_id, "texto_validado", "plantilla", f"{tipo} v{version(tipo)}")
    con.commit()

# ---------- composición ----------
def componer(con, despacho_id, reno, enlaces=None):
    """Genera asunto y cuerpos del aviso. Sin enlaces reales (vista previa) los botones apuntan a '#'."""
    tipo = reno["tipo"]
    if tipo not in TEXTOS:
        raise ErrorNegocio("Esta renovación no genera aviso al cliente.")
    p = con.execute("SELECT * FROM poliza WHERE despacho_id=? AND num_poliza=?", (despacho_id, reno["num_poliza"])).fetchone()
    cl = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, p["cod_cliente"])).fetchone()
    nombre_despacho = con.execute("SELECT nombre FROM despacho WHERE id=?", (despacho_id,)).fetchone()["nombre"]
    ops = json.loads(reno["opciones_json"] or "[]")
    for o in ops:
        o["prima_txt"], o["ahorro_txt"] = eur(o["prima"]), eur(o["ahorro_eur"])
    gar = [(g["garantia"], g["capital_limite"]) for g in con.execute(
        "SELECT * FROM garantia WHERE despacho_id=? AND num_poliza=? AND COALESCE(incluida,1)=1 ORDER BY id LIMIT 6", (despacho_id, p["num_poliza"]))]
    nombre = cl["razon_social"] or cl["nombre"] or "cliente"
    ctx = dict(despacho=nombre_despacho, nombre=nombre, ramo=p["ramo"], compania=p["compania"], num_poliza=p["num_poliza"],
               fecha=fecha(p["fecha_vencimiento"]), limite=fecha(R.limite_respuesta(p["fecha_vencimiento"])),
               referencia=eur(reno["referencia"]), ref_txt=("Precio de renovación que te propone " + p["compania"]) if p["prima_renovacion"] else "Precio actual de tu seguro",
               opciones=ops, garantias=gar,
               enlaces=enlaces or {k: "#" for k in ("cambiar_1", "cambiar_2", "cambiar_3", "no_cambiar", "llamar")})
    t = TEXTOS[tipo]
    return {"asunto": _env_texto.from_string(t["asunto"]).render(**ctx), "html": _plantilla_html(tipo).render(**ctx),
            "wa": _env_texto.from_string(t["wa"]).render(**ctx), "tipo": tipo, "version": version(tipo),
            "nombre_cliente": nombre, "num_opciones": len(ops)}

# ---------- envío ----------
class EmisorSimulado:
    """No envía nada real: deja el mensaje en la bandeja de salida. El emisor real (correo y WhatsApp) sustituirá a esta clase."""
    modo = "simulado"
    def enviar(self, con, despacho_id, reno_id, canal, destinatario, asunto, html, texto, aprobado_por):
        con.execute("""INSERT INTO envio(despacho_id,renovacion_id,canal,destinatario,asunto,cuerpo_html,cuerpo_texto,estado,modo,enviado_en,aprobado_por)
                       VALUES (?,?,?,?,?,?,?, 'enviado', ?, ?, ?)""",
                    (despacho_id, reno_id, canal, destinatario, asunto, html, texto, self.modo, ahora(), aprobado_por))

def puede_enviarse(con, despacho_id, reno):
    """Devuelve '' si se puede aprobar, o el motivo que lo impide."""
    if reno["estado"] != "preparada":
        return {"enviada": "Ya se envió.", "respondida": "Ya se envió y el cliente respondió."}.get(reno["estado"], "Esta renovación no está lista para enviar.")
    if not plantilla_validada(con, despacho_id, reno["tipo"]):
        return "El texto de este aviso aún no está validado por el administrador."
    p = con.execute("SELECT cod_cliente FROM poliza WHERE despacho_id=? AND num_poliza=?", (despacho_id, reno["num_poliza"])).fetchone()
    cl = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, p["cod_cliente"])).fetchone()
    if not any(R.canales(cl).values()):
        return "El cliente no tiene ningún canal disponible."
    return ""

def aprobar_y_enviar(con, despacho_id, reno_id, usuario_id, hoy=None, emisor=None):
    hoy = hoy or date.today()
    emisor = emisor or EmisorSimulado()
    reno = con.execute("SELECT * FROM renovacion WHERE id=? AND despacho_id=?", (reno_id, despacho_id)).fetchone()
    if not reno:
        raise ErrorNegocio("La renovación no existe.")
    if not con.execute("SELECT 1 FROM usuario WHERE id=? AND despacho_id=?", (usuario_id, despacho_id)).fetchone():
        raise ErrorNegocio("Usuario no autorizado.")
    motivo = puede_enviarse(con, despacho_id, reno)
    if motivo:
        raise ErrorNegocio(motivo)
    if hoy.isoformat() > R.limite_respuesta(reno["fecha_vencimiento"]) and reno["tipo"] == "oferta":
        raise ErrorNegocio("Ya pasó el último día para cambiar de compañía: no se pueden enviar opciones.")
    p = con.execute("SELECT cod_cliente FROM poliza WHERE despacho_id=? AND num_poliza=?", (despacho_id, reno["num_poliza"])).fetchone()
    cl = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, p["cod_cliente"])).fetchone()
    ops = json.loads(reno["opciones_json"] or "[]")
    if reno["tipo"] == "oferta":
        acciones = [f"cambiar_{i}" for i in range(1, len(ops) + 1)] + ["no_cambiar", "llamar"]
    else:
        acciones = ["llamar"]
    enlaces, expira = {}, R.limite_respuesta(reno["fecha_vencimiento"])
    try:
        for a in acciones:
            t = secrets.token_urlsafe(18)
            con.execute("INSERT INTO token_respuesta(token,despacho_id,renovacion_id,accion,expira) VALUES (?,?,?,?,?)",
                        (t, despacho_id, reno_id, a, expira))
            enlaces[a] = BASE_URL + t
        msg = componer(con, despacho_id, reno, enlaces)
        canales = R.canales(cl)
        if canales["email"]:
            emisor.enviar(con, despacho_id, reno_id, "email", cl["email"], msg["asunto"], msg["html"], None, usuario_id)
        if canales["whatsapp"]:
            emisor.enviar(con, despacho_id, reno_id, "whatsapp", cl["telefono_movil"], None, None, msg["wa"], usuario_id)
        con.execute("UPDATE renovacion SET estado='enviada', enviada_en=?, aprobada_por=? WHERE id=?", (ahora(), usuario_id, reno_id))
        registrar(con, despacho_id, usuario_id, "aviso_enviado", "renovacion",
                  f"{reno['num_poliza']} · {reno['tipo']} · canales: {', '.join(c for c, ok in canales.items() if ok)} · modo {emisor.modo}")
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"canales": [c for c, ok in canales.items() if ok], "modo": emisor.modo}

# ---------- respuesta del cliente ----------
_TXT = {"no_cambiar": "No cambiar", "llamar": "Prefiero que me llamen"}

def _accion_txt(accion, ops):
    if accion.startswith("cambiar_"):
        i = int(accion.split("_")[1]) - 1
        if 0 <= i < len(ops):
            return f"Cambiar a la opción {i+1} ({ops[i]['compania']}, {eur(ops[i]['prima'])})"
    return _TXT.get(accion, accion)

def consultar_token(con, token, hoy=None):
    """Para mostrar la página de confirmación. No registra nada."""
    hoy = hoy or date.today()
    t = con.execute("SELECT * FROM token_respuesta WHERE token=?", (token,)).fetchone()
    if not t:
        return {"ok": False, "error": "Este enlace no es válido."}
    reno = con.execute("SELECT * FROM renovacion WHERE id=?", (t["renovacion_id"],)).fetchone()
    p = con.execute("SELECT ramo,compania,num_poliza,fecha_vencimiento FROM poliza WHERE despacho_id=? AND num_poliza=?", (t["despacho_id"], reno["num_poliza"])).fetchone()
    d = con.execute("SELECT nombre FROM despacho WHERE id=?", (t["despacho_id"],)).fetchone()["nombre"]
    base = {"despacho": d, "ramo": p["ramo"], "compania": p["compania"], "vence": p["fecha_vencimiento"]}
    if reno["respuesta_accion"] or t["usado_en"]:
        return {**base, "ok": False, "error": "Ya recibimos tu respuesta. Si quieres cambiarla, llámanos."}
    if hoy.isoformat() > t["expira"]:
        return {**base, "ok": False, "error": "Este enlace ha caducado. Llámanos y lo vemos."}
    return {**base, "ok": True, "accion": t["accion"], "texto": _accion_txt(t["accion"], json.loads(reno["opciones_json"] or "[]"))}

def responder(con, token, hoy=None):
    """Registra la respuesta del cliente (solo la primera). Los enlaces de esa renovación dejan de valer."""
    hoy = hoy or date.today()
    info = consultar_token(con, token, hoy)
    if not info["ok"]:
        raise ErrorNegocio(info["error"])
    t = con.execute("SELECT * FROM token_respuesta WHERE token=?", (token,)).fetchone()
    reno = con.execute("SELECT * FROM renovacion WHERE id=?", (t["renovacion_id"],)).fetchone()
    con.execute("UPDATE token_respuesta SET usado_en=? WHERE renovacion_id=?", (ahora(), t["renovacion_id"]))
    con.execute("UPDATE renovacion SET estado='respondida', respuesta_accion=?, respuesta_detalle=?, respuesta_en=? WHERE id=?",
                (t["accion"], info["texto"], ahora(), t["renovacion_id"]))
    registrar(con, t["despacho_id"], None, "respuesta_cliente", "renovacion", f"{reno['num_poliza']}: {info['texto']}")
    con.commit()
    return info
