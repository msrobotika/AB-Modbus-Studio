# Revisión legal preliminar — 21 de octubre de 2026

Alcance: revisión documental del origen, licencia y distribución de esta entrega.
No es un dictamen de abogado, auditoría de propiedad intelectual ni garantía de
ausencia de infracción en España, UE u otras jurisdicciones.

## Origen y licencia elegida

Motor, interfaz, pruebas y documentación propia se han creado para MS ROBOTIKA
con asistencia de IA; no se incorporó código de otras implementaciones Modbus.
Se consultaron especificaciones públicas para interoperabilidad y se identifican
en PROTOCOL.md. Los documentos normativos y sus diagramas no se redistribuyen.
La autoría legal y la protección del material asistido por IA pueden depender de
aportaciones humanas y de la jurisdicción; este aviso no decide esa titularidad.

Se incluye el texto de la [licencia MIT publicada por OSI](https://opensource.org/license/mit).
MIT permite uso, modificación y redistribución sujeto a conservar sus avisos y
contiene exclusión de garantías. No proporciona autorización de marcas ni una
concesión de patentes expresa equivalente a la de Apache-2.0. No inmuniza frente
a derechos ajenos ni elimina obligaciones legales imperativas.

## Marca e interoperabilidad

La especificación V1.1b3 identifica MODBUS como marca registrada de Schneider
Automation Inc. Se usa descriptivamente para indicar el protocolo. El proyecto
no usa logotipos oficiales ni afirma afiliación, aprobación o certificación.
Véanse [especificaciones oficiales](https://www.modbus.org/modbus-specifications)
y [aviso legal del sitio](https://www.modbus.org/legal).
La disponibilidad del nombre en GitHub no equivale a una búsqueda registral.
Queda pendiente comprobar «AB-Modbus Studio» y «MS ROBOTIKA» en los territorios
y clases relevantes antes de registrar o comercializar marcas.

## Dependencias y distribución

El código fuente no necesita paquetes externos de ejecución. El portable incluye
runtime Python y bootloader PyInstaller: se conservan sus licencias separadas.
La [documentación de PyInstaller](https://pyinstaller.org/en/stable/license.html)
describe la excepción de su bootloader; se distribuye una copia junto al binario.
La [licencia de Python](https://docs.python.org/3/license.html) contiene su historial
y avisos adicionales. Cambiar dependencias requiere revisar de nuevo licencias,
componentes efectivos y obligaciones de redistribución.

## Pendientes que no deben anunciarse como resueltos

- Búsqueda profesional de marcas, patentes y posibles derechos de terceros.
- Verificación de titularidad, contribuciones humanas y acuerdos con colaboradores.
- Auditoría independiente de similitud, licencias y contenido transitivo del binario.
- Conformidad industrial, límites contractuales de dispositivos y responsabilidad.
- Revisión de privacidad al compartir perfiles o tramas de instalaciones reales.

Esta revisión reduce errores de atribución y distribución evidentes. No garantiza
originalidad absoluta frente a todo software existente, libertad de operación,
certificación de protocolo ni inmunidad jurídica.
