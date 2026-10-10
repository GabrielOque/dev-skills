# Changelog — initial-setup-pdn-stack

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versionado:
[SemVer](https://semver.org/lang/es/) — `patch` correcciones, `minor` capacidades nuevas
compatibles, `major` cambios en lo que la skill genera o espera.

## [Unreleased]

## [1.0.0] - 2026-10-10

### Added
- Flujo en cinco fases: descubrimiento, backend, frontend, módulos de dominio y verificación.
- Plantilla de backend: `config/` por variables de entorno, capa `common/`, identidad
  (`accounts`) separada del perfil (`users`), organizaciones, catálogo de permisos con pks
  deterministas y `sync_permissions`, roles por organización, JWT 15 min / 3 días con
  rotación y revalidación, activación, recuperación y cambio forzado de contraseña,
  auditoría, comandos `bootstrap_organization` y `add_permission`, tests y CI.
- Overlay de frontend para `create-next-app`: estructura por carpetas con alias y barrels,
  sesión en cookies + Redux Toolkit persistido, `proxy.ts`, cliente axios con refresh de
  un solo vuelo, `SessionSync`, permisos en la UI y páginas de login, recuperación y
  activación sin estilos.
- Scripts `scaffold.py`, `pin_requirements.py` y `permission_rows.py`.
- Referencias: arquitectura backend y frontend, control de acceso, sesiones, convenciones
  de API, entornos y despliegue, playbook de módulos nuevos.
