# AB-Modbus SCADA · Vista de supervisión (alfa)

Extensión original de **AB-Modbus Studio** bajo licencia MIT.
El cliente y el simulador reutilizan el motor Modbus TCP de este mismo repositorio,
sin librerías externas de SCADA y sin copiar las interfaces comerciales.

## Arranque

1. Ejecuta `python -m ab_modbus` o el portable disponible.
2. Abre la URL que proporciona la aplicación y entra en **AB-Modbus SCADA**
   desde su navegación. No abras `scada.html` como archivo suelto: se sirve desde
   la API local protegida.
3. Pulsa **Laboratorio local**: el backend inicia su simulador TCP en loopback,
   realiza una lectura FC03 y muestra 8 registros.
4. Ajusta los umbrales del canal que te interese. Ejemplo demostrativo: canal 1,
   umbral alto 220; el registro predeterminado 230 provocará alerta.
5. Pulsa **Iniciar supervisión** para sondeo periódico (mínimo 1000 ms).
6. Selecciona un canal para su tendencia y exporta CSV cuando quieras.

## Funciones en esta versión

- Supervisión *read-only* mediante FC01–FC04 del motor existente.
- Un dispositivo por sesión; adquisición secuencial sin reintentos ocultos.
- Vista de puntos y tendencias SVG propias, sin CDN ni telemetría.
- Umbrales altos/bajos por índice de registro, estados activos, recuperación
  y reconocimiento de eventos **solo informativo**.
- Histórico de hasta 1000 muestras por pestaña y CSV exportable;
  registro de hasta 150 eventos en memoria.
- La supervisión no se inicia sola al abrir la aplicación; la autorización
  de acceso a red privada exige opt-in y se borra al modificar destino/perfil.
- Una lectura fallida interrumpe el sondeo y registra una alarma de comunicación.
- Al ocultar la pestaña, navegar fuera o cerrarla se detiene el sondeo.

## Límites y seguridad

**No es un SCADA de seguridad ni un historian industrial.** Las alarmas dependen
de una pestaña abierta, no garantizan notificaciones ni persistencia.
No sirve para parada de emergencia, interlocks, protección o procesos críticos.
No hay comandos de escritura, setpoints al equipo ni acceso remoto público.

Los valores se muestran como registros **brutos**. Los nombres de canal, unidades,
escala, signo y formato multirregistro deben documentarse y verificarse con
la hoja de datos de cada equipo antes de una instalación real. No interpretar
230 automáticamente como °C, bar o rpm. Modbus TCP tradicional carece de cifrado
y autenticación: emplea VLAN o redes de laboratorio aisladas y permisos explícitos.

En esta fase el histórico y el reconocimiento de alarmas están **solo en memoria
del navegador** y se pierden al cerrar o recargar. El CSV se genera localmente
en el cliente. No hay base de datos persistente, notificaciones externas, RTU,
múltiples PLC concurrentes, redundancia o certificación de seguridad.

## Capturas reales y tests

`tools/capture_scada.py` inicia el backend real y usa Chromium/Playwright
contra el simulador TCP incluido; exige los ocho valores FC03 esperados y una
alarma por umbral, y genera:
- `docs/screenshots/scada-escritorio.png`
- `docs/screenshots/scada-tendencias.png`
- `docs/screenshots/scada-movil.png`

Se integró en [GitHub Actions](../.github/workflows/screenshots.yml).
El script necesita Playwright únicamente **para documentar y probar la interfaz**,
no para ejecutar AB-Modbus Studio. Las capturas son válidas cuando el job las
haya generado y los archivos PNG estén visibles en la rama publicada.

## Siguientes hitos

- Etiquetas, unidades y escalas verificadas, configuración exportable.
- Historian SQLite con límites de almacenamiento, política de retención y pruebas.
- Gestor de alarmas en backend con marca temporal, umbral, histéresis,
  diagnóstico de valores obsoletos y revisión del modelo de amenazas.
- Varios dispositivos autorizados, permisos por equipo y pruebas de carga.
- Exportación de datos hacia AB-BI Studio por interfaz documentada.

Copyright © 2026 MS ROBOTIKA. MIT.
