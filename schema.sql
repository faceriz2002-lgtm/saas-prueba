-- Esquema de la base de datos (SQLite para la prueba; el SQL se mantiene portable a PostgreSQL).
-- Todas las tablas llevan despacho_id: cada correduría ve solo sus datos.
CREATE TABLE IF NOT EXISTS despacho (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, creado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS usuario (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL REFERENCES despacho(id),
  nombre TEXT NOT NULL, email TEXT NOT NULL,
  rol TEXT NOT NULL CHECK (rol IN ('administrador','empleado')));
CREATE TABLE IF NOT EXISTS importacion (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL REFERENCES despacho(id),
  fecha TEXT NOT NULL, fichero TEXT, usuario_id INTEGER, resumen_json TEXT);
CREATE TABLE IF NOT EXISTS cliente (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, cod TEXT NOT NULL,
  tipo TEXT, nif TEXT, nombre TEXT, apellido1 TEXT, apellido2 TEXT, razon_social TEXT,
  sexo TEXT, fecha_nacimiento TEXT, estado_civil TEXT, profesion TEXT,
  direccion TEXT, cod_postal TEXT, poblacion TEXT, provincia TEXT,
  telefono_movil TEXT, telefono_2 TEXT, email TEXT,
  acepta_whatsapp INTEGER, acepta_comerciales INTEGER, fecha_alta TEXT, mediador TEXT,
  no_en_ultimo_export INTEGER NOT NULL DEFAULT 0, importacion_id INTEGER,
  UNIQUE (despacho_id, cod));
CREATE TABLE IF NOT EXISTS poliza (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, cod TEXT NOT NULL,
  num_poliza TEXT NOT NULL, cod_cliente TEXT, ramo TEXT, producto TEXT, compania TEXT,
  fecha_efecto TEXT, fecha_vencimiento TEXT, fecha_alta TEXT, estado TEXT, forma_pago TEXT,
  prima_neta REAL, impuestos REAL, prima_total REAL, prima_renovacion REAL, fecha_aviso TEXT,
  comision_pct REAL, comision_anual REAL, mediador TEXT, renovable INTEGER, origen TEXT,
  fecha_anulacion TEXT, motivo_anulacion TEXT, observaciones TEXT,
  no_en_ultimo_export INTEGER NOT NULL DEFAULT 0, importacion_id INTEGER,
  -- Comisión (la fija la correduría, no el documento de la póliza). Las columnas «propia» y «colaborador» las escribe
  -- la aplicación; las «aplicada» se recalculan solas cuando cambia la prima neta o el porcentaje.
  comision_pct_propia REAL, colaborador TEXT, colaborador_pct REAL,
  comision_pct_aplicada REAL, comision_origen TEXT, comision_aplicada REAL,
  comision_colaborador REAL, comision_correduria REAL,
  UNIQUE (despacho_id, num_poliza));
CREATE TABLE IF NOT EXISTS riesgo (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, cod TEXT NOT NULL,
  num_poliza TEXT, tipo TEXT, datos_json TEXT, UNIQUE (despacho_id, cod));
CREATE TABLE IF NOT EXISTS garantia (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, num_poliza TEXT NOT NULL,
  garantia TEXT NOT NULL, capital_limite TEXT, franquicia TEXT, incluida INTEGER,
  UNIQUE (despacho_id, num_poliza, garantia));
CREATE TABLE IF NOT EXISTS recibo (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, cod TEXT NOT NULL,
  num_recibo TEXT, num_poliza TEXT, cod_cliente TEXT, fecha_emision TEXT,
  inicio_cobertura TEXT, fin_cobertura TEXT, prima_neta REAL, impuestos REAL, prima_total REAL,
  comision REAL, estado_cobro TEXT, fecha_cobro TEXT, forma_cobro TEXT, gestor_cobro TEXT,
  liquidacion TEXT, UNIQUE (despacho_id, cod));
CREATE TABLE IF NOT EXISTS siniestro (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, cod TEXT NOT NULL,
  num_expediente_propio TEXT, num_expediente_compania TEXT, num_poliza TEXT, cod_cliente TEXT,
  ramo TEXT, fecha_ocurrencia TEXT, fecha_apertura TEXT, tipo TEXT, estado TEXT,
  reserva REAL, importe_pagado REAL, culpabilidad TEXT, tramitador TEXT, fecha_cierre TEXT,
  ultima_nota TEXT, UNIQUE (despacho_id, cod));
CREATE TABLE IF NOT EXISTS vinculo (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, cod_origen TEXT NOT NULL,
  cod_destino TEXT NOT NULL, relacion TEXT, relacion_inversa TEXT,
  UNIQUE (despacho_id, cod_origen, cod_destino));
CREATE TABLE IF NOT EXISTS documento (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, cod TEXT NOT NULL,
  tipo TEXT, cod_cliente TEXT, num_poliza TEXT, num_siniestro TEXT, num_recibo TEXT,
  nombre_fichero TEXT, ruta TEXT, fecha TEXT, tamano_kb INTEGER, fecha_caducidad TEXT,
  UNIQUE (despacho_id, cod));
CREATE TABLE IF NOT EXISTS oferta_manual (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, num_poliza TEXT NOT NULL,
  compania_oferta TEXT NOT NULL, prima_total_anual REAL, fecha_oferta TEXT, notas_cobertura TEXT,
  UNIQUE (despacho_id, num_poliza, compania_oferta, fecha_oferta));
-- Registro de actividad: solo se añaden filas, nunca se modifican ni se borran.
CREATE TABLE IF NOT EXISTS registro_actividad (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, usuario_id INTEGER,
  fecha TEXT NOT NULL, accion TEXT NOT NULL, entidad TEXT, detalle TEXT);
CREATE TRIGGER IF NOT EXISTS registro_no_update BEFORE UPDATE ON registro_actividad
  BEGIN SELECT RAISE(ABORT, 'registro_actividad es de solo añadir'); END;
CREATE TRIGGER IF NOT EXISTS registro_no_delete BEFORE DELETE ON registro_actividad
  BEGIN SELECT RAISE(ABORT, 'registro_actividad es de solo añadir'); END;
-- Salud de la cartera: una incidencia por regla y elemento; se reabre o se cierra sola en cada revisión.
CREATE TABLE IF NOT EXISTS incidencia_salud (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, regla TEXT NOT NULL,
  severidad TEXT NOT NULL CHECK (severidad IN ('alta','media','baja')),
  entidad TEXT NOT NULL, ref TEXT NOT NULL, detalle TEXT,
  estado TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta','resuelta')),
  detectada TEXT NOT NULL, resuelta TEXT, responsable_id INTEGER,
  UNIQUE (despacho_id, regla, entidad, ref));
CREATE TABLE IF NOT EXISTS revision_salud (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, fecha TEXT NOT NULL,
  motivo TEXT, abiertas INTEGER, nuevas INTEGER, resueltas INTEGER);
-- Renovaciones: una por póliza y vencimiento.
CREATE TABLE IF NOT EXISTS renovacion (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, num_poliza TEXT NOT NULL, fecha_vencimiento TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('oferta','sin_mejora','aviso','bloqueada','fuera_plazo','sin_tarificar')),
  estado TEXT NOT NULL CHECK (estado IN ('pendiente','preparada','enviada','respondida','cerrada')),
  motivo TEXT, referencia REAL, opciones_json TEXT, ahorro_max REAL,
  creada TEXT NOT NULL, enviada_en TEXT, aprobada_por INTEGER,
  respuesta_accion TEXT, respuesta_detalle TEXT, respuesta_en TEXT,
  UNIQUE (despacho_id, num_poliza, fecha_vencimiento));
-- Bandeja de salida: todo lo que se envía queda aquí (en la prueba, en modo simulado).
CREATE TABLE IF NOT EXISTS envio (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, renovacion_id INTEGER NOT NULL,
  canal TEXT NOT NULL CHECK (canal IN ('email','whatsapp')), destinatario TEXT NOT NULL,
  asunto TEXT, cuerpo_html TEXT, cuerpo_texto TEXT,
  estado TEXT NOT NULL CHECK (estado IN ('enviado','error')), modo TEXT NOT NULL,
  enviado_en TEXT NOT NULL, aprobado_por INTEGER,
  UNIQUE (despacho_id, renovacion_id, canal));
-- Enlaces de respuesta de los botones del correo: únicos y con caducidad.
CREATE TABLE IF NOT EXISTS token_respuesta (
  token TEXT PRIMARY KEY, despacho_id INTEGER NOT NULL, renovacion_id INTEGER NOT NULL,
  accion TEXT NOT NULL, expira TEXT NOT NULL, usado_en TEXT);
-- Validación de textos: quién la dio, cuándo y para qué versión exacta del texto.
CREATE TABLE IF NOT EXISTS plantilla_validacion (
  despacho_id INTEGER NOT NULL, tipo TEXT NOT NULL, version TEXT NOT NULL,
  validada_por INTEGER NOT NULL, validada_en TEXT NOT NULL, PRIMARY KEY (despacho_id, tipo));
-- Comisión estándar pactada con cada compañía para cada ramo; cada póliza la hereda salvo que tenga una propia.
CREATE TABLE IF NOT EXISTS comision_estandar (
  despacho_id INTEGER NOT NULL, compania TEXT NOT NULL, ramo TEXT NOT NULL,
  pct REAL NOT NULL CHECK (pct >= 0 AND pct <= 100), actualizado TEXT NOT NULL, usuario_id INTEGER,
  PRIMARY KEY (despacho_id, compania, ramo));
-- Recibos devueltos que la compañía comunica y el empleado registra a mano.
CREATE TABLE IF NOT EXISTS devolucion_recibo (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, num_poliza TEXT NOT NULL, cod_recibo TEXT,
  fecha_devolucion TEXT NOT NULL, importe REAL NOT NULL CHECK (importe > 0), motivo TEXT NOT NULL,
  registrada_por INTEGER, registrada_en TEXT NOT NULL,
  UNIQUE (despacho_id, num_poliza, fecha_devolucion, importe));
-- Avisos que la aplicación manda al propio despacho (en la prueba, solo simulados).
CREATE TABLE IF NOT EXISTS aviso_interno (
  id INTEGER PRIMARY KEY, despacho_id INTEGER NOT NULL, tipo TEXT NOT NULL, ref TEXT,
  destinatario TEXT NOT NULL, asunto TEXT NOT NULL, cuerpo TEXT NOT NULL,
  modo TEXT NOT NULL, enviado_en TEXT NOT NULL);
