---
name: Glosa QA Python315
description: Correr tests y cobertura en el entorno real del proyecto
---

# Glosa QA Python315

Úsalo antes de correr o interpretar tests.

## Entorno real
- Sistema y `.venv` en Python 3.15.0 (no soportado; CI verificado en 3.11-3.12).
- Flet pineado `>=0.27.0,<0.28.0`; falta `cryptography` en requirements aunque el código lo espera.

## Comandos
- Rápido: `pytest tests/ -v --tb=short --no-cov`
- Con cobertura: `pytest` (hereda `--cov-fail-under=15` de `pytest.ini`; `pyproject.toml` se ignora con warning).
- Estado conocido: 461 tests, `460 passed, 1 failed` (`test_navigation.py::TestNavigationControllerSetSize::test_set_window_size` por mock desactualizado), cobertura ~10%.

## Reglas
- Fixtures con `tmp_path`; prohibido tocar `\\MINERVA` en tests.
- `app/ui/app.py`, `business_logic.py` al 0% lastran cobertura; `coosalud_processor 5%`, `mutualser 7%`. Prioriza esos.
- `pytest.ini` es la fuente de verdad, no `pyproject.toml`.
- `ci.yml` hoy fallaría (cobertura + test rojo + path `app/main.py` inexistente).
