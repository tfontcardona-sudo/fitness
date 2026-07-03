# Política de seguridad

## Reportar una vulnerabilidad
Si detectas un problema de seguridad, **no abras un issue público**.
Escribe en privado a: **tfontcardona@gmail.com** con los detalles y pasos para
reproducirlo. Se responderá lo antes posible.

## Secretos y credenciales
- Este repositorio **no contiene** claves ni credenciales reales.
- Toda la configuración sensible vive en `.env`, que está **excluido** del
  repositorio (ver `.gitignore`).
- Los valores de `.env.example` son **solo de ejemplo** para desarrollo; en
  producción deben sustituirse por secretos largos y aleatorios.

## Datos personales (RGPD)
- Los datos de clientes (carpeta `storage/`) **nunca** se versionan ni se
  publican: contienen información de salud protegida.

## Licencia
Software propietario. Ver [`LICENSE`](LICENSE): todos los derechos reservados.
