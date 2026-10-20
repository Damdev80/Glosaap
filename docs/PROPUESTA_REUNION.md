# Propuesta para la reunión — Glosaap + Datos clínicos

## Dónde estamos
Glosaap gestiona glosas (Mutualser y Coosalud en producción, Sanitas en desarrollo). La homologación de códigos vive en Excels compartidos en red: funciona, pero se edita a mano, se bloquea entre usuarios y no deja auditoría.

## Propuesta: homologación en SQL Server (migración progresiva, sin downtime)
1. Tablas `homologacion` + `homologacion_auditoria` (una sirve para todas las EPS).
2. Migración por olas con gates: sombra (Excel manda, DB espeja y se comparan) → dual por EPS → DB primaria con Excel de respaldo → adiós Excel.
3. Conexión cifrada, login de mínimo privilegio, credenciales en keyring (nada en código).

## Oportunidad: Dinámica Gerencial (DGH)
Los "Código producto en DGH" salen del HIS. Si hay acceso de lectura a su BD (SQL Server):
- El catálogo maestro se lee directo de DGH (adiós digitación y Excel desactualizado).
- `COD_SERV_FACT` se valida contra el catálogo vivo.
- Esto puede reemplazar media migración: el dato ya existe, solo hay que leerlo.

## Decisiones que necesitamos de ustedes
1. ¿Quién edita hoy la homologación y quién debería poder hacerlo?
2. ¿Quién autoriza accesos (DBA) al SQL Server y a la BD de DGH? ¿Qué versión de DGH usan?
3. ¿Glosaap solo lee DGH, o algún otro sistema necesita una API REST interna? (Si es solo Glosaap, SQL directo basta.)
4. ¿Qué duele más: **Evitar** glosa (prevenir antes de facturar) o **Responder** glosa? Eso define el roadmap.
5. ¿Hay política de datos (quién ve qué) que condicione accesos y auditoría?

## Compromiso propuesto
Ola 0 (seguridad + tablas) → acceso lector DGH → migración por olas con reportes de validación en cada gate. Sin interrumpir el uso diario.
