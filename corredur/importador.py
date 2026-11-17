"""Carga del Excel de exportación a la base de datos.
Reglas: nunca se borra nada; lo que no aparece en el último export se marca; no se importa el IBAN."""
import json
from datetime import datetime, date
import openpyxl
from .db import ahora, registrar

def _f(v):
    if v is None or v == "":
        return None
    if isinstance(v, (datetime, date)):
        return v.date().isoformat() if isinstance(v, datetime) else v.isoformat()
    if isinstance(v, str):
        return v.strip() or None
    return v

def _si_no(v):
    v = _f(v)
    if v is None:
        return None
    return 1 if str(v).strip().lower() in ("sí", "si", "s", "1", "true") else 0

def _num(v):
    v = _f(v)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("€", "").replace("%", "").strip()
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        return float(s)
    except ValueError:
        return None

# columna del Excel -> (campo, conversor). El IBAN y el banco NO se importan (minimización de datos).
MAPAS = {
 "CLIENTES": ("cliente", ["cod"], {
   "COD_CLIENTE":("cod",_f),"TIPO":("tipo",_f),"NIF_CIF":("nif",_f),"NOMBRE":("nombre",_f),
   "APELLIDO_1":("apellido1",_f),"APELLIDO_2":("apellido2",_f),"RAZON_SOCIAL":("razon_social",_f),
   "SEXO":("sexo",_f),"FECHA_NACIMIENTO":("fecha_nacimiento",_f),"ESTADO_CIVIL":("estado_civil",_f),
   "PROFESION":("profesion",_f),"DIRECCION":("direccion",_f),"COD_POSTAL":("cod_postal",_f),
   "POBLACION":("poblacion",_f),"PROVINCIA":("provincia",_f),"TELEFONO_MOVIL":("telefono_movil",_f),
   "TELEFONO_2":("telefono_2",_f),"EMAIL":("email",_f),"ACEPTA_WHATSAPP":("acepta_whatsapp",_si_no),
   "ACEPTA_COMUNICACIONES_COMERCIALES":("acepta_comerciales",_si_no),"FECHA_ALTA":("fecha_alta",_f),
   "MEDIADOR_ASIGNADO":("mediador",_f)}),
 "POLIZAS": ("poliza", ["num_poliza"], {
   "COD_POLIZA":("cod",_f),"NUM_POLIZA":("num_poliza",_f),"COD_CLIENTE":("cod_cliente",_f),"RAMO":("ramo",_f),
   "PRODUCTO":("producto",_f),"COMPAÑIA":("compania",_f),"FECHA_EFECTO":("fecha_efecto",_f),
   "FECHA_VENCIMIENTO":("fecha_vencimiento",_f),"FECHA_ALTA":("fecha_alta",_f),"ESTADO":("estado",_f),
   "FORMA_PAGO":("forma_pago",_f),"PRIMA_NETA":("prima_neta",_num),"IMPUESTOS_Y_RECARGOS":("impuestos",_num),
   "PRIMA_TOTAL_ANUAL":("prima_total",_num),"PRIMA_RENOVACION_COMPAÑIA":("prima_renovacion",_num),
   "FECHA_AVISO_COMPAÑIA":("fecha_aviso",_f),"COMISION_PCT":("comision_pct",_num),
   "COMISION_ANUAL":("comision_anual",_num),"MEDIADOR":("mediador",_f),"RENOVABLE":("renovable",_si_no),
   "ORIGEN":("origen",_f),"FECHA_ANULACION":("fecha_anulacion",_f),"MOTIVO_ANULACION":("motivo_anulacion",_f),
   "OBSERVACIONES":("observaciones",_f)}),
 "GARANTIAS": ("garantia", ["num_poliza","garantia"], {
   "NUM_POLIZA":("num_poliza",_f),"GARANTIA":("garantia",_f),"CAPITAL_LIMITE":("capital_limite",_f),
   "FRANQUICIA":("franquicia",_f),"INCLUIDA":("incluida",_si_no)}),
 "RECIBOS": ("recibo", ["cod"], {
   "COD_RECIBO":("cod",_f),"NUM_RECIBO":("num_recibo",_f),"NUM_POLIZA":("num_poliza",_f),
   "COD_CLIENTE":("cod_cliente",_f),"FECHA_EMISION":("fecha_emision",_f),"INICIO_COBERTURA":("inicio_cobertura",_f),
   "FIN_COBERTURA":("fin_cobertura",_f),"PRIMA_NETA":("prima_neta",_num),"IMPUESTOS_Y_RECARGOS":("impuestos",_num),
   "PRIMA_TOTAL":("prima_total",_num),"COMISION":("comision",_num),"ESTADO_COBRO":("estado_cobro",_f),
   "FECHA_COBRO":("fecha_cobro",_f),"FORMA_COBRO":("forma_cobro",_f),"GESTOR_COBRO":("gestor_cobro",_f),
   "LIQUIDACION":("liquidacion",_f)}),
 "SINIESTROS": ("siniestro", ["cod"], {
   "COD_SINIESTRO":("cod",_f),"NUM_EXPEDIENTE_PROPIO":("num_expediente_propio",_f),
   "NUM_EXPEDIENTE_COMPAÑIA":("num_expediente_compania",_f),"NUM_POLIZA":("num_poliza",_f),
   "COD_CLIENTE":("cod_cliente",_f),"RAMO":("ramo",_f),"FECHA_OCURRENCIA":("fecha_ocurrencia",_f),
   "FECHA_APERTURA":("fecha_apertura",_f),"TIPO":("tipo",_f),"ESTADO":("estado",_f),"RESERVA":("reserva",_num),
   "IMPORTE_PAGADO":("importe_pagado",_num),"CULPABILIDAD":("culpabilidad",_f),"TRAMITADOR":("tramitador",_f),
   "FECHA_CIERRE":("fecha_cierre",_f),"ULTIMA_NOTA":("ultima_nota",_f)}),
 "VINCULOS": ("vinculo", ["cod_origen","cod_destino"], {
   "COD_CLIENTE_ORIGEN":("cod_origen",_f),"COD_CLIENTE_DESTINO":("cod_destino",_f),
   "RELACION":("relacion",_f),"RELACION_INVERSA":("relacion_inversa",_f)}),
 "DOCUMENTOS": ("documento", ["cod"], {
   "COD_DOCUMENTO":("cod",_f),"TIPO_DOCUMENTO":("tipo",_f),"COD_CLIENTE":("cod_cliente",_f),
   "NUM_POLIZA":("num_poliza",_f),"NUM_SINIESTRO":("num_siniestro",_f),"NUM_RECIBO":("num_recibo",_f),
   "NOMBRE_FICHERO":("nombre_fichero",_f),"RUTA":("ruta",_f),"FECHA":("fecha",_f),
   "TAMAÑO_KB":("tamano_kb",_num),"FECHA_CADUCIDAD":("fecha_caducidad",_f)}),
 "OFERTAS_MANUAL": ("oferta_manual", ["num_poliza","compania_oferta","fecha_oferta"], {
   "NUM_POLIZA":("num_poliza",_f),"COMPAÑIA_OFERTA":("compania_oferta",_f),
   "PRIMA_TOTAL_ANUAL":("prima_total_anual",_num),"FECHA_OFERTA":("fecha_oferta",_f),
   "NOTAS_COBERTURA":("notas_cobertura",_f)}),
}
CON_MARCA = {"cliente", "poliza"}   # tablas con "no aparece en el último export"

def _filas(ws):
    it = ws.iter_rows(values_only=True)
    cab = next(it, None)
    if not cab:
        return
    cab = [str(c).strip() if c is not None else "" for c in cab]
    for fila in it:
        if all(v is None or v == "" for v in fila):
            continue
        yield dict(zip(cab, fila))

def importar(con, despacho_id, ruta_excel, usuario_id=None):
    wb = openpyxl.load_workbook(ruta_excel, data_only=True)
    cur = con.execute("INSERT INTO importacion(despacho_id,fecha,fichero,usuario_id) VALUES (?,?,?,?)",
                      (despacho_id, ahora(), str(ruta_excel).split("/")[-1], usuario_id))
    imp_id = cur.lastrowid
    resumen = {"hojas": {}, "rechazadas": []}
    try:
        for hoja, (tabla, claves, mapa) in MAPAS.items():
            if hoja not in wb.sheetnames:
                continue
            nuevas = actualizadas = 0
            for n, fila in enumerate(_filas(wb[hoja]), start=2):
                datos = {}
                for col, (campo, conv) in mapa.items():
                    if col in fila:
                        datos[campo] = conv(fila[col])
                if any(datos.get(k) is None for k in claves):
                    resumen["rechazadas"].append(f"{hoja} fila {n}: falta {'/'.join(claves)}")
                    continue
                datos["despacho_id"] = despacho_id
                if tabla in CON_MARCA:
                    datos["importacion_id"] = imp_id
                    datos["no_en_ultimo_export"] = 0
                clave_where = " AND ".join(f"{k}=?" for k in ["despacho_id"] + claves)
                existe = con.execute(f"SELECT 1 FROM {tabla} WHERE {clave_where}",
                                     [despacho_id] + [datos[k] for k in claves]).fetchone()
                cols = list(datos)
                if existe:
                    sets = ", ".join(f"{c}=?" for c in cols if c not in claves and c != "despacho_id")
                    con.execute(f"UPDATE {tabla} SET {sets} WHERE {clave_where}",
                                [datos[c] for c in cols if c not in claves and c != "despacho_id"]
                                + [despacho_id] + [datos[k] for k in claves])
                    actualizadas += 1
                else:
                    con.execute(f"INSERT INTO {tabla}({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                                [datos[c] for c in cols])
                    nuevas += 1
            resumen["hojas"][hoja] = {"nuevas": nuevas, "actualizadas": actualizadas}
            if tabla in CON_MARCA:   # lo que no vino en este export se marca, nunca se borra
                con.execute(f"UPDATE {tabla} SET no_en_ultimo_export=1 WHERE despacho_id=? AND importacion_id<>?",
                            (despacho_id, imp_id))
        _importar_riesgos(con, despacho_id, wb, resumen)
        con.execute("UPDATE importacion SET resumen_json=? WHERE id=?", (json.dumps(resumen, ensure_ascii=False), imp_id))
        registrar(con, despacho_id, usuario_id, "importacion", "importacion", json.dumps(resumen["hojas"], ensure_ascii=False))
        con.commit()
    except Exception:
        con.rollback()
        raise
    resumen["importacion_id"] = imp_id
    return resumen

def _importar_riesgos(con, despacho_id, wb, resumen):
    """Los riesgos varían según el ramo (coche, vivienda, salud…): los datos propios se guardan como JSON."""
    if "RIESGOS" not in wb.sheetnames:
        return
    nuevas = actualizadas = 0
    for n, fila in enumerate(_filas(wb["RIESGOS"]), start=2):
        cod, num, tipo = _f(fila.get("COD_RIESGO")), _f(fila.get("NUM_POLIZA")), _f(fila.get("TIPO_RIESGO"))
        if not cod:
            resumen["rechazadas"].append(f"RIESGOS fila {n}: falta COD_RIESGO")
            continue
        extra = {k: _f(v) for k, v in fila.items() if k not in ("COD_RIESGO", "NUM_POLIZA", "TIPO_RIESGO") and _f(v) is not None}
        existe = con.execute("SELECT 1 FROM riesgo WHERE despacho_id=? AND cod=?", (despacho_id, cod)).fetchone()
        js = json.dumps(extra, ensure_ascii=False)
        if existe:
            con.execute("UPDATE riesgo SET num_poliza=?,tipo=?,datos_json=? WHERE despacho_id=? AND cod=?",
                        (num, tipo, js, despacho_id, cod)); actualizadas += 1
        else:
            con.execute("INSERT INTO riesgo(despacho_id,cod,num_poliza,tipo,datos_json) VALUES (?,?,?,?,?)",
                        (despacho_id, cod, num, tipo, js)); nuevas += 1
    resumen["hojas"]["RIESGOS"] = {"nuevas": nuevas, "actualizadas": actualizadas}
