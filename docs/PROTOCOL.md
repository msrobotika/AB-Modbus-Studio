# Contrato de protocolo y procedencia

Consulta normativa realizada para esta entrega: 21 de octubre de 2026.

- [Application Protocol V1.1b3](https://www.modbus.org/file/secure/modbusprotocolspecification.pdf),
  apartados 4.2–4.4, 6.1–6.4 y 7: codificación, direccionamiento y lecturas.
- [Messaging on TCP/IP V1.0b](https://www.modbus.org/file/secure/messagingimplementationguide.pdf),
  apartados 3.1.2–3.1.3: encapsulado TCP y MBAP.
- [Serial Line V1.02](https://www.modbus.org/file/secure/modbusoverserial.pdf):
  referencia futura para RTU, no una funcionalidad implementada en 0.1.
- [Índice oficial vigente](https://www.modbus.org/modbus-specifications).

Resumen propio del contrato implementado: FC01/02 aceptan 1–2000 bits; FC03/04
aceptan 1–125 registros. Los registros usan orden de byte de red y los bits se
empaquetan desde el menos significativo. Las direcciones transmitidas empiezan
en cero. La respuesta de excepción contiene función con bit alto y código.
MBAP tiene TID, protocolo cero, longitud que incluye unidad y PDU, y Unit ID.
La PDU se limita a 253 bytes; una ADU TCP no supera 260. El parser rechaza
longitudes incoherentes y el cliente valida correlación de transacción y unidad.

No se ha copiado la arquitectura de ejemplo de la guía. Los módulos se diseñan
para separar funciones puras, E/S, controles de red y presentación. No se han
consultado repositorios de implementaciones Modbus para escribir este código.
Los vectores hexadecimales de conformidad se comprueban con resultados conocidos;
no se redistribuyen documentos normativos, capturas o diagramas de terceros.

Los perfiles usan JSON propio de schema 1. No se promete compatibilidad con
perfiles, interfaces ni archivos de programas comerciales existentes.
