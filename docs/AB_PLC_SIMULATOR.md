# Integración AB-PLC Simulator → AB-Modbus Studio

**Suite MS ROBOTIKA** · Cliente Modbus TCP de solo lectura conectado a una CPU **simulada**, en el mismo ordenador.

## Puesta en marcha

1. Instala Node.js 20+ para AB-PLC Simulator.
2. En el proyecto [AB-PLC Simulator](https://github.com/msrobotika/AB-PLC-Simulator), ejecuta npm run sim:modbus. Es un proceso Node independiente del navegador y únicamente escucha en 127.0.0.1:1502.
3. Abre AB-Modbus Studio como cliente, en otra consola, con python -m ab_modbus.
4. En el formulario de lectura configura:
   - Dirección del equipo: **127.0.0.1**
   - Puerto TCP: **1502**
   - Unidad TCP: **1**
   - Función: **03 · Holding Registers**
   - Dirección PDU: **0**
   - Cantidad: **5**
   - Autorización LAN: **desactivada**; loopback está permitido por la política safe_target del cliente.
5. Pulsa **Leer datos**. El monitor de tramas reflejará la solicitud y respuesta del proceso de simulación. Repite la lectura para observar cambios de scans y temporizadores.

## Bancos de lectura compatibles

| Función | Direcciones 0-based | Datos simulados |
| --- | --- | --- |
| FC01 Coils | 0–2 | Q0.0, Q0.1, Q0.2 |
| FC02 Discrete Inputs | 0–3 | I0.0, I0.1, I0.2, I0.3 |
| FC03 Holding | 0–4 | Scans, tiempo/100 ms, CV, AI0 ×100, proceso ×100 |
| FC04 Input | 0–1 | AI0 ×100, proceso ×100 |

Las direcciones son offset PDU base cero, no etiquetas visuales 4xxxx. El valor de proceso depende del escenario (paquetes entregados o nivel virtual). Los registros son uint16 saturados.

Para utilizar el depósito en vez del transportador:

    node scripts/serve-modbus.mjs --tank

El comando anterior se ejecuta en el directorio de AB-PLC Simulator, no en AB-Modbus Studio.

## Límites y seguridad

- Solo hay **lecturas**, nunca escritura en máquinas. El servidor rechaza FC05, FC06, FC15 y FC16 por excepción de función ilegal.
- Únicamente se escucha en 127.0.0.1; no se habilita acceso LAN ni red industrial.
- El puente Node tiene su propia CPU de simulación: **no comparte aún el estado con la pestaña web** de AB-PLC Simulator.
- Esta guía documenta el procedimiento de integración. No constituye certificación de equivalencia industrial, precisión física, interoperabilidad universal ni funciones de seguridad.
- Detén el puente con Ctrl+C al terminar. No publiques el puerto mediante redirecciones ni túneles externos.

[Contrato de integración de la Suite](https://github.com/msrobotika/AB-PLC-Simulator/blob/main/docs/SUITE_PROTOCOL.md).
