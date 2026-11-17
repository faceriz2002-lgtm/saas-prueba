import json
from datetime import date, datetime, timedelta
import openpyxl
import pandas as pd
import pytest
from corredur.db import conectar, crear_despacho, crear_usuario
from corredur.importador import importar
from corredur import renovaciones as R, comunicaciones as C, salud
from corredur.web import crear_app

HOY = date(2026, 11, 14)
def en(dias): return datetime.combine(HOY + timedelta(days=dias), datetime.min.time())

CLI = ["COD_CLIENTE","TIPO","NIF_CIF","NOMBRE","APELLIDO_1","RAZON_SOCIAL","TELEFONO_MOVIL","EMAIL","ACEPTA_WHATSAPP"]
POL = ["COD_POLIZA","NUM_POLIZA","COD_CLIENTE","RAMO","PRODUCTO","COMPAÑIA","ESTADO","FECHA_EFECTO","FECHA_VENCIMIENTO",
       "PRIMA_TOTAL_ANUAL","PRIMA_RENOVACION_COMPAÑIA","RENOVABLE"]
OFE = ["NUM_POLIZA","COMPAÑIA_OFERTA","PRIMA_TOTAL_ANUAL","FECHA_OFERTA","NOTAS_COBERTURA"]
REC = ["COD_RECIBO","NUM_RECIBO","NUM_POLIZA","ESTADO_COBRO","PRIMA_TOTAL"]

def cli(cod, email="ok@ejemplo.test", movil="627181521", wa="Sí", nombre="Ana"):
    return [cod, "Persona física", "12345678Z", nombre, "Gil", None, movil, email, wa]

def pol(num, cod="C1", dias=45, ramo="Auto", total=100.0, ren=None, estado="En vigor", renovable="Sí", cia="Compañía A"):
    return ["P-"+num, num, cod, ramo, ramo, cia, estado, en(dias-365), en(dias), total, ren, renovable]

def excel(tp, clientes, polizas, ofertas=(), recibos=(), nombre="e.xlsx"):
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    for h, cab, f in [("CLIENTES",CLI,clientes),("POLIZAS",POL,polizas),("OFERTAS_MANUAL",OFE,ofertas),("RECIBOS",REC,recibos)]:
        ws = wb.create_sheet(h); ws.append(cab); [ws.append(x) for x in f]
    r = tp / nombre; wb.save(r); return r

def of(num, cia, prima, notas=None): return [num, cia, prima, en(0), notas]

@pytest.fixture
def mundo(tmp_path):
    con = conectar(); did, admin = crear_despacho(con, "Despacho Test")
    emp = crear_usuario(con, did, "Laura", "l@d.test", "empleado", admin)
    return con, did, admin, emp, tmp_path

def montar(mundo, clientes, polizas, ofertas=(), recibos=()):
    con, did, admin, emp, tp = mundo
    importar(con, did, excel(tp, clientes, polizas, ofertas, recibos), admin)
    R.detectar(con, did, HOY)
    return {r["num_poliza"]: r for r in con.execute("SELECT * FROM renovacion")}

# ---------- qué entra en renovación y de qué tipo ----------
def test_opciones_ordenadas_por_precio_con_umbral_y_maximo_tres(mundo):
    rs = montar(mundo, [cli("C1")], [pol("A1", total=100)],
                [of("A1","B",90), of("A1","C",95), of("A1","D",80), of("A1","E",85), of("A1","F",70), of("A1","Compañía A",50)])
    r = rs["A1"]; ops = json.loads(r["opciones_json"])
    assert r["tipo"] == "oferta" and r["estado"] == "preparada"
    assert [o["compania"] for o in ops] == ["F", "D", "E"]          # 3 más baratas; C (5 %) no llega al 7 %; la misma compañía se excluye
    assert ops[0]["ahorro_eur"] == 30 and ops[0]["ahorro_pct"] == 30.0
    assert r["ahorro_max"] == 30

def test_referencia_es_el_precio_de_renovacion_de_la_compania(mundo):
    rs = montar(mundo, [cli("C1")], [pol("A1", total=100, ren=120)], [of("A1","B",105), of("A1","C",115)])
    ops = json.loads(rs["A1"]["opciones_json"])
    assert rs["A1"]["referencia"] == 120 and [o["compania"] for o in ops] == ["B"]   # 105 ahorra 12,5 %; 115 solo 4,2 %

def test_sin_mejora_y_sin_tarificar(mundo):
    rs = montar(mundo, [cli("C1")], [pol("A1"), pol("A2"), pol("A3", ren=110)], [of("A1","B",99)])
    assert rs["A1"]["tipo"] == "sin_mejora" and rs["A1"]["estado"] == "preparada"
    assert rs["A2"]["tipo"] == "sin_tarificar" and rs["A2"]["estado"] == "pendiente"
    assert rs["A3"]["tipo"] == "sin_mejora"            # hay precio de renovación pero ninguna oferta mejor

def test_salud_y_vida_solo_aviso_sin_ofertas(mundo):
    rs = montar(mundo, [cli("C1")], [pol("S1", ramo="Salud"), pol("V1", ramo="Vida")], [of("S1","B",10)])
    assert rs["S1"]["tipo"] == "aviso" and json.loads(rs["S1"]["opciones_json"]) == []
    assert rs["V1"]["tipo"] == "aviso"
    assert "Opción" not in C.componer(mundo[0], mundo[1], rs["S1"])["html"]

def test_plazos(mundo):
    rs = montar(mundo, [cli("C1")], [pol("A1", dias=60), pol("A2", dias=61), pol("A3", dias=61, ren=100), pol("A4", dias=30), pol("A5", dias=29),
                                     pol("A6", dias=-1), pol("A7", dias=100, ren=100), pol("A8", estado="Anulada"), pol("A9", renovable="No")])
    assert "A1" in rs and "A2" not in rs                  # 60 días entra; 61 no, salvo que haya avisado la compañía
    assert "A3" in rs and "A7" not in rs                  # con precio de renovación entra hasta 90 días
    assert rs["A4"]["tipo"] != "fuera_plazo"              # justo 30 días: aún se puede cambiar
    assert rs["A5"]["tipo"] == "fuera_plazo" and rs["A5"]["estado"] == "pendiente"
    assert not ({"A6", "A8", "A9"} & set(rs))             # vencida, anulada y no renovable no entran

def test_retenidas_por_recibo_devuelto_o_sin_canal(mundo):
    rs = montar(mundo, [cli("C1"), cli("C2", email=None, movil=None, wa="No")], [pol("A1"), pol("A2", cod="C2"), pol("A3")],
                [of("A1","B",50), of("A2","B",50), of("A3","B",50)], [["R1","R1/1","A1","Devuelto",50]])
    assert rs["A1"]["tipo"] == "bloqueada" and "recibo" in rs["A1"]["motivo"]
    assert rs["A2"]["tipo"] == "bloqueada" and "WhatsApp" in rs["A2"]["motivo"]
    assert rs["A3"]["tipo"] == "oferta"
    assert rs["A1"]["estado"] == "pendiente"

def test_detectar_es_idempotente_y_no_toca_lo_enviado(mundo):
    con, did, admin, emp, tp = mundo
    montar(mundo, [cli("C1")], [pol("A1")], [of("A1","B",50)])
    C.validar_plantilla(con, did, "oferta", admin)
    rid = con.execute("SELECT id FROM renovacion").fetchone()[0]
    C.aprobar_y_enviar(con, did, rid, emp, HOY)
    r2 = R.detectar(con, did, HOY)
    assert r2["nuevas"] == 0 and con.execute("SELECT COUNT(*) FROM renovacion").fetchone()[0] == 1
    assert con.execute("SELECT estado FROM renovacion").fetchone()[0] == "enviada"

def test_renovacion_pendiente_se_cierra_si_la_poliza_deja_de_aplicar(mundo):
    con, did, admin, emp, tp = mundo
    montar(mundo, [cli("C1")], [pol("A1")], [of("A1","B",50)])
    importar(con, did, excel(tp, [cli("C1")], [pol("A1", estado="Anulada")], [of("A1","B",50)], nombre="2.xlsx"), admin)
    R.detectar(con, did, HOY)
    assert con.execute("SELECT estado FROM renovacion").fetchone()[0] == "cerrada"

# ---------- aprobación y envío ----------
def preparar_una(mundo, **kw):
    con, did, admin, emp, tp = mundo
    montar(mundo, [cli("C1", **kw)], [pol("A1")], [of("A1","B",80)])
    return con.execute("SELECT id FROM renovacion").fetchone()[0]

def test_nada_se_envia_sin_aprobar_ni_con_texto_sin_validar(mundo):
    con, did, admin, emp, tp = mundo
    rid = preparar_una(mundo)
    assert con.execute("SELECT COUNT(*) FROM envio").fetchone()[0] == 0          # detectar no envía
    with pytest.raises(C.ErrorNegocio, match="validado"):
        C.aprobar_y_enviar(con, did, rid, emp, HOY)
    assert con.execute("SELECT COUNT(*) FROM envio").fetchone()[0] == 0

def test_solo_el_administrador_valida_textos(mundo):
    con, did, admin, emp, tp = mundo
    with pytest.raises(C.ErrorNegocio, match="administrador"):
        C.validar_plantilla(con, did, "oferta", emp)
    C.validar_plantilla(con, did, "oferta", admin)
    v = C.plantilla_validada(con, did, "oferta")
    assert v["validada_por"] == admin and v["validada_en"]

def test_validacion_caduca_si_cambia_el_texto(mundo, monkeypatch):
    con, did, admin, emp, tp = mundo
    C.validar_plantilla(con, did, "oferta", admin)
    assert C.plantilla_validada(con, did, "oferta")
    monkeypatch.setitem(C.TEXTOS["oferta"], "asunto", C.TEXTOS["oferta"]["asunto"] + " (cambiado)")
    assert C.plantilla_validada(con, did, "oferta") is None                        # texto distinto = hay que validarlo otra vez

def test_envio_por_los_dos_canales_con_consentimiento(mundo):
    con, did, admin, emp, tp = mundo
    rid = preparar_una(mundo)
    C.validar_plantilla(con, did, "oferta", admin)
    res = C.aprobar_y_enviar(con, did, rid, emp, HOY)
    assert res["canales"] == ["email", "whatsapp"] and res["modo"] == "simulado"
    envios = {e["canal"]: e for e in con.execute("SELECT * FROM envio")}
    assert envios["email"]["destinatario"] == "ok@ejemplo.test" and envios["whatsapp"]["destinatario"] == "627181521"
    assert envios["email"]["modo"] == "simulado" and envios["email"]["aprobado_por"] == emp
    assert con.execute("SELECT estado FROM renovacion").fetchone()[0] == "enviada"
    with pytest.raises(C.ErrorNegocio, match="Ya se envió"):                       # no se puede enviar dos veces
        C.aprobar_y_enviar(con, did, rid, emp, HOY)
    assert con.execute("SELECT COUNT(*) FROM envio").fetchone()[0] == 2

def test_whatsapp_solo_con_consentimiento(mundo):
    con, did, admin, emp, tp = mundo
    rid = preparar_una(mundo, wa="No")
    C.validar_plantilla(con, did, "oferta", admin)
    assert C.aprobar_y_enviar(con, did, rid, emp, HOY)["canales"] == ["email"]

def test_sin_correo_va_solo_por_whatsapp(mundo):
    con, did, admin, emp, tp = mundo
    rid = preparar_una(mundo, email=None)
    C.validar_plantilla(con, did, "oferta", admin)
    assert C.aprobar_y_enviar(con, did, rid, emp, HOY)["canales"] == ["whatsapp"]

def test_no_se_envia_la_renovacion_retenida(mundo):
    con, did, admin, emp, tp = mundo
    montar(mundo, [cli("C1")], [pol("A1")], [of("A1","B",50)], [["R1","R1/1","A1","Impagado",50]])
    rid = con.execute("SELECT id FROM renovacion").fetchone()[0]
    C.validar_plantilla(con, did, "oferta", admin)
    with pytest.raises(C.ErrorNegocio):
        C.aprobar_y_enviar(con, did, rid, emp, HOY)

def test_no_se_ofrecen_opciones_pasado_el_limite(mundo):
    con, did, admin, emp, tp = mundo
    montar(mundo, [cli("C1")], [pol("A1", dias=45)], [of("A1","B",50)])
    rid = con.execute("SELECT id FROM renovacion").fetchone()[0]
    C.validar_plantilla(con, did, "oferta", admin)
    with pytest.raises(C.ErrorNegocio, match="último día"):
        C.aprobar_y_enviar(con, did, rid, emp, HOY + timedelta(days=20))          # 45-20 = 25 días: ya no se puede cambiar

def test_usuario_de_otro_despacho_no_puede_aprobar(mundo):
    con, did, admin, emp, tp = mundo
    rid = preparar_una(mundo)
    d2, a2 = crear_despacho(con, "Otro")
    C.validar_plantilla(con, did, "oferta", admin)
    with pytest.raises(C.ErrorNegocio):
        C.aprobar_y_enviar(con, did, rid, a2, HOY)

# ---------- contenido de los mensajes ----------
def test_correo_con_marca_del_despacho_precios_y_sin_mencionar_la_app(mundo):
    con, did, admin, emp, tp = mundo
    montar(mundo, [cli("C1", nombre="<script>alert(1)</script>")], [pol("A1", total=100)], [of("A1","B",80,"Sin coche de sustitución")])
    reno = con.execute("SELECT * FROM renovacion").fetchone()
    m = C.componer(con, did, reno)
    assert "Despacho Test" in m["html"] and "80,00 €" in m["html"] and "20,00 €" in m["html"] and "Sin coche de sustitución" in m["html"]
    assert "<script>" not in m["html"] and "&lt;script&gt;" in m["html"]                       # el nombre se escapa
    for prohibida in ("SaaS", "Claude", "Anthropic", "plataforma"):
        assert prohibida.lower() not in (m["html"] + m["wa"] + m["asunto"]).lower()
    assert "No cambiar" in m["html"] and "Prefiero que me llamen" in m["html"] and "Cambiar a la opción 1" in m["html"]
    assert "opción 2" not in m["html"]                                                          # solo hay una opción

def test_sin_mejora_recuerda_lo_que_tiene_y_solo_ofrece_llamar(mundo):
    con, did, admin, emp, tp = mundo
    montar(mundo, [cli("C1")], [pol("A1")])
    con.execute("INSERT INTO garantia(despacho_id,num_poliza,garantia,capital_limite,incluida) VALUES (?,?,?,?,1)", (did, "A1", "Daños propios", "60.000 €"))
    con.execute("UPDATE renovacion SET tipo='sin_mejora', estado='preparada'")
    m = C.componer(con, did, con.execute("SELECT * FROM renovacion").fetchone())
    assert "sigue siendo una buena opción" in m["html"] and "Daños propios" in m["html"] and "60.000 €" in m["html"]
    assert "Cambiar a la opción" not in m["html"] and "Prefiero que me llamen" in m["html"]

# ---------- respuesta del cliente ----------
def enviar_y_tokens(mundo):
    con, did, admin, emp, tp = mundo
    rid = preparar_una(mundo)
    C.validar_plantilla(con, did, "oferta", admin)
    C.aprobar_y_enviar(con, did, rid, emp, HOY)
    return rid, {t["accion"]: t["token"] for t in con.execute("SELECT * FROM token_respuesta")}

def test_tokens_solo_de_las_acciones_que_existen(mundo):
    rid, toks = enviar_y_tokens(mundo)
    assert set(toks) == {"cambiar_1", "no_cambiar", "llamar"}                    # una sola opción: no hay cambiar_2
    assert len(set(toks.values())) == 3 and all(len(t) >= 20 for t in toks.values())

def test_primera_respuesta_vale_y_el_resto_se_rechaza(mundo):
    con, did, admin, emp, tp = mundo
    rid, toks = enviar_y_tokens(mundo)
    info = C.responder(con, toks["cambiar_1"], HOY)
    r = con.execute("SELECT * FROM renovacion WHERE id=?", (rid,)).fetchone()
    assert r["estado"] == "respondida" and r["respuesta_accion"] == "cambiar_1" and "(B, 80,00 €)" in r["respuesta_detalle"]
    for t in toks.values():
        with pytest.raises(C.ErrorNegocio, match="Ya recibimos"):
            C.responder(con, t, HOY)

def test_enlace_caducado_y_enlace_inventado(mundo):
    con, did, admin, emp, tp = mundo
    rid, toks = enviar_y_tokens(mundo)
    with pytest.raises(C.ErrorNegocio, match="caducado"):
        C.responder(con, toks["llamar"], HOY + timedelta(days=16))               # límite = vencimiento − 30 = hoy + 15
    with pytest.raises(C.ErrorNegocio, match="no es válido"):
        C.responder(con, "inventado", HOY)
    assert con.execute("SELECT estado FROM renovacion").fetchone()[0] == "enviada"

# ---------- cifras con el export de ejemplo, calculadas aparte con pandas ----------
def test_renovaciones_del_ejemplo_coinciden_con_un_calculo_independiente():
    con = conectar(); did, uid = crear_despacho(con, "Piloto")
    importar(con, did, "export_ejemplo_correduria.xlsx", uid); R.detectar(con, did, HOY)
    pol_df = pd.read_excel("export_ejemplo_correduria.xlsx", sheet_name="POLIZAS")
    pol_df["dias"] = (pd.to_datetime(pol_df["FECHA_VENCIMIENTO"]) - pd.Timestamp(HOY)).dt.days
    elegibles = pol_df[(pol_df.ESTADO == "En vigor") & (pol_df.RENOVABLE == "Sí") & (pol_df.dias >= 0) &
                       ((pol_df.dias <= 60) | (pol_df.PRIMA_RENOVACION_COMPAÑIA.notna() & (pol_df.dias <= 90)))]
    assert con.execute("SELECT COUNT(*) FROM renovacion").fetchone()[0] == len(elegibles)
    assert {r["num_poliza"] for r in con.execute("SELECT num_poliza FROM renovacion")} == set(elegibles.NUM_POLIZA)
    salud_vida = elegibles[elegibles.RAMO.isin(["Salud", "Vida"]) & (elegibles.dias >= 30)]
    avisos = con.execute("SELECT COUNT(*) FROM renovacion WHERE tipo='aviso'").fetchone()[0]
    assert avisos <= len(salud_vida)
    assert con.execute("SELECT COUNT(*) FROM renovacion WHERE tipo='fuera_plazo'").fetchone()[0] <= (elegibles.dias < 30).sum()
    assert con.execute("SELECT COUNT(*) FROM envio").fetchone()[0] == 0

# ---------- pantallas ----------
@pytest.fixture
def web(mundo):
    con, did, admin, emp, tp = mundo
    rid = preparar_una(mundo)
    app = crear_app(con, did, hoy=HOY); app.config["TESTING"] = True
    return con, did, admin, emp, rid, app

def como(app, uid):
    c = app.test_client(); c.get(f"/entrar/{uid}"); return c

def test_flujo_completo_por_pantalla(web):
    con, did, admin, emp, rid, app = web
    a, e = como(app, admin), como(app, emp)
    assert b"Texto sin validar" in e.get(f"/renovacion/{rid}").data
    assert e.post("/texto/oferta/validar").status_code == 403                    # el empleado no valida
    assert con.execute("SELECT COUNT(*) FROM plantilla_validacion").fetchone()[0] == 0
    a.post("/texto/oferta/validar", data={"volver": rid})
    html = e.get(f"/renovacion/{rid}").get_data(as_text=True)
    assert "Texto validado" in html and "Aprobar y enviar" in html and "Despacho Test" in html
    r = e.post(f"/renovacion/{rid}/aprobar", follow_redirects=True)
    assert "modo simulado" in r.get_data(as_text=True) and con.execute("SELECT COUNT(*) FROM envio").fetchone()[0] == 2
    assert "Enviados" not in e.get("/renovaciones").get_data(as_text=True)       # el empleado no ve la bandeja de salida
    assert e.get("/salida").status_code == 403 and a.get("/salida").status_code == 200

def test_pagina_publica_de_respuesta(web):
    con, did, admin, emp, rid, app = web
    como(app, admin).post("/texto/oferta/validar")
    como(app, emp).post(f"/renovacion/{rid}/aprobar")
    tok = con.execute("SELECT token FROM token_respuesta WHERE accion='cambiar_1'").fetchone()[0]
    publico = app.test_client()                                                  # sin sesión
    g = publico.get(f"/r/{tok}"); html = g.get_data(as_text=True)
    assert g.status_code == 200 and "Confirmar" in html and "80,00 €" in html
    assert "ok@ejemplo.test" not in html and "627181521" not in html             # no enseña datos personales
    assert con.execute("SELECT estado FROM renovacion").fetchone()[0] == "enviada"   # el GET no registra nada (antivirus de correo)
    p = publico.post(f"/r/{tok}"); assert p.status_code == 200 and "Gracias" in p.get_data(as_text=True)
    assert con.execute("SELECT estado FROM renovacion").fetchone()[0] == "respondida"
    assert publico.post(f"/r/{tok}").status_code == 410
    assert publico.get("/r/inventado").status_code == 410
    assert publico.get("/clientes").status_code == 200                           # la demo entra sola como administrador; la página pública no da acceso a nada más
