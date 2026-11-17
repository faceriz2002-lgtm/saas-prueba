import random, datetime as dt
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
random.seed(2611)
HOY = dt.date(2026,11,14)
F = lambda d: d  # keep dates as dates

# ---------- helpers
def nif(n):
    return f"{n:08d}" + "TRWAGMYFPDXBNJZSQVHLCKE"[n%23]
def cif(n): return "B" + f"{n:07d}" + str(n%10)
def tel(): return f"6{random.randint(0,9)}{random.randint(0,9)} {random.randint(100,999)} {random.randint(100,999)}"
def tel_fijo(): return f"976 {random.randint(100,999)} {random.randint(100,999)}"
def iban(): return "ES" + f"{random.randint(10,99)} " + " ".join(f"{random.randint(0,9999):04d}" for _ in range(5))

NOMBRES_H = ["Antonio","José","Manuel","Francisco","David","Javier","Daniel","Carlos","Miguel","Rafael","Pablo","Sergio","Alberto","Jorge","Luis","Andrés"]
NOMBRES_M = ["María","Carmen","Ana","Laura","Marta","Isabel","Elena","Lucía","Pilar","Cristina","Sara","Paula","Rosa","Teresa","Beatriz","Silvia"]
APE = ["García","Martínez","López","Sánchez","Pérez","Gómez","Ruiz","Hernández","Jiménez","Díaz","Moreno","Álvarez","Romero","Navarro","Torres","Domínguez","Gil","Vázquez","Serrano","Blasco","Ortega","Marín","Sanz","Lacasa","Used","Abadía"]
CALLES = ["Calle Alfonso I","Paseo de la Independencia","Avenida Goya","Calle San Miguel","Calle Predicadores","Avenida Cesáreo Alierta","Calle Delicias","Paseo Sagasta","Calle Coso","Calle Tomás Bretón","Avenida Navarra","Calle Boggiero","Camino de las Torres","Calle Zurita"]
POBL = [("Zaragoza","50",["50001","50002","50003","50004","50005","50006","50007","50008","50009","50010","50011","50012","50013","50014","50015","50017","50018"]),("Utebo","50",["50180"]),("Cuarte de Huerva","50",["50410"]),("Villanueva de Gállego","50",["50830"]),("Huesca","22",["22001","22002"]),("Calatayud","50",["50300"])]
CIAS = {"A":"Compañía A","B":"Compañía B","C":"Compañía C","D":"Compañía D","E":"Compañía E","F":"Compañía F","G":"Compañía G","H":"Compañía H","I":"Compañía I","J":"Compañía J","N":"Compañía N","P":"Compañía P","R":"Compañía R"}
CIA_RAMO = {"Auto":["A","H","N","B"],"Moto":["P","A"],"Hogar":["D","I","B"],"Salud":["G","F"],"Vida":["F","G"],"Comercio":["R","D"],"RC Profesional":["R","B"]}
COMI = {"Auto":.12,"Moto":.12,"Hogar":.14,"Salud":.06,"Vida":.08,"Comercio":.09,"RC Profesional":.10}
MARCAS = [("Seat","León"),("Seat","Ibiza"),("Renault","Clio"),("Volkswagen","Golf"),("Toyota","Corolla"),("Peugeot","208"),("Ford","Focus"),("Citroën","C3"),("Dacia","Sandero"),("Hyundai","Tucson"),("Kia","Sportage"),("Opel","Corsa")]
TRAMIT = ["Laura","Iván","Carmen"]
MEDIADORES = {"Laura":"Laura (colaboradora)","Iván":"Iván (colaborador)"}
SEXO_H=set(NOMBRES_H)

# ---------- clientes
clientes=[]; cid=1000
def nuevo_cli(tipo, nombre, ap1="", ap2="", rs="", **kw):
    global cid; cid+=1
    c=dict(cod=f"C{cid:05d}", tipo=tipo, nombre=nombre, ap1=ap1, ap2=ap2, rs=rs); c.update(kw); clientes.append(c); return c
used=set()
for i in range(36):
    sexo = random.choice("HM")
    nom = random.choice(NOMBRES_H if sexo=="H" else NOMBRES_M)
    a1,a2=random.sample(APE,2)
    n=random.randint(10000000,79999999)
    fn=dt.date(random.randint(1948,2002),random.randint(1,12),random.randint(1,28))
    pob,prov,cps=random.choice(POBL)
    c=nuevo_cli("Persona física",nom,a1,a2,nif=nif(n),sexo=sexo,fnac=fn,
        dir=f"{random.choice(CALLES)}, {random.randint(1,120)}, {random.randint(1,6)}º {random.choice('ABCD')}",cp=random.choice(cps),pob=pob,prov=prov,
        tel=tel(),tel2=tel_fijo() if random.random()<.3 else "",mail=f"{nom.lower().replace('é','e').replace('í','i').replace('á','a').replace('ú','u')}.{a1.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')}{i}@ejemplo.test" if random.random()>.1 else "",
        wa=random.random()<.72,mailcom=random.random()<.88,
        alta=dt.date(random.randint(2009,2025),random.randint(1,12),random.randint(1,28)),
        ecivil=random.choice(["Soltero/a","Casado/a","Casado/a","Divorciado/a","Viudo/a"]),prof=random.choice(["Funcionario/a","Autónomo/a","Jubilado/a","Empleado/a","Docente","Sanitario/a","Ingeniero/a","Comercial"]))
EMPRESAS=["Talleres Lacasa S.L.","Panadería Obrador Marín S.L.","Clínica Dental Sanz S.L.P.","Construcciones Used S.L.","Distribuciones Blasco S.A.","Asesoría Abadía y Asociados S.L.","Restaurante La Plaza S.L.","Transportes Ortega S.L."]
for j,rs in enumerate(EMPRESAS):
    pob,prov,cps=random.choice(POBL[:4])
    nuevo_cli("Persona jurídica","","","",rs=rs,nif=cif(random.randint(1000000,9999999)),sexo="",fnac=None,
        dir=f"Polígono {random.choice(['Malpica','Plaza','Cogullada','Centrovía'])}, nave {random.randint(1,40)}",cp=random.choice(cps),pob=pob,prov=prov,
        tel=tel_fijo(),tel2=tel(),mail=f"admin{j}@empresa-ejemplo.test",wa=random.random()<.5,mailcom=True,
        alta=dt.date(random.randint(2010,2024),random.randint(1,12),random.randint(1,28)),ecivil="",prof="")
# casos de borde
clientes[5]["mail"]=""; clientes[5]["wa"]=False   # sin email ni whatsapp
clientes[9]["tel"]=""                                # sin móvil
clientes[12]["mailcom"]=False                        # no acepta comunicaciones comerciales
for c in clientes:
    c["mediador"]=random.choice(["Laura","Iván"])
    c["banco"]=random.choice(["Caja Rural","Ibercaja","CaixaBank","BBVA","Santander","Sabadell"])
    c["iban"]=iban()
    c["nombre_c"]=c["rs"] if c["tipo"]=="Persona jurídica" else f'{c["nombre"]} {c["ap1"]} {c["ap2"]}'

# ---------- pólizas
polizas=[];riesgos=[];garantias=[];recibos=[];siniestros=[];docs=[]
pid=0;rid=0;recid=0;sid=0;did=0
def add_doc(tipo,cod_cli,num_pol="",num_sin="",num_rec="",nombre=None):
    global did; did+=1
    docs.append(dict(id=f"D{did:06d}",tipo=tipo,cli=cod_cli,pol=num_pol,sin=num_sin,rec=num_rec,
        fichero=nombre or f"{tipo.lower().replace(' ','_')}_{cod_cli}_{num_pol or num_sin or num_rec}.pdf",
        ruta=f"/documentos/{cod_cli}/",fecha=HOY-dt.timedelta(days=random.randint(5,900)),tam=random.randint(60,2400)))
def venc_aleatorio(zona):
    if zona=="proximo": d=random.randint(1,63)
    elif zona=="pasado": d=-random.randint(1,25)
    else: d=random.randint(64,360)
    return HOY+dt.timedelta(days=d)
def add_pol(c, ramo, producto, zona, prima, forma, estado="En vigor", cia=None, extra=None):
    global pid
    pid+=1
    cia=cia or random.choice(CIA_RAMO[ramo]); v=venc_aleatorio(zona)
    try: efecto=v.replace(year=v.year-1)
    except ValueError: efecto=v-dt.timedelta(days=365)
    num=f"{ {'Auto':'AU','Moto':'MO','Hogar':'HG','Salud':'SA','Vida':'VI','Comercio':'MR','RC Profesional':'RC'}[ramo] }-{efecto.year}-{pid:04d}"
    neta=round(prima/1.0615,2); imp=round(prima-neta,2)
    pol=dict(cod=f"P{pid:05d}",num=num,cli=c["cod"],ramo=ramo,prod=producto,cia=CIAS[cia],efecto=efecto,vence=v,
        alta=efecto-dt.timedelta(days=random.randint(0,40)) if random.random()<.8 else efecto,estado=estado,forma=forma,
        neta=neta,imp=imp,total=round(prima,2),com=round(neta*COMI[ramo],2),pct=COMI[ramo]*100,mediador=c["mediador"],
        renov="Sí" if estado=="En vigor" else "No",
        origen=random.choice(["Cartera propia","Cartera propia","Traspaso","Nueva producción"]),
        anulacion=None,motivo="",obs="")
    if estado=="Anulada": pol["anulacion"]=HOY-dt.timedelta(days=random.randint(20,200)); pol["motivo"]=random.choice(["A petición del cliente","Impago","Cambio de compañía"]); pol["renov"]="No"
    if estado=="Suspendida": pol["obs"]="Suspendida por impago de recibo"
    pol["prima_ren"]=round(pol["total"]*random.choice([random.uniform(.97,1.0),random.uniform(1.0,1.08),random.uniform(1.08,1.22)]),2) if (v-HOY).days<=90 and estado=="En vigor" else None
    pol["fecha_aviso"]=v-dt.timedelta(days=random.randint(45,75)) if pol["prima_ren"] else None
    if extra: pol.update(extra)
    polizas.append(pol)
    add_doc("Póliza",c["cod"],num)
    # recibos
    nrec={"Anual":1,"Semestral":2,"Trimestral":4,"Mensual":12}[forma]
    importe=round(prima/nrec,2)
    step=365//nrec
    for k in range(nrec):
        global recid; recid+=1
        ini=efecto+dt.timedelta(days=k*step); fin=min(ini+dt.timedelta(days=step-1),v-dt.timedelta(days=1))
        if ini>HOY+dt.timedelta(days=30): est="Pendiente de emitir"
        elif ini>HOY: est="Pendiente"
        else: est="Cobrado"
        recibos.append(dict(cod=f"R{recid:06d}",num=f"{num}/{k+1:02d}",pol=num,cli=c["cod"],ini=ini,fin=fin,
            emision=ini-dt.timedelta(days=random.randint(10,25)),
            neta=round(importe/1.0615,2),imp=round(importe-importe/1.0615,2),total=importe,
            com=round(importe/1.0615*COMI[ramo],2),est=est,
            cobro=ini+dt.timedelta(days=random.randint(0,6)) if est=="Cobrado" else None,
            forma="Domiciliado",gestor="Compañía" if random.random()<.8 else "Correduría",liq=("Liquidado" if est=="Cobrado" else "Pendiente de liquidar")))
    return pol
def add_riesgo(pol,tipo,**kw):
    global rid; rid+=1
    r=dict(cod=f"RI{rid:05d}",pol=pol["num"],tipo=tipo); r.update(kw); riesgos.append(r)
def add_gar(pol,nombre,capital,franq="",incl="Sí"):
    garantias.append(dict(pol=pol["num"],gar=nombre,capital=capital,franq=franq,incl=incl))

def crea_auto(c,zona,cia=None,**kw):
    marca,mod=random.choice(MARCAS); anio=random.randint(2008,2025)
    tipo=random.choices(["Todo riesgo con franquicia","Terceros ampliado","Terceros básico","Todo riesgo sin franquicia"],[4,3,2,1])[0]
    base={"Todo riesgo con franquicia":random.randint(420,680),"Terceros ampliado":random.randint(260,380),"Terceros básico":random.randint(180,290),"Todo riesgo sin franquicia":random.randint(640,900)}[tipo]
    p=add_pol(c,"Auto",tipo,zona,base,random.choice(["Anual","Anual","Semestral"]),cia=cia,**kw)
    mat=f"{random.randint(1000,9999)} {''.join(random.choices('BCDFGHJKLMNPRSTVWXYZ',k=3))}"
    add_riesgo(p,"Vehículo",matricula=mat,marca=marca,modelo=mod,anio=anio,
        fmat=dt.date(anio,random.randint(1,12),random.randint(1,28)),uso="Particular",combustible=random.choice(["Gasolina","Diésel","Híbrido","Eléctrico"]),
        valor=random.randint(4000,32000),conductor=c["nombre_c"],fcarnet=dt.date(random.randint(1985,2018),random.randint(1,12),random.randint(1,28)),
        bonus=random.choice(["-60%","-50%","-40%","-30%","-20%","0%"]),garaje=random.choice(["Sí","No"]),km=random.choice([8000,12000,15000,20000]))
    add_gar(p,"Responsabilidad civil obligatoria","Límites legales")
    add_gar(p,"Responsabilidad civil voluntaria","50.000.000 €")
    add_gar(p,"Defensa jurídica y reclamación de daños","600 €")
    add_gar(p,"Asistencia en viaje","Desde km 0")
    add_gar(p,"Lunas","Incluida","", "Sí" if tipo!="Terceros básico" else "No")
    add_gar(p,"Robo e incendio","Valor venal","", "Sí" if "Terceros básico" not in tipo else "No")
    if tipo.startswith("Todo riesgo"):
        add_gar(p,"Daños propios","Valor venal","300 €" if "con" in tipo else "Sin franquicia")
        add_gar(p,"Vehículo de sustitución","15 días")
    return p
def crea_hogar(c,zona,cia=None,**kw):
    pob=c["pob"]; m2=random.randint(55,190); cont=random.choice([60000,90000,120000,180000]); contenido=random.choice([15000,20000,30000,45000])
    p=add_pol(c,"Hogar","Hogar vivienda habitual",zona,random.randint(150,320),random.choice(["Anual","Semestral"]),cia=cia,**kw)
    add_riesgo(p,"Inmueble",direccion=f"{c['dir']}, {c['cp']} {pob}",m2=m2,anio_cons=random.randint(1955,2022),regimen=random.choice(["Propiedad","Alquiler"]),
        continente=cont,contenido=contenido,joyas=random.choice([0,3000,6000]),alarma=random.choice(["Sí","No"]),tipo_viv=random.choice(["Piso","Casa adosada","Chalet"]))
    add_gar(p,"Incendio, explosión y rayo",f"{cont:,} €".replace(",","."),"")
    add_gar(p,"Daños por agua",f"{cont:,} €".replace(",","."),"150 €")
    add_gar(p,"Robo y expoliación",f"{contenido:,} €".replace(",","."),"")
    add_gar(p,"Responsabilidad civil familiar","300.000 €")
    add_gar(p,"Defensa jurídica","3.000 €")
    add_gar(p,"Asistencia al hogar 24h","Incluida")
    return p
def crea_salud(c,zona,**kw):
    n=random.choice([1,1,2,3,4])
    p=add_pol(c,"Salud","Salud cuadro médico"+(" con copago" if random.random()<.4 else ""),zona,random.randint(480,1700)*n//1,random.choice(["Mensual","Mensual","Trimestral","Anual"]),**kw)
    add_riesgo(p,"Asegurados",num_asegurados=n,modalidad=random.choice(["Cuadro médico","Cuadro médico + dental","Reembolso"]),carencias=random.choice(["Sin carencias","Con carencias"]),preexistencias="No declaradas")
    add_gar(p,"Asistencia ambulatoria y especialidades","Cuadro médico")
    add_gar(p,"Hospitalización y cirugía","Cuadro médico")
    add_gar(p,"Urgencias","Incluida")
    return p
def crea_vida(c,zona,**kw):
    cap=random.choice([60000,100000,150000,250000])
    p=add_pol(c,"Vida","Vida riesgo temporal anual renovable",zona,random.randint(90,420),"Anual",**kw)
    add_riesgo(p,"Asegurado",capital_fallecimiento=cap,capital_invalidez=cap,beneficiarios=random.choice(["Cónyuge","Hijos por partes iguales","Herederos legales"]),fnac_asegurado=c["fnac"],fumador=random.choice(["No","Sí"]),vinculada_hipoteca=random.choice(["Sí","No"]))
    add_gar(p,"Fallecimiento",f"{cap:,} €".replace(",","."))
    add_gar(p,"Invalidez absoluta y permanente",f"{cap:,} €".replace(",","."))
    return p

# reparto de pólizas por cliente
zonas=lambda: random.choices(["proximo","futuro","pasado"],[5,6,1])[0]
for idx,c in enumerate(clientes):
    if c["tipo"]=="Persona jurídica":
        p=add_pol(c,"Comercio","Multirriesgo comercio/taller",zonas(),random.randint(520,1900),random.choice(["Anual","Trimestral"]))
        add_riesgo(p,"Local",direccion=f"{c['dir']}, {c['cp']} {c['pob']}",actividad=random.choice(["Taller mecánico","Obrador","Clínica","Oficina","Restauración"]),m2=random.randint(80,600),continente=random.choice([200000,350000,600000]),contenido=random.choice([60000,120000,200000]),existencias=random.choice([20000,40000,0]))
        add_gar(p,"Incendio y complementarias","Continente y contenido")
        add_gar(p,"Responsabilidad civil explotación","600.000 €")
        add_gar(p,"Pérdida de beneficios","90.000 €")
        if random.random()<.5: crea_auto(c,zonas())
        if random.random()<.4:
            p=add_pol(c,"RC Profesional","RC profesional",zonas(),random.randint(280,900),"Anual")
            add_riesgo(p,"Actividad",actividad="Servicios profesionales",facturacion=random.choice([150000,300000,600000]),limite=random.choice([300000,600000,1000000]))
            add_gar(p,"RC profesional","600.000 €","1.000 €")
        continue
    ramos=random.choices([["auto"],["auto","hogar"],["hogar"],["auto","hogar","vida"],["auto","salud"],["hogar","vida","salud"],["auto","hogar","salud","vida"]],[3,5,2,3,2,2,1])[0]
    for r in ramos:
        z=zonas()
        if r=="auto": crea_auto(c,z)
        if r=="hogar": crea_hogar(c,z)
        if r=="salud": crea_salud(c,z)
        if r=="vida": crea_vida(c,z)
    if random.random()<.12:
        p=add_pol(c,"Moto","Moto terceros ampliado",zonas(),random.randint(130,280),"Anual")
        add_riesgo(p,"Vehículo",matricula=f"{random.randint(1000,9999)} {''.join(random.choices('BCDFGHJKLMNPRSTVWXYZ',k=3))}",marca="Yamaha",modelo="MT-07",anio=random.randint(2012,2024),uso="Particular",cilindrada=689)
        add_gar(p,"Responsabilidad civil obligatoria","Límites legales")
# casos de borde explícitos
polizas[2]["estado"]="Anulada"; polizas[2]["anulacion"]=HOY-dt.timedelta(days=60); polizas[2]["motivo"]="Cambio de compañía"; polizas[2]["renov"]="No"
polizas[7]["estado"]="Suspendida"; polizas[7]["obs"]="Suspendida por impago de recibo"; polizas[7]["renov"]="No"
polizas[11]["estado"]="Pendiente de emisión"; polizas[11]["renov"]="No"; polizas[11]["origen"]="Nueva producción"
# impagos / devueltos
cobrados=[r for r in recibos if r["est"]=="Cobrado"]
for r in random.sample(cobrados,6): r["est"]="Devuelto"; r["cobro"]=None; r["liq"]="Pendiente de liquidar"
for r in random.sample([r for r in recibos if r["est"]=="Cobrado"],4): r["est"]="Impagado"; r["cobro"]=None; r["liq"]="Pendiente de liquidar"
pol_by_num={p["num"]:p for p in polizas}
for r in recibos:
    if r["est"] in("Devuelto","Impagado") and pol_by_num[r["pol"]]["estado"]=="En vigor":
        pass
# ---------- siniestros
cand=[p for p in polizas if p["ramo"] in("Auto","Hogar","Comercio","Moto") and p["estado"]=="En vigor"]
TIPOS={"Auto":["Colisión con otro vehículo","Daños por lunas","Daños propios (golpe aparcado)","Robo de accesorios","Atropello de animal"],"Hogar":["Daños por agua","Robo","Rotura de cristales","Daños eléctricos","Incendio doméstico"],"Comercio":["Daños por agua","Robo en local","Rotura de cristales"],"Moto":["Caída","Robo"]}
for p in random.sample(cand,min(16,len(cand))):
    sid+=1; fo=HOY-dt.timedelta(days=random.randint(5,700)); est="Abierto" if random.random()<.3 else random.choice(["Cerrado","Cerrado con pago","Cerrado sin pago"])
    if est=="Abierto": fo=HOY-dt.timedelta(days=random.randint(3,60))
    num_s=f"SN-{fo.year}-{sid:05d}"
    siniestros.append(dict(cod=f"S{sid:05d}",num=num_s,ncia=f"{random.randint(10**8,10**9-1)}",pol=p["num"],cli=p["cli"],ramo=p["ramo"],
        ocurr=fo,apertura=fo+dt.timedelta(days=random.randint(0,4)),tipo=random.choice(TIPOS[p["ramo"]]),
        est=est,reserva=random.choice([300,640,1200,2500,4800]) if est=="Abierto" else 0,
        pagado=0 if est in("Abierto","Cerrado sin pago") else random.choice([180,410,640,980,2100]),
        culpa=random.choice(["Propia","Contraria","Compartida","No aplica"]) if p["ramo"] in("Auto","Moto") else "No aplica",
        tramit=random.choice(TRAMIT),cierre=None if est=="Abierto" else fo+dt.timedelta(days=random.randint(10,120)),
        notas=random.choice(["Peritación realizada","Pendiente de documentación del cliente","En espera de peritaje","Reparación autorizada","Pago emitido por la compañía"])))
    add_doc("Parte de siniestro",p["cli"],p["num"],num_s)
# ---------- vínculos
vinc=[]
pf=[c for c in clientes if c["tipo"]=="Persona física"]
def v(a,b,rel,inv=None): vinc.append(dict(a=a["cod"],na=a["nombre_c"],b=b["cod"],nb=b["nombre_c"],rel=rel,inv=inv or ""))
for i in range(0,10,2):
    v(pf[i],pf[i+1],"Cónyuge","Cónyuge")
    pf[i+1]["dir"]=pf[i]["dir"]; pf[i+1]["cp"]=pf[i]["cp"]; pf[i+1]["pob"]=pf[i]["pob"]
v(pf[10],pf[11],"Padre/Madre de","Hijo/a de"); v(pf[10],pf[12],"Padre/Madre de","Hijo/a de"); v(pf[14],pf[15],"Hermano/a de","Hermano/a de")
emp=[c for c in clientes if c["tipo"]=="Persona jurídica"]
for j,e in enumerate(emp[:6]): v(pf[20+j],e,"Administrador/a de","Administrador/a único/a" )
v(pf[26],emp[0],"Socio/a de","Socio/a de"); v(pf[27],emp[1],"Socio/a de","Socio/a de")
# docs de clientes
for c in clientes:
    add_doc("DNI/NIF" if c["tipo"]=="Persona física" else "CIF/Escrituras",c["cod"],nombre=f"identificacion_{c['cod']}.pdf")
for r in random.sample(recibos,25): add_doc("Recibo",r["cli"],r["pol"],"",r["num"])

# ---------- escribir
wb=Workbook(); wb.remove(wb.active)
HFILL=PatternFill("solid",fgColor="1F3864"); HFONT=Font(name="Arial",bold=True,color="FFFFFF",size=10); BF=Font(name="Arial",size=10)
def hoja(nombre,cols,filas,fmt=None,anchos=None):
    ws=wb.create_sheet(nombre); ws.append([c[0] for c in cols])
    for row in filas: ws.append([row.get(c[1],"") if isinstance(row,dict) else row for c in cols])
    for i,c in enumerate(cols,1):
        cell=ws.cell(1,i); cell.fill=HFILL; cell.font=HFONT; cell.alignment=Alignment(vertical="center",wrap_text=True)
        L=get_column_letter(i); ws.column_dimensions[L].width=max(12,min(46,max(len(str(c[0])),*(len(str(ws.cell(r,i).value or "")) for r in range(2,min(ws.max_row,60)+1)))+2))
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font=BF
            if isinstance(cell.value,(dt.date,dt.datetime)): cell.number_format="DD/MM/YYYY"
            elif isinstance(cell.value,float): cell.number_format="#,##0.00"
    ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions; ws.row_dimensions[1].height=30
    return ws

# Léeme
ws=wb.create_sheet("LEEME")
txt=["EXPORT DE EJEMPLO — DATOS 100% FICTICIOS","",
"Generado para desarrollar y probar la app de renovaciones. NIF, IBAN, teléfonos y correos son inventados (dominio .test).",
f"Fecha de la 'exportación': {HOY.strftime('%d/%m/%Y')}.","",
"Hojas: CLIENTES · POLIZAS · RIESGOS · GARANTIAS · RECIBOS · SINIESTROS · VINCULOS · DOCUMENTOS · OFERTAS_MANUAL (plantilla del piloto, no es parte del export).",
"Las hojas se relacionan por: COD_CLIENTE, NUM_POLIZA, NUM_RECIBO, NUM_SINIESTRO.","",
"CASOS DE BORDE INCLUIDOS A PROPÓSITO:",
" - Clientes sin correo o sin móvil, y con/sin consentimiento de WhatsApp y comunicaciones comerciales.",
" - Pólizas anuladas, suspendidas por impago y pendientes de emisión (no deben renovarse).",
" - Recibos devueltos e impagados (no ofrecer cambio a quien tiene impagos).",
" - PRIMA_RENOVACION_COMPAÑIA: precio que la compañía comunica para el siguiente periodo (solo pólizas que vencen en ~90 días). La app calcula la variación frente a PRIMA_TOTAL_ANUAL.",
" - Vencimientos ya pasados, dentro de 60 días y lejanos.",
" - Clientes con varias pólizas con vencimientos cercanos (agrupar avisos).",
" - Personas jurídicas (CIF), cónyuges con misma dirección, administradores y socios de empresas.",
" - Siniestros abiertos y cerrados, con/sin pago.",
"","AVISO: las columnas y nombres reales de QS pueden diferir. Cuando tengamos un export real anonimizado, se ajusta el mapeo."]
for t in txt: ws.append([t])
ws.column_dimensions["A"].width=120; ws["A1"].font=Font(name="Arial",bold=True,size=13)
for r in range(2,ws.max_row+1): ws.cell(r,1).font=BF
hoja("CLIENTES",[("COD_CLIENTE","cod"),("TIPO","tipo"),("NIF_CIF","nif"),("NOMBRE","nombre"),("APELLIDO_1","ap1"),("APELLIDO_2","ap2"),("RAZON_SOCIAL","rs"),("SEXO","sexo"),("FECHA_NACIMIENTO","fnac"),("ESTADO_CIVIL","ecivil"),("PROFESION","prof"),
 ("DIRECCION","dir"),("COD_POSTAL","cp"),("POBLACION","pob"),("PROVINCIA","prov"),("TELEFONO_MOVIL","tel"),("TELEFONO_2","tel2"),("EMAIL","mail"),("ACEPTA_WHATSAPP","wa"),("ACEPTA_COMUNICACIONES_COMERCIALES","mailcom"),
 ("FECHA_ALTA","alta"),("MEDIADOR_ASIGNADO","mediador"),("BANCO","banco"),("IBAN","iban")],
 [dict(c,wa="Sí" if c["wa"] else "No",mailcom="Sí" if c["mailcom"] else "No") for c in clientes])
hoja("POLIZAS",[("COD_POLIZA","cod"),("NUM_POLIZA","num"),("COD_CLIENTE","cli"),("RAMO","ramo"),("PRODUCTO","prod"),("COMPAÑIA","cia"),("FECHA_EFECTO","efecto"),("FECHA_VENCIMIENTO","vence"),("FECHA_ALTA","alta"),("ESTADO","estado"),("FORMA_PAGO","forma"),
 ("PRIMA_NETA","neta"),("IMPUESTOS_Y_RECARGOS","imp"),("PRIMA_TOTAL_ANUAL","total"),("PRIMA_RENOVACION_COMPAÑIA","prima_ren"),("FECHA_AVISO_COMPAÑIA","fecha_aviso"),("COMISION_PCT","pct"),("COMISION_ANUAL","com"),("MEDIADOR","mediador"),("RENOVABLE","renov"),("ORIGEN","origen"),("FECHA_ANULACION","anulacion"),("MOTIVO_ANULACION","motivo"),("OBSERVACIONES","obs")],polizas)
hoja("RIESGOS",[("COD_RIESGO","cod"),("NUM_POLIZA","pol"),("TIPO_RIESGO","tipo"),("MATRICULA","matricula"),("MARCA","marca"),("MODELO","modelo"),("AÑO","anio"),("FECHA_MATRICULACION","fmat"),("USO","uso"),("COMBUSTIBLE","combustible"),("VALOR_VEHICULO","valor"),("CONDUCTOR_HABITUAL","conductor"),("FECHA_CARNET","fcarnet"),("BONUS","bonus"),("GARAJE","garaje"),("KM_ANUALES","km"),("CILINDRADA","cilindrada"),
 ("DIRECCION_RIESGO","direccion"),("TIPO_VIVIENDA","tipo_viv"),("REGIMEN","regimen"),("M2","m2"),("AÑO_CONSTRUCCION","anio_cons"),("CAPITAL_CONTINENTE","continente"),("CAPITAL_CONTENIDO","contenido"),("JOYAS","joyas"),("EXISTENCIAS","existencias"),("ALARMA","alarma"),("ACTIVIDAD","actividad"),
 ("Nº_ASEGURADOS","num_asegurados"),("MODALIDAD","modalidad"),("CARENCIAS","carencias"),("PREEXISTENCIAS","preexistencias"),
 ("CAPITAL_FALLECIMIENTO","capital_fallecimiento"),("CAPITAL_INVALIDEZ","capital_invalidez"),("BENEFICIARIOS","beneficiarios"),("FECHA_NAC_ASEGURADO","fnac_asegurado"),("FUMADOR","fumador"),("VINCULADA_HIPOTECA","vinculada_hipoteca"),("FACTURACION","facturacion"),("LIMITE_INDEMNIZACION","limite")],riesgos)
hoja("GARANTIAS",[("NUM_POLIZA","pol"),("GARANTIA","gar"),("CAPITAL_LIMITE","capital"),("FRANQUICIA","franq"),("INCLUIDA","incl")],garantias)
hoja("RECIBOS",[("COD_RECIBO","cod"),("NUM_RECIBO","num"),("NUM_POLIZA","pol"),("COD_CLIENTE","cli"),("FECHA_EMISION","emision"),("INICIO_COBERTURA","ini"),("FIN_COBERTURA","fin"),("PRIMA_NETA","neta"),("IMPUESTOS_Y_RECARGOS","imp"),("PRIMA_TOTAL","total"),("COMISION","com"),("ESTADO_COBRO","est"),("FECHA_COBRO","cobro"),("FORMA_COBRO","forma"),("GESTOR_COBRO","gestor"),("LIQUIDACION","liq")],recibos)
hoja("SINIESTROS",[("COD_SINIESTRO","cod"),("NUM_EXPEDIENTE_PROPIO","num"),("NUM_EXPEDIENTE_COMPAÑIA","ncia"),("NUM_POLIZA","pol"),("COD_CLIENTE","cli"),("RAMO","ramo"),("FECHA_OCURRENCIA","ocurr"),("FECHA_APERTURA","apertura"),("TIPO","tipo"),("ESTADO","est"),("RESERVA","reserva"),("IMPORTE_PAGADO","pagado"),("CULPABILIDAD","culpa"),("TRAMITADOR","tramit"),("FECHA_CIERRE","cierre"),("ULTIMA_NOTA","notas")],siniestros)
hoja("VINCULOS",[("COD_CLIENTE_ORIGEN","a"),("NOMBRE_ORIGEN","na"),("COD_CLIENTE_DESTINO","b"),("NOMBRE_DESTINO","nb"),("RELACION","rel"),("RELACION_INVERSA","inv")],vinc)
hoja("DOCUMENTOS",[("COD_DOCUMENTO","id"),("TIPO_DOCUMENTO","tipo"),("COD_CLIENTE","cli"),("NUM_POLIZA","pol"),("NUM_SINIESTRO","sin"),("NUM_RECIBO","rec"),("NOMBRE_FICHERO","fichero"),("RUTA","ruta"),("FECHA","fecha"),("TAMAÑO_KB","tam")],docs)
# plantilla ofertas manuales (con ejemplos reales sobre pólizas próximas)
prox=[p for p in polizas if p["estado"]=="En vigor" and 0<(p["vence"]-HOY).days<=63 and p["ramo"] in("Auto","Hogar","Moto")][:12]
ofs=[]
for p in prox:
    for cia in random.sample([k for k in CIAS if k not in [kk for kk,vv in CIAS.items() if vv==p["cia"]]],2):
        ofs.append(dict(pol=p["num"],cia=CIAS[cia],prima=round(p["total"]*random.uniform(.84,1.04),2),fecha=HOY,nota=random.choice(["","Mismas coberturas","Sin vehículo de sustitución","Franquicia 250 €"])))
hoja("OFERTAS_MANUAL",[("NUM_POLIZA","pol"),("COMPAÑIA_OFERTA","cia"),("PRIMA_TOTAL_ANUAL","prima"),("FECHA_OFERTA","fecha"),("NOTAS_COBERTURA","nota")],ofs)
wb.save("/home/claude/export_ejemplo_correduria.xlsx")
print(len(clientes),len(polizas),len(riesgos),len(garantias),len(recibos),len(siniestros),len(vinc),len(docs),len(ofs))
print(sum(1 for p in polizas if 0<(p["vence"]-HOY).days<=63))
