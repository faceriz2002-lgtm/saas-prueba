import io
from datetime import date
import pytest
from pypdf import PdfReader
from corredur.db import conectar, crear_despacho
from corredur.importador import importar
from corredur.web import crear_app

@pytest.fixture(scope="module")
def mundo():
    con = conectar(); did, uid = crear_despacho(con, "Piloto")
    importar(con, did, "export_ejemplo_correduria.xlsx", uid)
    app = crear_app(con, did, hoy=date(2026, 11, 14)); app.config["TESTING"] = True
    return con, did, uid, app

def texto(resp):
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(resp.data)).pages)

def test_descarga_de_la_poliza_de_un_cliente(mundo):
    con, did, uid, app = mundo
    c = app.test_client()
    cod = con.execute("SELECT cod FROM documento WHERE tipo='Póliza' AND num_poliza='HG-2025-0001'").fetchone()[0]
    r = c.get(f"/documento/{cod}/descargar")
    assert r.status_code == 200 and r.mimetype == "application/pdf" and r.data.startswith(b"%PDF")
    assert "attachment" in r.headers["Content-Disposition"] and ".pdf" in r.headers["Content-Disposition"]
    t = texto(r)
    assert "HG-2025-0001" in t and "Cristina Ortega Lacasa" in t and "184,00 €" in t and "FICTICIO" in t

def test_descarga_de_identificacion_persona_y_empresa(mundo):
    con, did, uid, app = mundo
    c = app.test_client()
    pf = con.execute("SELECT d.cod, cl.nif FROM documento d JOIN cliente cl ON cl.cod=d.cod_cliente WHERE d.tipo='DNI/NIF' LIMIT 1").fetchone()
    t = texto(c.get(f"/documento/{pf['cod']}/descargar"))
    assert pf["nif"] in t and "ejemplo" in t.lower() and "FICTICIO" in t
    emp = con.execute("SELECT d.cod, cl.nif, cl.razon_social FROM documento d JOIN cliente cl ON cl.cod=d.cod_cliente WHERE d.tipo='CIF/Escrituras' LIMIT 1").fetchone()
    t = texto(c.get(f"/documento/{emp['cod']}/descargar"))
    assert emp["nif"] in t and emp["razon_social"] in t and "CIF" in t

def test_todos_los_documentos_descargables_se_generan(mundo):
    con, did, uid, app = mundo
    c = app.test_client()
    filas = con.execute("SELECT cod FROM documento WHERE tipo IN ('Póliza','DNI/NIF','CIF/Escrituras')").fetchall()
    assert len(filas) == 79 + 36 + 8
    for f in filas:
        assert c.get(f"/documento/{f['cod']}/descargar").data.startswith(b"%PDF"), f["cod"]

def test_documentos_no_descargables_y_ajenos(mundo):
    con, did, uid, app = mundo
    c = app.test_client()
    recibo = con.execute("SELECT cod FROM documento WHERE tipo='Recibo' LIMIT 1").fetchone()[0]
    assert c.get(f"/documento/{recibo}/descargar").status_code == 404
    assert c.get("/documento/NOEXISTE/descargar").status_code == 404
    d2, a2 = crear_despacho(con, "Otro")
    app2 = crear_app(con, d2); cod = con.execute("SELECT cod FROM documento WHERE tipo='Póliza' LIMIT 1").fetchone()[0]
    assert app2.test_client().get(f"/documento/{cod}/descargar").status_code == 404

def test_ficha_ofrece_descargar_poliza_e_identificacion_y_queda_registrado(mundo):
    con, did, uid, app = mundo
    c = app.test_client()
    html = c.get("/cliente/C01001").get_data(as_text=True)
    assert html.count("Descargar") >= 2
    n = con.execute("SELECT COUNT(*) FROM registro_actividad WHERE accion='documento_descargado'").fetchone()[0]
    c.get(c.get("/cliente/C01001").get_data(as_text=True).split('href="')[1 + html.split('href="').index(next(x for x in html.split('href="') if x.startswith("/documento/"))) - 1].split('"')[0]) if False else None
    cod = con.execute("SELECT cod FROM documento WHERE cod_cliente='C01001' AND tipo='Póliza'").fetchone()[0]
    c.get(f"/documento/{cod}/descargar")
    assert con.execute("SELECT COUNT(*) FROM registro_actividad WHERE accion='documento_descargado'").fetchone()[0] == n + 1
