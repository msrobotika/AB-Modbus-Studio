# Contribuir a AB-Modbus-Studio

Gracias por mejorar MS ROBOTIKA. Se admiten incidencias y pull requests reproducibles; las modificaciones a `main` deben poder revisarse sin depender de capturas o resultados inventados.

## Flujo de trabajo

1. Describe el problema con versión, entorno y pasos para reproducirlo; solicita revisión antes de cambiar la arquitectura.
2. Trabaja en una rama temática. Incluye código fuente editable, pruebas automáticas y documentación cuando corresponda.
3. Ejecuta las comprobaciones disponibles en el repositorio. Indica con precisión qué se ha probado y qué no.
4. Adjunta capturas obtenidas del software o hardware real únicamente si puedes documentar su origen, versión, modo demo o equipo de prueba.
5. Completa la plantilla de pull request, enumera riesgos, limitaciones y cómo revertir el cambio.

## Normas específicas

**Sistemas industriales:** separa pruebas de simulador, pruebas de red y pruebas en PLC o hardware. No introducir salidas físicas por defecto ni afirmar conformidad IEC, seguridad funcional, precisión temporal o compatibilidad de fabricante sin validar el caso específico. Incluye tramas/simulaciones sintéticas sin datos reales de instalaciones.

## Dependencias, licencias y secretos

- Respeta la licencia existente; conserva avisos y atribuciones de bibliotecas, tipografías, modelos y recursos.
- No añadir binarios de compilación, carpetas `.pio/build`, cachés, credenciales, claves API ni datos de clientes.
- Los reportes de vulnerabilidad se tratan por un canal privado según `SECURITY.md`. Nunca adjuntes exploits ni contraseñas en incidencias públicas.
