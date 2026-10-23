# Auditoría funcional de AB-Modbus Studio — 23/10/2026

**Estado del producto:** EXPERIMENTAL (cliente Modbus TCP read-only con laboratorio local). **AB-Modbus SCADA** es un módulo de esta app, no un repositorio separado. No se han probado dispositivos físicos.

## Origen y control de cambios

- Repositorio: https://github.com/msrobotika/AB-Modbus-Studio
- SHA main antes de trabajar: 1ffa4063940203d070c82ef51c5f4c3cc4c023a1
- Rama: qa/release-smoke-modbus-scada-20261023
- No se modifica el código original del motor ni se sustituyen las Releases: esta entrega instala exclusivamente pruebas y evidencia.
- Releases previamente publicadas: https://github.com/msrobotika/AB-Modbus-Studio/releases/tag/v0.1.0 (pre-release, ZIP Windows + Linux y SHA256SUMS.txt).
- Capturas reales del módulo SCADA: las genera el propio tools/capture_scada.py con un navegador Chromium, lectura real FC03 de ocho registros del simulador local y alarma informativa sobre umbral 220. No es un ensayo de seguridad industrial.

## Pruebas ejecutables

### Fuente (en Ubuntu y Windows, Python 3.13)

    python -m unittest discover -v
    python -m ab_modbus --self-test
    node --check ab_modbus/web/scada.js

### Browser (Ubuntu, Chromium real)

    python -m pip install "playwright==1.55.1"
    python -m playwright install --with-deps chromium
    python tools/capture_screenshots.py
    python tools/capture_scada.py

Se suben capturas a un artefacto independiente de la PR y no se publican de forma automática en main.

### Distribución PUBLICADA e inmutable

Con GitHub CLI y los permisos de solo lectura:

    gh release download v0.1.0 --repo msrobotika/AB-Modbus-Studio --dir <directorio>
    python tools/verify_published_release.py --assets-dir <directorio> --platform Linux

En Windows, sustituir Linux por Windows. La prueba exige los ZIP verdaderos, verifica **SHA256SUMS.txt**, descomprime de forma controlada, arranca **el binario distribuido**, comprueba FC01–FC04 mediante --self-test, y prueba su servidor HTTP autenticado con token temporal en localhost. Comprueba además que se entregan los recursos SCADA actuales: /scada.html, /scada.js y /scada.css.

**Si el ZIP antiguo no contiene SCADA**, las pruebas deben FALLAR con RELEASE_GAP. No se presentará ese paquete como actualización del módulo, no se reescribirá la etiqueta v0.1.0 ni se publicará una release silenciosa. Primero corregir o versionar nueva candidata, repetir tests de instalador y acreditar licencias.

## Seguridad, límites y comunicación

- Solo lectura Modbus FC01, FC02, FC03, FC04 y simulador TCP en 127.0.0.1.
- Ninguna prueba envía mensajes a un PLC industrial.
- El HTML/JS expuesto por el paquete se comprueba con el servidor real; tampoco una lectura del simulador acredita compatibilidad de hardware.
- Los ZIP portables son ejecutables empaquetados, no simples archivos de fuentes. El código de main puede haber avanzado desde el release: informar por separado.
- Permisos de red LAN requieren autorización explícita; no desplegar puentes ni abrir puertos a Internet.
- Esta auditoría no acredita funcionamiento en máquina industrial, ni certificación de ciberseguridad/seguridad funcional.

## Matriz de resultados

| Evidencia | Fuente | Estado |
| --- | --- | --- |
| Inventario de Release, SHA-256, arranque ZIP Windows | CI nueva qa-release-smoke.yml | PENDIENTE_RESULTADO_CI |
| Inventario de Release, SHA-256, arranque ZIP Linux | CI nueva qa-release-smoke.yml | PENDIENTE_RESULTADO_CI |
| Fuente 3.13 Windows / Ubuntu + unidad + CLI | CI nueva qa-release-smoke.yml | PENDIENTE_RESULTADO_CI |
| Chromium real FC03, alarma y capturas | CI nueva qa-release-smoke.yml | PENDIENTE_RESULTADO_CI |
| PLC de planta y redes externas | Ninguna prueba autorizada | NO_VERIFICADO |
| Traffic (vistas, usuarios únicos) | Insights privado | NO_DISPONIBLE |

No sustituir estos marcadores por PASADO hasta obtener conclusiones/logs y SHA de cada workflow.
