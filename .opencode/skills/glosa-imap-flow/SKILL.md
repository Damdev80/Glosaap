---
name: Glosa IMAP Flow
description: Buscar correos de glosas por IMAP sin colgar la app ni traer cuerpos enteros
---

# Glosa IMAP Flow

Úsalo antes de tocar `app/core/imap_client.py`, `app/service/email_service.py` o `app/service/auth_service.py`.

## Workflow
1. Para listar usa `BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)]`, nunca `RFC822` completo.
2. Criterio de búsqueda sin paréntesis redundantes: `SUBJECT "x" SINCE dd-Mon-yyyy BEFORE dd-Mon-yyyy`. Gmail rechaza `(...)` extra.
3. Parsea `msg["date"]` con al menos 6 formatos (incluye `(UTC)`, `-0500`, `GMT`); si falla, marca `email_date=None` explícito en vez de contaminar con `now()`.
4. Valida `folder` contra inyección IMAP antes de `select`.
5. `AuthService.login` corre en thread: los callbacks `on_success/on_error` NO deben tocar UI directo; devuelven al hilo principal.
6. `download_attachments` maneja `msg_id` str/bytes una sola vez; sin doble `decode`.
7. `search_limit` e `IMAP_CONFIG` de `settings.py` son la fuente; no dupliques defaults de Gmail en `email_service`.

## Prohibido
- `fetch_recent` con `search ALL` + cuerpo completo en buzones grandes.
- `time.sleep(0.1)` como "sincronización de UI".
