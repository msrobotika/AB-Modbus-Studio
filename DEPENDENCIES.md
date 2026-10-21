# Dependencias

## Ejecución desde código

- Python CPython ≥3.11 y biblioteca estándar (licencia PSF y avisos incluidos por Python).
- Navegador moderno del usuario; no se redistribuye con el programa.
- Sin paquetes pip de ejecución; sin pymodbus, libmodbus, Modbus Poll ni equivalentes.
- Interfaz: HTML, CSS, JavaScript y marca gráfica propios, con fuentes del sistema.
  No hay fuentes descargadas, imágenes, CDN ni librerías web de terceros.

## Construcción y distribución

Versiones fijadas en `requirements-build.txt`. PyInstaller 6.16.0 (GPL con excepción
de bootloader), hooks-contrib 2026.9, altgraph 0.17.5 (MIT), packaging 26.3
(Apache-2.0/BSD), setuptools 84.2.1 (MIT). En Windows, pefile 2023.2.7 (MIT) y
pywin32-ctypes 0.2.3 (BSD-3-Clause). Son herramientas de construcción; no son
un motor Modbus. Revisa también sus avisos y dependencias transitivas al cambiarlas.

El portable contiene CPython y el bootloader de PyInstaller, con los avisos
copiados por `tools/build.py` en `licenses/`. `BUILD-INFO.json` documenta la
plataforma y herramientas usadas. Mantén esos avisos junto al ejecutable.
No se garantiza que dos construcciones sean idénticas byte a byte.

CI usa actions/checkout v4, actions/setup-python v5, actions/upload-artifact v4
y la CLI `gh` de los runners GitHub para generar un borrador de Release.
Las acciones se referencian por versión mayor; fijarlas por SHA y generar un SBOM
completo son mejoras pendientes. No se ejecutan en el usuario final.
