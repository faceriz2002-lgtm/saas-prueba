"""Arranca la aplicación en tu ordenador con el Excel de ejemplo (datos 100 % ficticios).
Uso:  python arrancar.py        y abre  http://localhost:5000
Lo que hagas (comisiones, devoluciones…) se guarda en el archivo datos_prueba.db.
Para empezar de cero, cierra la aplicación y borra ese archivo.
La fecha «de hoy» está fijada al 14/11/2026 porque el Excel de ejemplo está construido para ese día."""
import os, sys, webbrowser
from datetime import date
from corredur.db import conectar, crear_despacho, crear_usuario
from corredur.importador import importar
from corredur import salud, renovaciones as R, comunicaciones as C
from corredur.web import crear_app

HOY = date(2026, 11, 14)
EXCEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_ejemplo_correduria.xlsx")

def preparar(ruta_db="datos_prueba.db"):
    nuevo = not os.path.exists(ruta_db) if ruta_db != ":memory:" else True
    con = conectar(ruta_db)
    if nuevo:
        did, admin = crear_despacho(con, "Despacho piloto (ejemplo)", "Administrador", "admin@despacho.test")
        crear_usuario(con, did, "Laura (empleada)", "laura@despacho.test", "empleado", admin)
        importar(con, did, EXCEL, admin)
        salud.revisar(con, did, hoy=HOY, usuario_id=admin)
        R.detectar(con, did, HOY, admin)
        for tipo in C.TEXTOS:     # en la prueba el administrador ya ha validado los textos de los avisos
            C.validar_plantilla(con, did, tipo, admin)
    else:
        did = con.execute("SELECT id FROM despacho ORDER BY id LIMIT 1").fetchone()["id"]
    return crear_app(con, did, hoy=HOY)

if __name__ == "__main__":
    app = preparar()
    print("\nAplicación lista en  http://localhost:5000   (para salir: Ctrl+C)\n")
    try:
        webbrowser.open("http://localhost:5000")
    except Exception:
        pass
    app.run(host="127.0.0.1", port=5000, threaded=False)   # solo accesible desde tu ordenador
