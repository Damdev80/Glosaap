---
name: Glosa Release
description: Versionar, generar changelog, tag y publicar release en GitHub
---

# Glosa Release

Úsalo antes de bump de versión, build o release.

## Workflow
1. Actualiza `APP_VERSION` en `app/config/settings.py` (semver).
2. Agrega entrada `## [x.y.z] - YYYY-MM-DD` en `CHANGELOG.md` (Keep a Changelog). `release.py` falla si no existe y usa `git log` crudo.
3. Sincroniza `pyproject.toml`, `README.md` y `docs/MANUAL_USUARIO.md` (hoy dicen 1.0.0 / 1.3.8 / 0.11.11 distintos).
4. Crea tag git `v{x.y.z}` local antes de publicar; `release.py` no lo crea solo.
5. `GITHUB_TOKEN` viene de `.env` (hay `python-dotenv`, no hay `.env.example` en repo: documéntalo sin commitear el token).
6. Build: `python build.py` genera `release/Glosaap_v*.zip` con `Glosaap.exe + updater.exe + README.txt`. Si hay varios ZIP timestamped, sube el correcto, no `zip_files[0]` a ciegas.
7. Genera checksum (sha256) del ZIP y publícalo en la release. El updater hoy no verifica firma (riesgo supply-chain conocido).

## Prohibido
- Publicar con HEAD sin tag o con tag `v1.0.0` huérfano sin bump (estado actual).
- `input()` bloqueante en scripts de CI.
