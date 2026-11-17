import sys
from datetime import date
from corredur.db import conectar, crear_despacho
from corredur.importador import importar
from corredur import salud

ruta = sys.argv[1] if len(sys.argv) > 1 else "../export_ejemplo_correduria.xlsx"
con = conectar()
did, uid = crear_despacho(con, "Despacho piloto (ejemplo)")
r = importar(con, did, ruta, uid)
print("IMPORTACIÓN:", {k: v for k, v in r["hojas"].items()}, "rechazadas:", r["rechazadas"])
print("REVISIÓN:", salud.revisar(con, did, hoy=date(2026, 11, 14), usuario_id=uid))
for regla, sev, n, desc in salud.resumen(con, did):
    print(f"  [{sev:5}] {n:3}  {regla:28} {desc}")
