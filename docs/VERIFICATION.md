# Verificación de 0.1.0

Fecha: 21 de octubre de 2026. Estas evidencias describen pruebas realizadas,
no una certificación industrial ni una promesa de ausencia de fallos.

## Local

- Windows x86_64, CPython 3.13.7: suite de pruebas automatizadas con unittest.
- Autoprueba real por TCP de FC01, FC02, FC03 y FC04 contra el simulador local.
- Portable Windows generado con PyInstaller 6.16.0 y autoprueba ejecutada desde
  el EXE resultante, sin importar paquetes del código fuente.
- Interfaz ejercitada en navegador: arranque del simulador, lectura FC03 y FC01,
  edición de memoria local con lectura posterior y guardado/carga de perfiles.
- Captura real de la UI obtenida durante la lectura; no es un diseño ficticio.

## Cobertura automatizada

Vectores binarios con resultados conocidos; límites de bits/registros; direcciones
y tipos no válidos; MBAP incorrecto; byte count incoherente; excepciones;
relleno de bits; 400 rondas generadas con semilla fija y 500 entradas malformadas;
TCP segmentado y solicitudes concatenadas; cierre truncado; transacción/unidad
ajenas; plazo total frente a goteo; escrituras rechazadas antes del socket y en
el simulador; cierre de conexiones al detener; rollover de TID; monitor acotado;
políticas de IP; Host/Origin/token; JSON/tamaños; persistencia e importación segura.

## GitHub

La ejecución inicial de CI pasó en Ubuntu y Windows con Python 3.11 y 3.13:
[ejecución 39654565080](https://github.com/msrobotika/AB-Modbus-Studio/actions/runs/39654565080).
Las ejecuciones posteriores, incluidas las del tag de entrega, se consultan en
[Actions](https://github.com/msrobotika/AB-Modbus-Studio/actions).
Un enlace al repositorio no prueba por sí mismo que un portable esté publicado;
comprueba el archivo concreto en Releases y su SHA-256.

## Pendiente

No se han probado PLC físicos, adaptadores serie, Modbus RTU, redes públicas,
TLS Modbus Security, versiones antiguas de glibc, todas las distribuciones Linux,
ni conformidad mediante laboratorio acreditado. Tampoco se ha realizado auditoría
externa de seguridad, revisión jurídica profesional ni comparación exhaustiva
con todo el código público existente. Los tests propios no sustituyen pruebas de
interoperabilidad con implementaciones y equipos independientes.
