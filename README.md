<p align="center"><img src="static/logo.svg" width="120" alt="LechuJob"></p>

# LechuJob

Asistente personal de búsqueda laboral construido sobre **Claude Code**. Lee las alertas de empleo
que llegan a Gmail, filtra las que encajan con tu perfil, las puntúa contra tu CV, arma una ficha
de cada empresa y puesto, y lleva un tracker en Google Sheets con postulaciones, contactos y su estado.

Todo se maneja desde una interfaz local con un botón: **Buscar ofertas**.

## Cómo funciona

```
Gmail (alertas)  ──►  job-scout  ──►  Google Sheet (Ofertas)  ──►  reporte en la app
                                                    ▲
Gmail (respuestas) ─►  tracker  ───────────────────┘  (Postulaciones, Contactos, Resumen)
```

| Pieza | Qué hace |
|---|---|
| `.claude/agents/job-scout.md` | Extrae ofertas de los mails de alerta (LinkedIn, GetOnBoard, Greenhouse, etc.), las filtra según `config/filtros.yaml`, lee el aviso, puntúa el match 0–100 y arma la ficha de empresa y puesto. |
| `.claude/agents/tracker.md` | Revisa Gmail en busca de confirmaciones, "vio tu solicitud", rechazos y entrevistas, y actualiza el Sheet. |
| `.claude/commands/` | `/buscar-ofertas` (scout + tracker) y `/seguimiento` (solo tracker). |
| `app.py` | Servidor local (solo librería estándar de Python) que ejecuta los comandos con `claude -p` y muestra el avance en vivo. |
| `static/` | Interfaz web y logo. |

Los agentes **no postulan ni contactan a nadie**: todo envío queda sujeto a aprobación humana.

## Requisitos

- macOS (el lanzador `.app` es para Mac; la app en sí corre en cualquier sistema con Python 3)
- [Claude Code](https://claude.com/claude-code) con sesión iniciada
- Conectores de **Gmail** y **Google Sheets** habilitados en tu cuenta de Claude

## Instalación

1. Cloná el repo y copiá la configuración:
   ```bash
   cp config/candidato.example.yaml config/candidato.yaml
   ```
2. Creá un Google Sheet con las pestañas `Resumen`, `Ofertas`, `Postulaciones` y `Contactos`
   (encabezados en `.claude/agents/*.md`) y pegá su ID en `google_sheet_id`.
3. Completá tus datos y las rutas a tus CVs en Markdown en `config/candidato.yaml`,
   y ajustá roles, seniority y ubicaciones en `config/filtros.yaml`.
4. Arrancá la app:
   ```bash
   python3 app.py              # abre http://localhost:8765
   ./build_app.sh              # opcional: genera LechuJob.app para el Dock
   ```

## Privacidad

`config/candidato.yaml`, `data/` (reportes, logs y estado) y el `.app` generado están en `.gitignore`.
Ningún dato personal ni ID de documento vive en el código.

## Próximamente

- **cv-tailor**: CV en PDF ajustado a cada oferta (ES/EN).
- **applier**: postulación asistida con Chrome (Easy Apply y formularios externos) con confirmación antes de enviar.
- **networker**: solicitudes de conexión a recruiters.
- Rutina diaria programada.
