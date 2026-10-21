# Seguridad

Este MVP es una herramienta de laboratorio de solo lectura. No es un componente
de seguridad industrial. Usa equipos y redes sobre los que tengas autorización.

## Controles implementados

- Funciones permitidas: 01, 02, 03, 04. Se rechazan las demás antes de abrir socket.
- No existe envío de PDU arbitraria ni API de escritura. El simulador responde
  excepción 01 a escrituras y funciones no admitidas, sin modificar memoria.
- Web y simulador enlazan exclusivamente con 127.0.0.1. No hay escucha 0.0.0.0.
- El cliente usa IPv4 literal, sin resolución DNS. Loopback por defecto; redes
  RFC1918 requieren permiso explícito en cada sesión/destino. IP públicas,
  link-local, multicast y nombres de host arbitrarios se rechazan.
- Secreto aleatorio de 256 bits por proceso, pasado inicialmente en fragmento URL,
  después en Authorization. Se elimina del fragmento y vive en sessionStorage.
- Host exacto (incluido puerto), Origin exacto si viene presente y bloqueo cross-site;
  sin CORS; CSP sin scripts inline, CDN, eval ni framing.
- Cuerpos JSON ≤64 KiB, perfiles con esquema estricto, sin permisos persistidos.
- Máximo 8 manejadores HTTP y 16 conexiones del simulador. El cliente serializa lecturas.
- MBAP limita ADU; timeout total de transacción 100–10000 ms; simulador 2 s por
  trama, máximo 120 solicitudes/conexión y 50 respuestas/s por conexión.
- Parar el simulador cierra sus conexiones activas. No hay reintentos automáticos.
- Monitor de 500 eventos en RAM; solo exportación explícita a disco.

## Límites

La API local no es un servicio de red endurecido; no la publiques con proxy,
túnel ni redirección. Los límites de hilos acotan recursos pero no impiden toda
denegación de servicio local. Un proceso con permisos del mismo usuario o una
extensión maliciosa puede inspeccionar la sesión; no hay aislamiento frente a él.
El token de consola/URL es sensible: no compartas esa URL ni capturas que la muestren.

Modbus TCP clásico no autentica ni cifra. La activación de red privada no prueba
que el destino esté autorizado. No conectes la aplicación a Internet ni producción
sin un análisis de riesgos y controles externos adecuados.
Una lectura puede sobrecargar un PLC; el intervalo mínimo de UI no limita a
clientes externos del simulador. No hay protección contra modificaciones del código
por quien lo ejecuta. No hay auditoría de seguridad externa ni certificación.

Los perfiles y tramas exportados pueden revelar direcciones y datos del equipo.
Revisa su contenido antes de compartirlos. No se incluyen secretos de sesión.
No subas vulnerabilidades con detalles de tus equipos a incidencias públicas;
coordina primero un canal privado con el propietario del repositorio.
