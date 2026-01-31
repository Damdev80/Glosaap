# 📤 GUÍA: SUBIR CAMBIOS A GIT

Esta guía te enseña paso a paso cómo subir cambios del proyecto Glosaap a GitHub.

---

## 📋 REQUISITOS PREVIOS

- Git instalado en tu computadora
- Acceso al repositorio en GitHub
- Credenciales configuradas (usuario y contraseña/token)

---

## 🚀 PASOS PARA SUBIR CAMBIOS

### PASO 1: Abre la Terminal

1. En VS Code, presiona: **Ctrl + j** (o Ctrl + `)
2. O abre PowerShell en la carpeta del proyecto
3. Verifica que estés en la carpeta correcta:

```powershell
cd C:\Users\[TuUsuario]\Desktop\Glosaap
```

---

### PASO 2: Verifica los Cambios

Antes de subir, mira qué cambios tienes:

```powershell
git status
```

**Resultado esperado:**
```
On branch main

Changes not staged for commit:
  modified:   docs/MANUAL_USUARIO.md
  modified:   app/ui/app.py

Untracked files:
  docs/GUIA_GIT_CAMBIOS.md
```

**Explicación:**
- **modified** = Archivos que ya existían y fueron modificados
- **Untracked files** = Archivos nuevos que Git no conoce aún

---

### PASO 3: Agrupa los Cambios (Staging)

Hay dos formas:

#### Opción A: Agregar TODOS los cambios

```powershell
git add .
```

#### Opción B: Agregar archivos específicos

```powershell
git add docs/MANUAL_USUARIO.md
git add app/ui/app.py
```

**Verifica que se agregaron correctamente:**

```powershell
git status
```

Deberías ver algo como:
```
Changes to be committed:
  modified:   docs/MANUAL_USUARIO.md
  modified:   app/ui/app.py
  new file:   docs/GUIA_GIT_CAMBIOS.md
```

---

### PASO 4: Crea un Commit (Descripción de cambios)

Un commit es una "foto" de los cambios con una descripción:

```powershell
git commit -m "Descripción clara del cambio"
```

**Ejemplos de buenas descripciones:**

```powershell
git commit -m "docs: Agregado manual de usuario completo"
git commit -m "fix: Corregida búsqueda de glosas por rango de fechas"
git commit -m "feat: Añadida funcionalidad Mix Excel para transferencia de datos"
git commit -m "refactor: Optimizado código de homologación"
```

**Formato recomendado:**
- `docs:` = Cambios en documentación
- `fix:` = Corrección de errores
- `feat:` = Nueva funcionalidad
- `refactor:` = Cambios en código sin nueva funcionalidad

---

### PASO 5: Sube los Cambios a GitHub (Push)

Sube tu rama local a GitHub:

```powershell
git push origin main
```

**Si es tu primera vez o estás en una rama diferente:**

```powershell
git push -u origin [nombre-de-rama]
```

**Resultado esperado:**
```
Enumerating objects: 5, done.
Counting objects: 100% (5/5), done.
Writing objects: 100% (5/5), 1.24 KiB
remote: Resolving deltas: 100% (3/3), done.
To github.com:usuario/Glosaap.git
   abc1234..def5678  main -> main
```

---

## 🔄 FLUJO COMPLETO RÁPIDO

Si ya sabes qué cambios quieres subir, usa este comando todo en uno:

```powershell
# 1. Ver estado
git status

# 2. Agregar todos los cambios
git add .

# 3. Crear commit con descripción
git commit -m "Descripción del cambio"

# 4. Subir a GitHub
git push origin main
```

---

## ⚠️ CASOS ESPECIALES

### Caso 1: "Tengo cambios pero no quiero subirlos todavía"

Guarda tus cambios sin perderlos (stash):

```powershell
git stash
```

Para recuperarlos después:

```powershell
git stash pop
```

---

### Caso 2: "Quiero descartar cambios en un archivo"

```powershell
git checkout -- [nombre-archivo]
```

Ejemplo:
```powershell
git checkout -- app/ui/app.py
```

---

### Caso 3: "Cometí un error en el commit anterior"

Si aún no hiciste push, amenda el último commit:

```powershell
git add .
git commit --amend --no-edit
```

O cambia el mensaje:

```powershell
git commit --amend -m "Nuevo mensaje"
```

---

### Caso 4: "Quiero trabajar en una rama diferente"

Crea una nueva rama:

```powershell
git checkout -b [nombre-rama]
```

Ejemplo:
```powershell
git checkout -b feature/homologador-mejorado
```

Luego trabaja normalmente y sube:

```powershell
git add .
git commit -m "Mejoras en homologador"
git push -u origin feature/homologador-mejorado
```

---

### Caso 5: "¿Cómo se hace un Pull Request?"

1. **Después de hacer push en tu rama**, ve a GitHub
2. Haz click en "Compare & pull request" (sale automáticamente)
3. Completa:
   - **Título**: Descripción breve del cambio
   - **Descripción**: Detalles del cambio (qué, por qué, cómo)
4. Click en "Create pull request"
5. Espera revisión y aprobación

---

## 📊 COMANDOS GIT ÚTILES

| Comando | Qué hace |
|---------|----------|
| `git status` | Ver cambios no subidos |
| `git log` | Ver histórico de commits |
| `git diff` | Ver diferencias en archivos |
| `git branch` | Ver ramas disponibles |
| `git pull` | Descargar cambios desde GitHub |
| `git clone [url]` | Descargar repositorio completo |
| `git fetch` | Ver cambios sin descargar |
| `git merge [rama]` | Fusionar rama con actual |

---

## 🎯 RESUMEN RÁPIDO

### Para subir cambios:

```powershell
git status              # Ver qué cambió
git add .               # Agrupar cambios
git commit -m "..."     # Crear commit
git push origin main    # Subir a GitHub
```

### Ver cambios antes:

```powershell
git diff                # Ver diferencias
git log --oneline       # Ver commits recientes
```

### Trabajar en rama:

```powershell
git checkout -b feature/[nombre]   # Crear rama
git add .
git commit -m "..."
git push -u origin feature/[nombre] # Subir rama
```

---

## ✅ CHECKLIST ANTES DE HACER PUSH

- [ ] Verificaste con `git status` qué cambios tienes
- [ ] Los archivos a subir son los correctos (sin archivos temporales)
- [ ] El commit tiene una descripción clara
- [ ] No hay conflictos con otros cambios
- [ ] Hiciste `git push` correctamente

---

## 🆘 AYUDA

Si tienes error, aquí están las soluciones comunes:

### Error: "Permission denied"
- Tu cuenta no tiene acceso al repositorio
- Solución: Verifica credenciales con: `git config --global user.name` y `git config --global user.email`

### Error: "Rejected (non-fast-forward)"
- Otros subieron cambios antes que tú
- Solución: Primero haz `git pull origin main`, luego `git push origin main`

### Error: "File is dirty" o cambios sin guardar
- Tienes cambios sin commitear
- Solución: `git add .` y `git commit -m "..."` primero

### Error: "Merge conflict"
- Dos personas editaron el mismo archivo
- Solución: Abre el archivo, elige qué cambios mantener, luego `git add .` y `git commit`

---

## 📞 REFERENCIA RÁPIDA

Guarda esta tabla en favoritos:

**Workflow típico:**
1. Haces cambios en archivos
2. `git add .` — Preparas cambios
3. `git commit -m "Descripción"` — Guardas con descripción
4. `git push origin main` — Subes a GitHub

**Mientras trabajas:**
- `git status` — ¿Qué cambié?
- `git log` — ¿Qué he hecho?
- `git diff` — ¿Cuáles son las diferencias exactas?

**Antes de push:**
- `git pull origin main` — Descargar cambios de otros
- `git status` — Verificar todo está listo
- `git push origin main` — Subir

---

**Última actualización:** Enero 2026  
**Repositorio:** Glosaap  
**Rama principal:** main

---

*Para más ayuda con Git, consulta: https://git-scm.com/book/es/v2*
