# Prueba técnica: base, salud de la cartera, pantallas, renovaciones y avisos

Esto es una **prueba** con datos 100 % ficticios. No es todavía la aplicación final. Sirve para demostrar que lo difícil funciona antes de pedir datos reales.

## Qué hace
1. **Guarda todo en una base de datos**: despachos, usuarios (administrador o empleado), clientes, pólizas, riesgos, garantías, recibos, siniestros, vínculos, documentos y ofertas.
2. **Carga el Excel de exportación**. Si se vuelve a cargar, no duplica nada. Nunca borra: lo que no aparece en el último Excel se marca como «no aparece en el último export».
3. **No guarda el IBAN ni el banco** (minimización de datos).
4. **Salud de la cartera**: revisa 18 tipos de error y abre una incidencia por cada uno. Si se corrige el dato, la incidencia se cierra sola; si reaparece, se reabre.
5. **Registro de actividad**: cada carga y cada revisión queda anotada. La base de datos impide modificar o borrar ese registro.
6. **Separación por despacho**: cada correduría solo ve sus datos.

## Pantallas (nuevas)
- **Salud de la cartera** (solo administrador): errores abiertos, graves y a revisar, tabla por tipo de error y lista de casos que enlaza a cada ficha.
- **Clientes**: lista con buscador por nombre, NIF o código.
- **Ficha de cliente**: datos, avisos (siniestros de los últimos 2 años, recibos devueltos, «no aparece en el último export»), pólizas, vinculados y documentos.
- **Ficha de póliza**: avisos de anulada, suspendida, vencida o próxima a renovar; garantías, riesgo, recibos, siniestros de 2 años y ofertas. La comisión solo la ve el administrador.
- **Roles**: el empleado no entra en Salud (error 403) y no ve comisiones. Cada despacho solo ve sus datos.
- **Aviso importante**: el cambio de usuario de la demo no es seguridad real. El acceso con usuario y contraseña se construye después.

## Documentos descargables (nuevo)
En la ficha de cada cliente, el botón **Descargar** entrega en PDF la póliza y la copia de identificación (DNI/NIF o CIF). Son documentos **ficticios**, generados al vuelo desde los datos, con marca de agua «FICTICIO» y sin imitar ningún documento oficial. Cada descarga queda en el registro de actividad.

## Renovaciones y avisos (nuevo)
- **Qué entra:** pólizas en vigor y renovables que vencen en 60 días o menos (o hasta 90 si la compañía ya avisó del precio). Con el ejemplo salen 33 renovaciones.
- **Qué se hace con cada una:**
  - *Con ofertas:* hasta 3 alternativas de otras compañías, ordenadas por precio, con al menos un 7 % de ahorro (umbral supuesto, a confirmar).
  - *Sigue siendo buena opción:* no hay alternativa mejor; se recuerda lo que tiene y solo hay botón «Prefiero que me llamen».
  - *Aviso de salud o vida:* sin ofertas.
  - *Retenida:* hay un recibo devuelto o impagado, o el cliente no tiene ningún canal. No se avisa hasta que decida un empleado.
  - *Fuera de plazo:* faltan menos de 30 días; ya no se puede cambiar de compañía. Se gestiona a mano.
  - *Falta tarificar:* no hay ofertas ni precio de referencia.
- **Aprobación:** nada se envía sin que una persona pulse «Aprobar y enviar». El texto debe estar validado por el administrador; si el texto cambia, hay que validarlo de nuevo.
- **Canales:** correo si hay correo válido; WhatsApp solo con consentimiento y móvil válido. Se envía por los dos cuando están disponibles.
- **Botones del correo:** enlaces únicos que caducan 30 días antes del vencimiento. La página de respuesta pide confirmar (así los antivirus de correo no responden por el cliente) y solo vale la primera respuesta.
- **Envío simulado:** en la prueba no sale nada real. Todo queda en la bandeja de salida. El envío real de correo y WhatsApp se conecta en una sola pieza (`EmisorSimulado`), cuando haya proveedor y dominio.
- **Marca blanca:** el cliente solo ve el nombre del despacho; ningún texto menciona la aplicación.

## Los 18 errores que detecta
NIF/CIF inválido · NIF repetido · posible cliente duplicado · cliente sin contacto · correo inválido · móvil inválido · acepta WhatsApp sin móvil · póliza en vigor ya vencida · póliza anulada o suspendida · póliza sin cliente · fechas incoherentes · prima neta + impuestos ≠ total · comisión ≠ prima neta × % · póliza o cliente que no aparece en el último export · recibo devuelto o impagado · recibo sin póliza · siniestro sin póliza.

## Resultado con el Excel de ejemplo
- La carga coincide con el Excel: mismas filas en las 9 hojas y la misma suma de primas. Ninguna fila rechazada.
- La primera revisión abre 39 avisos: 10 recibos devueltos o impagados, 7 pólizas en vigor ya vencidas, 7 NIF inválidos, 8 móviles inválidos, 5 casos de WhatsApp sin móvil y 2 pólizas anuladas o suspendidas.
- Los 7 NIF inválidos son CIF inventados por mí al generar el ejemplo. El validador está comprobado con DNI, NIE y CIF reales conocidos.
- Los 8 móviles inválidos son teléfonos fijos (976…) guardados en el campo móvil, normalmente de empresas.

## Pruebas automáticas (49, todas superadas)
Incluyen una cartera limpia (0 errores), una cartera con 20 errores sembrados (se detectan exactamente esos y ninguno más), reimportación sin duplicados, cierre y reapertura de incidencias, aislamiento entre despachos y registro inmutable. Las pantallas se prueban con todas las fichas del ejemplo (44 clientes y 79 pólizas), los roles, las cifras en pantalla y el aislamiento entre despachos. Las renovaciones se prueban con escenarios construidos (umbrales, plazos, canales, retenciones, caducidad de enlaces) y contra un cálculo independiente con pandas sobre el ejemplo. Se rompieron reglas a propósito (el umbral de ahorro y la validación de textos) y las pruebas fallaron. La demo navegable, con aprobación y descargas, se probó en un navegador real sin pantalla. Para comprobar que las pruebas valen, rompí a propósito una regla y la prueba falló.

## Qué todavía no está hecho
- Acceso con usuario y contraseña.
- Avisos por correo al administrador tras cada subida de datos.
- Envío real de correo y WhatsApp (proveedor, dominio y consentimientos).
- Multitarificador: hoy las opciones salen de las ofertas anotadas a mano.
- Edición de los textos por el despacho (hoy son fijos y se validan tal cual).
- Mensajes para las compañías tras la respuesta del cliente.
- Revisión diaria programada (ahora se ejecuta a mano).
- La tecnología definitiva: esta prueba usa Python y SQLite. El producto real usaría PostgreSQL alojado en la Unión Europea.
- Los recibos devueltos aún no tienen estados de gestión (fase 6).

## Cómo ejecutarla
    cd saas
    python3 demo.py                 # carga el Excel y muestra el contador de salud
    python3 exportar_demo.py        # genera demo.html con todas las pantallas
    (los scripts leen el Excel de ejemplo de la carpeta superior: export_ejemplo_correduria.xlsx)
    python3 -m pytest -q            # ejecuta las pruebas
