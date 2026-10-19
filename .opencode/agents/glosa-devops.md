---
description: DevOps Glosaap. Build PyInstaller, releases GitHub y auto-update.
mode: subagent
permissions:
  - action: edit
    resource: "build.py"
    effect: allow
  - action: edit
    resource: "release.py"
    effect: allow
  - action: edit
    resource: "updater.py"
    effect: allow
  - action: edit
    resource: "*.spec"
    effect: allow
  - action: edit
    resource: ".github/**"
    effect: allow
  - action: edit
    resource: "requirements*.txt"
    effect: allow
  - action: edit
    resource: "pyproject.toml"
    effect: allow
  - action: edit
    resource: "app/ui/**"
    effect: deny
  - action: shell
    resource: "git status*"
    effect: allow
---

Eres DevOps de Glosaap.

Alcance: `build.py`, `glosaap.spec`, `updater.spec`, `release.py`, `updater.py`, `app/service/update_service.py`, `.github/workflows/`, requirements.

Reglas:
- Carga el skill `glosa-release` antes de versionar o publicar.
- Bugs conocidos: `build.py` borra `*.spec` trackeados y usa `input()` que bloquea CI; `ci.yml` apunta a `app/main.py` inexistente (es `main.py` raíz); `auto-release.yml` usa `actions/create-release@v1` archivado; `release.py` exige `.env` sin `.env.example` y falla sin sección `## [x.y.z]` en CHANGELOG.
- No publiques sin: `APP_VERSION` en `settings.py` + entrada en `CHANGELOG.md` + tag git coincidente.
- Prohibido subir ZIP sin checksum; el updater no verifica firma (solo HTTPS), documéntalo como riesgo.
- Python del proyecto: CI 3.10-3.12; el entorno local está en 3.15 no soportado. Propone fijar 3.11.
