"""Documentos FICTICIOS para la prueba: la póliza y la copia de identificación de cada cliente.
Se generan al vuelo desde los datos de la base. Llevan marca de agua «FICTICIO» y no imitan ningún documento oficial."""
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .formato import eur, fecha

TIPOS_POLIZA = ("Póliza",)
TIPOS_IDENTIFICACION = ("DNI/NIF", "CIF/Escrituras")
TIPOS_DESCARGABLES = TIPOS_POLIZA + TIPOS_IDENTIFICACION

def _marca(c, texto="FICTICIO"):
    c.saveState(); c.setFont("Helvetica-Bold", 90); c.setFillGray(0.93)
    c.translate(300, 380); c.rotate(35); c.drawCentredString(0, 0, texto); c.restoreState()

def _cabecera(c, despacho, titulo):
    c.setFont("Helvetica-Bold", 16); c.drawString(50, 790, titulo)
    c.setFont("Helvetica", 10); c.setFillGray(0.4)
    c.drawString(50, 774, f"{despacho} · DOCUMENTO FICTICIO PARA PRUEBAS · sin validez alguna"); c.setFillGray(0)
    c.line(50, 766, 545, 766)

def _filas(c, y, pares, ancho=150):
    for k, v in pares:
        c.setFont("Helvetica", 10); c.setFillGray(0.4); c.drawString(50, y, k)
        c.setFillGray(0); c.setFont("Helvetica-Bold", 10); c.drawString(50 + ancho, y, str(v) if v not in (None, "") else "—")
        y -= 18
    return y

def _nombre(cl):
    return (cl["razon_social"] or " ".join(x for x in (cl["nombre"], cl["apellido1"], cl["apellido2"]) if x)).strip()

def pdf_poliza(con, despacho_id, num_poliza):
    p = con.execute("SELECT * FROM poliza WHERE despacho_id=? AND num_poliza=?", (despacho_id, num_poliza)).fetchone()
    if not p:
        return None
    cl = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, p["cod_cliente"])).fetchone()
    d = con.execute("SELECT nombre FROM despacho WHERE id=?", (despacho_id,)).fetchone()["nombre"]
    gar = con.execute("SELECT * FROM garantia WHERE despacho_id=? AND num_poliza=? AND COALESCE(incluida,1)=1 ORDER BY id", (despacho_id, num_poliza)).fetchall()
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Póliza {num_poliza} (ficticia)")
    _marca(c); _cabecera(c, d, f"Condiciones particulares · póliza {num_poliza}")
    y = _filas(c, 740, [
        ("Tomador", _nombre(cl) if cl else "—"), ("NIF/CIF", cl["nif"] if cl else "—"),
        ("Ramo", p["ramo"]), ("Producto", p["producto"]), ("Compañía", p["compania"]),
        ("Efecto", fecha(p["fecha_efecto"])), ("Vencimiento", fecha(p["fecha_vencimiento"])),
        ("Estado", p["estado"]), ("Forma de pago", p["forma_pago"]),
        ("Prima neta", eur(p["prima_neta"])), ("Impuestos y recargos", eur(p["impuestos"])),
        ("Prima total anual", eur(p["prima_total"]))])
    y -= 10; c.setFont("Helvetica-Bold", 12); c.drawString(50, y, "Garantías"); y -= 8; c.line(50, y, 545, y); y -= 16
    c.setFont("Helvetica", 10)
    for g in gar:
        if y < 70:
            c.showPage(); _marca(c); y = 780; c.setFont("Helvetica", 10)
        c.drawString(50, y, str(g["garantia"])[:60]); c.drawString(330, y, str(g["capital_limite"] or "—")); c.drawString(450, y, str(g["franquicia"] or "—")); y -= 15
    if not gar:
        c.drawString(50, y, "Sin garantías registradas.")
    c.setFont("Helvetica-Oblique", 8); c.setFillGray(0.4)
    c.drawString(50, 40, "Generado automáticamente con datos inventados. No es una póliza real.")
    c.save(); return buf.getvalue()

def pdf_identificacion(con, despacho_id, cod_cliente):
    cl = con.execute("SELECT * FROM cliente WHERE despacho_id=? AND cod=?", (despacho_id, cod_cliente)).fetchone()
    if not cl:
        return None
    d = con.execute("SELECT nombre FROM despacho WHERE id=?", (despacho_id,)).fetchone()["nombre"]
    empresa = cl["tipo"] == "Persona jurídica"
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Identificación {cod_cliente} (ficticia)")
    _marca(c)
    _cabecera(c, d, "Copia de identificación fiscal (ejemplo)" if empresa else "Copia de documento de identificación (ejemplo)")
    pares = [("Código de cliente", cl["cod"]), ("CIF" if empresa else "NIF", cl["nif"])]
    if empresa:
        pares += [("Razón social", cl["razon_social"])]
    else:
        pares += [("Nombre", cl["nombre"]), ("Apellidos", f"{cl['apellido1'] or ''} {cl['apellido2'] or ''}".strip()),
                  ("Fecha de nacimiento", fecha(cl["fecha_nacimiento"]))]
    pares += [("Domicilio", cl["direccion"]), ("Localidad", f"{cl['cod_postal'] or ''} {cl['poblacion'] or ''}".strip())]
    _filas(c, 740, pares)
    c.setFont("Helvetica-Oblique", 8); c.setFillGray(0.4)
    c.drawString(50, 40, "Documento de ejemplo con datos inventados: no reproduce ni sustituye ningún documento oficial.")
    c.save(); return buf.getvalue()

def pdf_documento(con, despacho_id, cod_documento):
    """Devuelve (nombre_fichero, bytes) o None si el documento no existe o no es descargable en la prueba."""
    d = con.execute("SELECT * FROM documento WHERE despacho_id=? AND cod=?", (despacho_id, cod_documento)).fetchone()
    if not d or d["tipo"] not in TIPOS_DESCARGABLES:
        return None
    if d["tipo"] in TIPOS_POLIZA:
        datos = pdf_poliza(con, despacho_id, d["num_poliza"]) if d["num_poliza"] else None
    else:
        datos = pdf_identificacion(con, despacho_id, d["cod_cliente"])
    if not datos:
        return None
    nombre = (d["nombre_fichero"] or f"{d['cod']}.pdf")
    return nombre if nombre.lower().endswith(".pdf") else nombre + ".pdf", datos
