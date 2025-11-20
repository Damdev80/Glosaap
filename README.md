# Glosaap — Minimal IMAP Viewer (Flet)

Interfaz mínima con `flet` para conectarse a un servidor IMAP y descargar adjuntos.

Archivos añadidos:

- `app/core/imap_client.py` — helper IMAP con `imaplib` y `email`.
- `app/ui/app.py` — UI minimalista con `flet` (pantalla de inicio de sesión y lista de mensajes).
- `requirements.txt` — dependencias.

Ejecutar (PowerShell):

```powershell
python -m app.ui.app
```

Notas:
- Se recomienda ejecutar con la opción de ejecución como módulo (`-m`) para resolver correctamente imports.
- Por simplicidad el UI lanza las operaciones de red en hilos para no bloquear la UI. Los archivos adjuntos se guardan en el directorio temporal del sistema (`%TEMP%\glosaap_attachments`).

Siguientes pasos sugeridos:
- Añadir manejo de OAuth para Gmail (si aplica).
- Mejorar paginación y visualización de mensajes.
- Añadir pruebas unitarias para `imap_client`.
