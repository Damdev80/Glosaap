---
name: Glosa Secrets
description: Migrar secretos de base64 y texto plano a almacenamiento seguro
---

# Glosa Secrets

Úsalo antes de tocar `app/core/session_manager.py`, `app/service/credential_manager.py` o archivos de credenciales.

## Estado actual (compat legacy retirada)
- `session_manager.py` y `credential_manager.py` custodian en keyring/DPAPI.
  Los formatos legacy (base64/plano) ya NO se leen: se ignoran y exigen
  re-login / re-guardar. No reintroducir ramas de compat.
- Sin `chmod 600`, sin file locking, sin expiración en versiones viejas;
  riesgo de commit accidental si alguien revive esos formatos.

## Migración
1. Usa `keyring` (DPAPI en Windows) como backend principal; fallback `cryptography.fernet` con clave en keyring, nunca en disco.
2. Agrega `cryptography` a `requirements.txt` (hoy ausente y rompería en limpio).
3. Mantén compatibilidad de lectura con formato viejo una versión, escribe solo formato nuevo.
4. `SESSION_FILE` y `credentials.json` con `chmod 600` donde aplique; maneja `JSONDecodeError`/`binascii.Error` sin tragar el error con `print`.
5. Verifica `.gitignore` incluya `.session.json`, `credentials.json`, `temp/config/`, `temp/perfil_chrome/`.
6. Tras migrar, pide rotación de contraseñas IMAP y portales (las actuales se consideran expuestas).

## Prohibido
- Guardar secretos nuevos en base64 o plano.
- Commitear `.env` con `GITHUB_TOKEN`.
