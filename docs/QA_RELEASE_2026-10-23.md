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

## Resultados observados en ejecución PR #1 — 23/10/2026

Evidencia: [Actions 39986719928](https://github.com/msrobotika/AB-Modbus-Studio/actions/runs/39986719928), commit `86d56b7f98ab11b1507848ff02859ad988fe0f36`.

- Fuente Python 3.13: **40 pruebas PASADAS** en Ubuntu y Windows. En Linux, Chromium completó seis capturas auténticas (escritorio, monitor de tramas, móvil, SCADA, tendencias y SCADA móvil), incluida lectura FC03 de valores 230, 1500, 42, 2026, 100, 0, 65535, 1234 y activación de aviso demostrativo de umbral 220.
- Nueva candidata empaquetada desde esa rama (NO Release): PyInstaller 6.16.0 sobre Python 3.13.16, Windows y Ubuntu. Se ejecutó su `--self-test` (FC01–04), se inició HMI localhost, se consultó API con y sin token, y se verificaron las rutas `/scada.html`, `/scada.js`, `/scada.css`: **PASADO ambos SO**. Los artefactos están en la propia ejecución QA de la PR, no en Releases.
- Release publicada v0.1.0: se descargaron los ZIP originales y `SHA256SUMS.txt`, verificando **SHA-256**. Los ejecutables pasaron `--self-test` e HMI autenticada; ambos carecen de los tres recursos SCADA. Este desfase está CONFIRMADO en Linux y Windows: no es un bug supuesto. La ejecución inicial marcó fallo `RELEASE_GAP`; ahora la opción explícita `--expect-legacy-no-scada` comprueba esta ausencia conocida sin vender ese paquete como SCADA.
- No se ha cambiado la Release v0.1.0 ni su checksum, ni se ha instalado en el PC del usuario ni probado con hardware real.

**Pendiente antes de publicar una próxima versión:** elegir nueva versión coherente en aplicación/paquetes, revisión de cambios, SHA256 de distribución final, pruebas en el SHA final y aprobación del responsable. Los logs de la ejecución anterior no sustituyen las pruebas del último commit: comprobar de nuevo la matriz.
