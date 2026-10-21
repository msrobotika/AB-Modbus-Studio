# Avisos de terceros

El código propio de AB-Modbus Studio se distribuye bajo MIT. Sus dependencias
y runtimes conservan las condiciones originales; la licencia MIT del proyecto
no cambia sus licencias.

- [Python: licencia e historial](https://docs.python.org/3/license.html).
  El portable incluye una copia de la licencia del intérprete empleado.
- [PyInstaller: licencia y excepción de distribución del bootloader](https://pyinstaller.org/en/stable/license.html).
  El portable incluye `licenses/PYINSTALLER-COPYING.txt`. La excepción permite
  distribuir programas empaquetados bajo sus propias licencias; cualquier
  modificación o redistribución de la herramienta debe revisarse aparte.
- Las herramientas adicionales de construcción se enumeran en DEPENDENCIES.md;
  no se incorpora código suyo al motor ni a la interfaz.

La biblioteca estándar y el runtime pueden incluir componentes con avisos
adicionales recogidos en la licencia de Python. Esta lista no constituye un
SBOM transitivo certificado. Revisa el contenido efectivo de cada binario al
reconstruir, añadir dependencias o distribuir comercialmente.
