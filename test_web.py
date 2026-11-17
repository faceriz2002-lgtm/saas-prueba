import re
from datetime import date
import pytest
from corredur.db import conectar, crear_despacho, crear_usuario
from corredur.importador import importar
from corredur import salud
from corredur.web import crear_app

HOY = date(2026, 11, 14)

@pytest.fixture(scope="module")
def mundo():
    con = conectar(); did, admin = crear_despacho(con, "Piloto")
    emp = crear_usuario(con, did, "Laura", "laura@despacho.test", "empleado", admin)
    importar(con, did, "export_ejemplo_correduria.xlsx", admin)
    salud.revisar(con, did, hoy=HOY, usuario_id=admin)
    app = crear_app(con, did, hoy=HOY); app.config["TESTING"] = True
    return con, did, admin, emp, app

def cliente_como(app, uid):
    c = app.test_client()
    c.get(f"/entrar/{uid}")
    return c

def test_todas_las_pantallas_cargan(mundo):
    con, did, admin, emp, app = mundo
    c = cliente_como(app, admin)
    assert c.get("/salud").status_code == 200 and c.get("/clientes").status_code == 200
    for r in con.execute("SELECT cod FROM cliente"):
        assert c.get(f"/cliente/{r['cod']}").status_code == 200, r["cod"]
    for r in con.execute("SELECT num_poliza FROM poliza"):
        assert c.get(f"/poliza/{r['num_poliza']}").status_code == 200, r["num_poliza"]
    for regla in salud.REGLAS:
        assert c.get(f"/salud/{regla}").status_code == 200, regla

def test_cifras_de_la_pantalla_coinciden_con_la_base(mundo):
    con, did, admin, emp, app = mundo
    html = cliente_como(app, admin).get("/salud").get_data(as_text=True)
    abiertas = con.execute("SELECT COUNT(*) FROM incidencia_salud WHERE estado='abierta'").fetchone()[0]
    assert f"<b>{abiertas}</b><span>errores abiertos" in html
    for regla, sev, n, desc in salud.resumen(con, did):
        assert desc in html and f"<b>{n}</b>" in html

def test_empleado_no_ve_salud_ni_comisiones(mundo):
    con, did, admin, emp, app = mundo
    c = cliente_como(app, emp)
    assert c.get("/salud").status_code == 403
    assert c.get("/salud/NIF_INVALIDO").status_code == 403
    html = c.get("/poliza/HG-2025-0001").get_data(as_text=True)
    assert "Comisión" not in html and "solo administrador" not in html
    assert "Salud de la cartera" not in c.get("/clientes").get_data(as_text=True)
    assert "Errores" not in c.get("/clientes").get_data(as_text=True)
    # y el administrador sí
    a = cliente_como(app, admin)
    assert "Comisión" in a.get("/poliza/HG-2025-0001").get_data(as_text=True)

def test_ficha_inexistente_da_404(mundo):
    con, did, admin, emp, app = mundo
    c = cliente_como(app, admin)
    assert c.get("/cliente/NOEXISTE").status_code == 404
    assert c.get("/poliza/NOEXISTE").status_code == 404
    assert c.get("/salud/REGLA_FALSA").status_code == 404

def test_avisos_visibles_en_polizas_con_problemas(mundo):
    con, did, admin, emp, app = mundo
    c = cliente_como(app, emp)
    anulada = con.execute("SELECT num_poliza FROM poliza WHERE estado='Anulada'").fetchone()[0]
    assert "Póliza anulada" in c.get(f"/poliza/{anulada}").get_data(as_text=True)
    vencida = con.execute("SELECT num_poliza FROM poliza WHERE estado='En vigor' AND fecha_vencimiento<'2026-11-14' LIMIT 1").fetchone()[0]
    assert "Figura en vigor pero venció" in c.get(f"/poliza/{vencida}").get_data(as_text=True)

def test_siniestros_solo_de_los_ultimos_dos_anios(mundo):
    con, did, admin, emp, app = mundo
    con.execute("INSERT INTO siniestro(despacho_id,cod,num_poliza,cod_cliente,fecha_ocurrencia,tipo,estado) VALUES (?,?,?,?,?,?,?)",
                (did, "SVIEJO", "HG-2025-0001", "C01001", "2022-01-10", "Siniestro antiguo muy viejo", "Cerrado"))
    con.commit()
    html = cliente_como(app, admin).get("/poliza/HG-2025-0001").get_data(as_text=True)
    assert "Siniestro antiguo muy viejo" not in html
    con.execute("DELETE FROM siniestro WHERE cod='SVIEJO'"); con.commit()

def test_busqueda_de_clientes(mundo):
    con, did, admin, emp, app = mundo
    c = cliente_como(app, emp)
    todos = c.get("/clientes").get_data(as_text=True).count('/cliente/C')
    filtrado = c.get("/clientes?q=C01001").get_data(as_text=True)
    assert 0 < filtrado.count('/cliente/C') < todos and "/cliente/C01001" in filtrado

def test_nada_se_ve_de_otro_despacho(mundo):
    con, did, admin, emp, app = mundo
    d2, a2 = crear_despacho(con, "Otro despacho")
    app2 = crear_app(con, d2, hoy=HOY)
    c = app2.test_client(); c.get(f"/entrar/{a2}")
    assert c.get("/cliente/C01001").status_code == 404 and c.get("/poliza/HG-2025-0001").status_code == 404
    assert "C01001" not in c.get("/clientes").get_data(as_text=True)
    c.get(f"/entrar/{admin}")        # un usuario de otro despacho no puede entrar aquí
    assert c.get("/cliente/C01001").status_code == 404

def test_arrancar_prepara_la_aplicacion_y_responde():
    import arrancar
    app = arrancar.preparar(":memory:"); app.config["TESTING"] = True
    c = app.test_client()
    for ruta in ("/salud", "/renovaciones", "/clientes", "/comisiones", "/salida"):
        assert c.get(ruta).status_code == 200, ruta
