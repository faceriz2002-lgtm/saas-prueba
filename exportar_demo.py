"""Genera una demo navegable (un solo HTML) con las pantallas REALES de la aplicación,
renderizadas con el export de ejemplo. No es un servidor en vivo: es una foto navegable.
En la demo, «Aprobar y enviar» solo simula el envío y «Descargar» entrega los PDF ficticios."""
import base64, json, re
from datetime import date
from corredur.db import conectar, crear_despacho, crear_usuario
from corredur.importador import importar
from corredur import salud, renovaciones as R, comunicaciones as C
from corredur.documentos import pdf_documento, TIPOS_DESCARGABLES
from corredur.web import crear_app

HOY = date(2026, 11, 14)
con = conectar()
did, admin = crear_despacho(con, "Despacho piloto (ejemplo)", "Administrador", "admin@despacho.test")
emp = crear_usuario(con, did, "Laura (empleada)", "laura@despacho.test", "empleado", admin)
importar(con, did, "../export_ejemplo_correduria.xlsx", admin)
salud.revisar(con, did, hoy=HOY, usuario_id=admin)
R.detectar(con, did, HOY, admin)
for tipo in C.TEXTOS:                      # el administrador ya ha validado los textos
    C.validar_plantilla(con, did, tipo, admin)
app = crear_app(con, did, hoy=HOY)

rutas_comunes = ["/renovaciones"] + [f"/renovacion/{r['id']}" for r in con.execute("SELECT id FROM renovacion WHERE estado<>'cerrada' ORDER BY id")] \
              + ["/clientes"] + [f"/cliente/{r['cod']}" for r in con.execute("SELECT cod FROM cliente ORDER BY cod")] \
              + [f"/poliza/{r['num_poliza']}" for r in con.execute("SELECT num_poliza FROM poliza ORDER BY num_poliza")]
rutas_admin = ["/salud"] + [f"/salud/{r}" for r in salud.REGLAS] + ["/salida"] + rutas_comunes
roles = {"admin": (admin, rutas_admin, "/salud"), "emp": (emp, rutas_comunes, "/renovaciones")}
ids = {admin: "admin", emp: "emp"}

secciones, estilo = [], None
for rol, (uid, rutas, inicio) in roles.items():
    c = app.test_client(); c.get(f"/entrar/{uid}")
    for ruta in rutas:
        html = c.get(ruta).get_data(as_text=True)
        estilo = estilo or re.search(r"<style>.*?</style>", html, re.S).group(0)
        cab = re.search(r"<header>.*?</header>", html, re.S).group(0)
        cuerpo = re.search(r"<main>.*?</main>", html, re.S).group(0)
        def reescribir(m, rol=rol, inicio=inicio):
            destino = m.group(1)
            e = re.fullmatch(r"/entrar/(\d+)", destino)
            if e:
                nuevo = ids[int(e.group(1))]
                return f'href="#{nuevo}:{roles[nuevo][2]}"'
            d = re.fullmatch(r"/documento/([^/]+)/descargar", destino)
            if d:
                return f'href="#" data-descargar="{d.group(1)}"'
            if destino == "/":
                destino = inicio
            return f'href="#{rol}:{destino}"'
        cab = re.sub(r'href="(/[^"]*)"', reescribir, cab)
        cuerpo = re.sub(r'href="(/[^"]*)"', reescribir, cuerpo)
        cuerpo = re.sub(r'<form method="get">(<input[^>]*>)</form>', r"\1", cuerpo)
        secciones.append(f'<section data-ruta="{rol}:{ruta}" hidden>{cab}{cuerpo}</section>')

docs = {}
for r in con.execute("SELECT cod FROM documento WHERE tipo IN (%s)" % ",".join("?" * len(TIPOS_DESCARGABLES)), TIPOS_DESCARGABLES):
    nombre, datos = pdf_documento(con, did, r["cod"])
    docs[r["cod"]] = {"n": nombre, "b": base64.b64encode(datos).decode()}

js = """
var actual='admin:/salud';
function ir(r){var ok=false;document.querySelectorAll('section').forEach(function(x){var v=x.getAttribute('data-ruta')===r;x.hidden=!v;if(v)ok=true});
 if(ok){actual=r;window.scrollTo(0,0)}}
function aviso(t){var d=document.createElement('div');d.textContent=t;d.style.cssText='position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#1f2430;color:#fff;padding:10px 16px;border-radius:10px;z-index:99;font:14px system-ui';document.body.appendChild(d);setTimeout(function(){d.remove()},3500)}
document.addEventListener('click',function(e){
 var dl=e.target.closest&&e.target.closest('a[data-descargar]');
 if(dl){e.preventDefault();descargar(dl.getAttribute('data-descargar'));return}
 var a=e.target.closest&&e.target.closest('a[href^="#"]');if(!a)return;e.preventDefault();var h=a.getAttribute('href').slice(1);if(h)ir(decodeURIComponent(h))});
async function descargar(cod){var d=DOCS[cod];if(!d)return;
 try{var dw=window.claude&&await window.claude.use('downloads');if(!dw){aviso('La descarga no está disponible en esta vista');return}
  var bin=atob(d.b),u=new Uint8Array(bin.length);for(var i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
  await dw.save({filename:d.n,data:new Blob([u],{type:'application/pdf'})})}catch(err){if(!err||err.code!=='declined')aviso('No se pudo descargar el documento')}}
document.addEventListener('submit',function(e){e.preventDefault();var f=e.target;var id=f.getAttribute('data-aprobar');if(!id)return;
 document.querySelectorAll('[data-reno-estado="'+id+'"]').forEach(function(x){x.textContent='Enviada';x.className='etq ok'});
 document.querySelectorAll('[data-oculto-tras-enviar="'+id+'"]').forEach(function(x){x.hidden=true});
 document.querySelectorAll('[data-msg-enviado="'+id+'"]').forEach(function(x){x.hidden=false});
 var t=document.querySelector('section[data-ruta="admin:/salida"] table');
 if(t){var v=t.querySelector('td.vacio');if(v)v.closest('tr').remove();var tr=document.createElement('tr');
  tr.innerHTML='<td>'+f.getAttribute('data-poliza')+'</td><td>'+f.getAttribute('data-canales')+'</td><td>cliente</td><td>ahora (simulado)</td>';t.appendChild(tr)}
 aviso('Enviado en modo simulado: no ha salido nada real')});
document.addEventListener('input',function(e){if(e.target.type!=='search')return;var q=e.target.value.toLowerCase();
 e.target.closest('section').querySelectorAll('table tr').forEach(function(r,i){if(i===0)return;r.hidden=q&&r.textContent.toLowerCase().indexOf(q)<0})});
ir(actual);
"""
doc = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Renovaciones · demo</title>{estilo}'
       f'<style>section[hidden],tr[hidden],[hidden]{{display:none!important}}</style></head><body>{"".join(secciones)}'
       f'<script>var DOCS={json.dumps(docs)};{js}</script></body></html>')
open("demo.html", "w", encoding="utf-8").write(doc)

existentes = set(re.findall(r'data-ruta="([^"]+)"', doc))
rotos = {h for h in re.findall(r'href="#([^"]+)"', doc) if h and h not in existentes}
print(f"{len(existentes)} pantallas, {len(docs)} documentos, {len(doc)/1024:.0f} KB, enlaces rotos: {len(rotos)}")
for r in sorted(rotos)[:10]:
    print("  roto:", r)
