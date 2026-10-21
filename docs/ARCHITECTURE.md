# Arquitectura

```text
Navegador local (HTML/CSS/JS propios)
          │ API loopback + Bearer efímero
   application.py ─── profiles.py (JSON estricto y reemplazo atómico)
       │       │
   client.py   server.py (simulador, memoria sin conexión a hardware)
       └── transport.py ── sockets TCP
                │
           protocol.py (PDU/MBAP puras)
                │
           monitor.py (deque de eventos)
```

El cliente valida antes de conectar. Una transacción usa una conexión propia;
el plazo total abarca connect/send/receive, evita goteo indefinido de bytes y
se comprueba entre lecturas. No se reutiliza un socket con datos residuales.
Las respuestas deben coincidir en TID, unidad, función y tamaño; las excepciones
se distinguen de errores de transporte. No hay reintento de lectura implícito.

El servidor mantiene bancos separados de bits y uint16, protegidos por lock.
Recibe exactamente una ADU según MBAP, de modo que funciona con segmentación
y concatenación de TCP. Solo devuelve funciones de lectura o excepciones.
El editor de memoria modifica ese modelo local, nunca utiliza el cliente.

La UI no ejecuta protocolo ni sockets: su permiso LAN es un booleano explícito
que el backend comprueba. Una importación de perfiles no puede activar el permiso.
La sesión de navegador no vuelve a conectar automáticamente a ningún PLC.
Cerrar la pestaña para la repetición pero el proceso sigue activo hasta cerrarlo
desde la app o consola. Se documenta ese comportamiento en vez de ocultar servicios.

La extensión RTU compartirá la PDU y tendrá su propio framing, CRC y transporte;
no se enviarán cabeceras MBAP por el puerto serie.
