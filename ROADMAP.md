# Hoja de ruta

## 0.1 — MVP TCP (implementado)

- Motor propio FC01–04, validación MBAP y plazo total de transacción.
- Simulador loopback, monitor, perfiles e interfaz española Windows/Linux.
- Pruebas automatizadas y construcción de portable con licencias.
- Acceso a red privada explícito y escrituras ausentes del motor.

## Extensión SCADA alfa — integrada (pendiente de validación E2E en CI)

- Dashboard original de supervisión read-only para el cliente FC01–04.
- Tendencias SVG, umbrales configurables por canal, eventos y reconocimiento informativo.
- Muestreo secuencial con inicio voluntario, intervalo mínimo de 1000 ms y
  parada en error u ocultación de pestaña.
- Memoria efímera: 1000 muestras; exportación CSV; sin escritura a dispositivos.
- Prueba y capturas de integración con Chromium y simulador local, mediante
  `tools/capture_scada.py` y workflow de GitHub Actions.

**Pendiente:** evidencias del job de navegador, más seguridad, base de datos
de series temporales, unidad/escala configurable y gestión persistente de alarmas.

## 0.2 — Interoperabilidad TCP

- Verificar contra varios equipos reales autorizados y registrar matrices de compatibilidad.
- Ensayar carga y cierre bajo concurrencia, ampliar pruebas generativas y análisis de amenazas.
- Tipos int16/uint32/int32/float32 con orden de palabras explícito y pruebas de vectores.
- Exportación CSV y configuración de escala/unidades sin alterar los valores recibidos.
- Mejorar accesibilidad con lectores de pantalla y pruebas de navegación por teclado.
- Evaluar firma de binarios, SBOM y builds reproducibles (hoy no se garantizan).

## 0.3 — RTU sin hardware (pendiente)

- Implementar CRC16 desde la especificación Serial Line V1.02 y vectores independientes.
- Separar ADU RTU y PDU compartida; probar tramas incompletas, CRC erróneo y límites.
- Modelo de temporización t1.5/t3.5, velocidad, paridad y turnaround; reloj inyectable.
- Transporte serie inyectable y pruebas con canales virtuales. Sin puerto físico por defecto.

## 0.4 — RTU físico de solo lectura (pendiente)

- Elegir y revisar adaptador serie (posible dependencia pySerial, aún no incluida).
- Opt-in por puerto, bloqueo exclusivo y cancelación; sin broadcast de lectura.
- Probar Windows/Linux con adaptadores USB-RS485 y hardware aislado.
- Documentar límites de temporización de USB/OS, ruido, desconexión y reconexión.
- Mantener escrituras bloqueadas hasta una fase distinta con revisión de seguridad.

## Fases posteriores sin fecha prometida

- Evaluar Modbus Security/TLS, sin inventar cifrado propio.
- Evaluar escrituras únicamente con modo de laboratorio, lista de destinos y confirmación
  contextual; no se activarán por migrar un perfil antiguo.
- Revisión jurídica profesional de nombre, marca y distribución comercial, y certificación
  de conformidad si interesa; ninguna se da por realizada.
