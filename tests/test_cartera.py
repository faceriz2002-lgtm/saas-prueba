import sqlite3
from datetime import date, datetime
import openpyxl
import pytest
from corredur.db import conectar, crear_despacho
from corredur.importador import importar
from corredur import salud
from corredur.validadores import nif_valido, email_valido, movil_valido

HOY = date(2026, 11, 14)
EXPORT = "export_ejemplo_correduria.xlsx"

CAB_CLI = ["COD_CLIENTE","TIPO","NIF_CIF","NOMBRE","APELLIDO_1","APELLIDO_2","RAZON_SOCIAL","FECHA_NACIMIENTO",
           "TELEFONO_MOVIL","EMAIL","ACEPTA_WHATSAPP","IBAN"]
CAB_POL = ["COD_POLIZA","NUM_POLIZA","COD_CLIENTE","RAMO","ESTADO","FECHA_EFECTO","FECHA_VENCIMIENTO",
           "PRIMA_NETA","IMPUESTOS_Y_RECARGOS","PRIMA_TOTAL_ANUAL","COMISION_PCT","COMISION_ANUAL"]
CAB_REC = ["COD_RECIBO","NUM_RECIBO","NUM_POLIZA","ESTADO_COBRO","PRIMA_TOTAL"]
CAB_SIN = ["COD_SINIESTRO","NUM_POLIZA"]

def d(y, m, dd): return datetime(y, m, dd)

def excel(tmp_path, clientes, polizas, recibos=(), siniestros=(), nombre="e.xlsx"):
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    for hoja, cab, filas in [("CLIENTES",CAB_CLI,clientes),("POLIZAS",CAB_POL,polizas),
                             ("RECIBOS",CAB_REC,recibos),("SINIESTROS",CAB_SIN,siniestros)]:
        ws = wb.create_sheet(hoja); ws.append(cab)
        for f in filas: ws.append(f)
    ruta = tmp_path / nombre; wb.save(ruta); return ruta

def _nif_unico(cod):
    n = 30000000 + sum(ord(ch) * (i + 1) for i, ch in enumerate(str(cod))) * 7
    return f"{n}{'TRWAGMYFPDXBNJZSQVHLCKE'[n % 23]}"

def cli_ok(cod, nif=None, email=None, movil="627181521", wa="Sí", nombre=None, ap=None, fnac=d(1980,1,1)):
    nif = nif or _nif_unico(cod); nombre = nombre or f"Nombre{cod}"; ap = ap or f"Apellido{cod}"
    return [cod,"Persona física",nif,nombre,ap,"",None,fnac,movil,email or f"{str(cod).lower()}@ejemplo.test",wa,"ES00 0000 0000 0000 0000 0000"]

def pol_ok(num, cod, estado="En vigor", ef=d(2026,3,1), ve=d(2027,3,1), neta=100, imp=6, total=106, pct=15, com=15):
    return ["P-"+num, num, cod, "Hogar", estado, ef, ve, neta, imp, total, pct, com]

@pytest.fixture
def entorno(tmp_path):
    con = conectar(); did, uid = crear_despacho(con, "Test"); return con, did, uid, tmp_path

def reglas(con, did):
    return {(r["regla"], r["ref"]) for r in con.execute("SELECT regla, ref FROM incidencia_salud WHERE despacho_id=? AND estado='abierta'", (did,))}

# ---------- validadores (con casos reales conocidos) ----------
def test_validadores():
    assert nif_valido("12345678Z") and nif_valido("X1234567L") and nif_valido("Q2826000H") and nif_valido("A58818501")
    assert not nif_valido("12345678A") and not nif_valido("") and not nif_valido("B45168000")
    assert email_valido("a.b@x.es") and not email_valido("a@b") and not email_valido("sin arroba")
    assert movil_valido("627 181 521") and movil_valido("+34 627181521") and not movil_valido("976 333 535")

# ---------- cartera limpia: cero errores ----------
def test_cartera_limpia_sin_incidencias(entorno):
    con, did, uid, tp = entorno
    ruta = excel(tp, [cli_ok("C1")], [pol_ok("A1","C1")])
    importar(con, did, ruta, uid)
    assert salud.revisar(con, did, hoy=HOY)["abiertas"] == 0

# ---------- cada error sembrado se detecta, y solo ese ----------
def test_errores_sembrados(entorno):
    con, did, uid, tp = entorno
    clientes = [
        cli_ok("C1"),
        cli_ok("C2", nif="12345678A"),                               # NIF inválido
        cli_ok("C3", nif="00000000T", ap="Ruiz"), cli_ok("C4", nif="00000000T", nombre="Luis", ap="Mena"),  # NIF repetido
        cli_ok("C5", nombre="Pepe", ap="Dup", nif="87654321X", fnac=d(1990,5,5)),
        cli_ok("C6", nombre="Pepe", ap="Dup", nif="11111111H", fnac=d(1990,5,5)),   # posible duplicado
        ["C7","Persona física","22222222J","Sin","Contacto","",None,d(1970,1,1),None,None,"No",None],  # sin contacto
        cli_ok("C8", email="no-es-correo"),                          # email inválido
        cli_ok("C9", movil="976333535", wa="Sí"),                    # móvil inválido + whatsapp sin móvil
    ]
    polizas = [
        pol_ok("A1","C1"),
        pol_ok("A2","C1", ve=d(2026,10,1), ef=d(2025,10,1)),         # vigente vencida
        pol_ok("A3","C1", estado="Anulada"),
        pol_ok("A4","C1", estado="Suspendida"),
        pol_ok("A5","ZZ"),                                           # sin cliente
        pol_ok("A6","C1", ef=d(2026,5,1), ve=d(2026,4,1)),           # fechas incoherentes
        pol_ok("A7","C1", total=200),                                # prima incoherente
        pol_ok("A8","C1", com=40),                                   # comisión incoherente (100×15 %=15 ≠ 40)
    ]
    recibos = [["R1","R1/1","A1","Cobrado",106],["R2","R2/1","A1","Devuelto",50],
               ["R3","R3/1","A1","Impagado",50],["R4","R4/1","NOEXISTE","Cobrado",10]]
    sin = [["S1","A1"],["S2","NOEXISTE"]]
    importar(con, did, excel(tp, clientes, polizas, recibos, sin), uid)
    salud.revisar(con, did, hoy=HOY)
    esperadas = {
        ("NIF_INVALIDO","C2"),
        ("NIF_DUPLICADO","C3"),("NIF_DUPLICADO","C4"),
        ("CLIENTE_DUPLICADO_POSIBLE","C5"),("CLIENTE_DUPLICADO_POSIBLE","C6"),
        ("SIN_CONTACTO","C7"),
        ("EMAIL_INVALIDO","C8"),
        ("MOVIL_INVALIDO","C9"),("WHATSAPP_SIN_MOVIL","C9"),
        ("POLIZA_VIGENTE_VENCIDA","A2"),
        ("POLIZA_ANULADA_SUSPENDIDA","A3"),("POLIZA_ANULADA_SUSPENDIDA","A4"),
        ("POLIZA_SIN_CLIENTE","A5"),
        ("POLIZA_FECHAS_INCOHERENTES","A6"),("POLIZA_VIGENTE_VENCIDA","A6"),   # A6 además venció en abril
        ("POLIZA_PRIMA_INCOHERENTE","A7"),
        ("POLIZA_COMISION_INCOHERENTE","A8"),
        ("RECIBO_DEVUELTO","R2"),("RECIBO_DEVUELTO","R3"),("RECIBO_SIN_POLIZA","R4"),
        ("SINIESTRO_SIN_POLIZA","S2"),
    }
    obtenidas = reglas(con, did)
    assert esperadas <= obtenidas, f"No detectado: {esperadas - obtenidas}"
    inesperadas = obtenidas - esperadas
    assert not inesperadas, f"Falsos positivos: {inesperadas}"

# ---------- importación ----------
def test_importacion_coincide_con_excel_y_no_guarda_iban():
    con = conectar(); did, uid = crear_despacho(con, "Piloto")
    r = importar(con, did, EXPORT, uid)
    wb = openpyxl.load_workbook(EXPORT, data_only=True)
    tablas = {"CLIENTES":"cliente","POLIZAS":"poliza","GARANTIAS":"garantia","RECIBOS":"recibo","SINIESTROS":"siniestro",
              "VINCULOS":"vinculo","DOCUMENTOS":"documento","OFERTAS_MANUAL":"oferta_manual","RIESGOS":"riesgo"}
    for hoja, tabla in tablas.items():
        filas = wb[hoja].max_row - 1
        n = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        assert n == filas, f"{hoja}: Excel {filas} filas, base de datos {n}"
    assert r["rechazadas"] == []
    # cifras económicas idénticas
    exc = sum(row[0] or 0 for row in wb["POLIZAS"].iter_rows(min_row=2, min_col=14, max_col=14, values_only=True))
    bd = con.execute("SELECT SUM(prima_total) FROM poliza").fetchone()[0]
    assert abs(exc - bd) < 0.01
    todo = " ".join(str(tuple(f)) for t in tablas.values() for f in con.execute(f"SELECT * FROM {t}"))
    assert "ES72" not in todo and "ES93" not in todo        # ningún IBAN en la base de datos

def test_reimportar_no_duplica_y_marca_lo_que_falta(entorno):
    con, did, uid, tp = entorno
    r1 = excel(tp, [cli_ok("C1"), cli_ok("C2")], [pol_ok("A1","C1"), pol_ok("A2","C2")], nombre="1.xlsx")
    importar(con, did, r1, uid)
    r2 = excel(tp, [cli_ok("C1")], [pol_ok("A1","C1")], nombre="2.xlsx")        # A2 y C2 ya no vienen
    res = importar(con, did, r2, uid)
    assert con.execute("SELECT COUNT(*) FROM poliza").fetchone()[0] == 2          # nunca se borra
    assert con.execute("SELECT no_en_ultimo_export FROM poliza WHERE num_poliza='A2'").fetchone()[0] == 1
    assert con.execute("SELECT no_en_ultimo_export FROM poliza WHERE num_poliza='A1'").fetchone()[0] == 0
    assert res["hojas"]["POLIZAS"] == {"nuevas": 0, "actualizadas": 1}
    salud.revisar(con, did, hoy=HOY)
    assert ("POLIZA_NO_EN_EXPORT","A2") in reglas(con, did) and ("CLIENTE_NO_EN_EXPORT","C2") in reglas(con, did)

def test_fila_sin_clave_se_rechaza_y_se_informa(entorno):
    con, did, uid, tp = entorno
    ruta = excel(tp, [cli_ok("C1"), cli_ok(None)], [pol_ok("A1","C1")])
    res = importar(con, did, ruta, uid)
    assert len(res["rechazadas"]) == 1 and "CLIENTES" in res["rechazadas"][0]

# ---------- ciclo de vida de las incidencias ----------
def test_incidencia_se_cierra_sola_al_corregirse(entorno):
    con, did, uid, tp = entorno
    importar(con, did, excel(tp, [cli_ok("C1", nif="12345678A")], [pol_ok("A1","C1")], nombre="1.xlsx"), uid)
    assert salud.revisar(con, did, hoy=HOY)["abiertas"] == 1
    importar(con, did, excel(tp, [cli_ok("C1", nif="12345678Z")], [pol_ok("A1","C1")], nombre="2.xlsx"), uid)
    r = salud.revisar(con, did, hoy=HOY)
    assert r == {"abiertas": 0, "nuevas": 0, "resueltas": 1}
    importar(con, did, excel(tp, [cli_ok("C1", nif="12345678A")], [pol_ok("A1","C1")], nombre="3.xlsx"), uid)
    assert salud.revisar(con, did, hoy=HOY)["abiertas"] == 1                       # se reabre

def test_revision_repetida_es_estable(entorno):
    con, did, uid, tp = entorno
    importar(con, did, excel(tp, [cli_ok("C1", nif="12345678A")], [pol_ok("A1","C1")]), uid)
    salud.revisar(con, did, hoy=HOY)
    r = salud.revisar(con, did, hoy=HOY)
    assert r == {"abiertas": 1, "nuevas": 0, "resueltas": 0}

# ---------- aislamiento entre despachos y registro de actividad ----------
def test_cada_despacho_solo_ve_lo_suyo(tmp_path):
    con = conectar()
    d1, u1 = crear_despacho(con, "Uno"); d2, u2 = crear_despacho(con, "Dos")
    importar(con, d1, excel(tmp_path, [cli_ok("C1", nif="12345678A")], [pol_ok("A1","C1")], nombre="1.xlsx"), u1)
    importar(con, d2, excel(tmp_path, [cli_ok("C1")], [pol_ok("A1","C1")], nombre="2.xlsx"), u2)
    assert salud.revisar(con, d1, hoy=HOY)["abiertas"] == 1
    assert salud.revisar(con, d2, hoy=HOY)["abiertas"] == 0
    assert con.execute("SELECT COUNT(*) FROM cliente").fetchone()[0] == 2

def test_registro_de_actividad_es_inmutable():
    con = conectar(); did, uid = crear_despacho(con, "Test")
    assert con.execute("SELECT COUNT(*) FROM registro_actividad").fetchone()[0] >= 1
    with pytest.raises(sqlite3.DatabaseError):
        con.execute("UPDATE registro_actividad SET accion='x'")
    with pytest.raises(sqlite3.DatabaseError):
        con.execute("DELETE FROM registro_actividad")

def test_importacion_y_revision_quedan_registradas():
    con = conectar(); did, uid = crear_despacho(con, "Test")
    importar(con, did, EXPORT, uid); salud.revisar(con, did, hoy=HOY, usuario_id=uid)
    acciones = {r[0] for r in con.execute("SELECT accion FROM registro_actividad")}
    assert {"importacion", "revision_salud"} <= acciones
