# initial-setup-pdn-stack

Monta un proyecto nuevo sobre el stack **PDN — PostgreSQL · Django REST Framework ·
Next.js** con la arquitectura ya decidida y probada, y luego guía la construcción de
cada módulo de negocio a partir del contexto que le des.

> La skill decide **estructura y buenas prácticas**. El producto, sus nombres y su
> diseño visual los decides tú: no impone librerías de UI, colores ni layouts.

## Qué genera

**Backend (`<proyecto>-back`)**

- Proyecto `config/` con settings 100 % por variables de entorno (`local` / `test` /
  `production`) y `.env.example` documentado.
- Capa `common/`: `BaseModel` (UUID, timestamps, borrado lógico), viewsets que exigen
  permiso en cada acción, decoradores `@required_perms` y `@audit_action`, contrato de
  errores `{code, message, detail}`, utilidades de listados en SQL crudo.
- Identidad separada del perfil: `accounts.DjangoUser` (login por email) y
  `users.User` (organización, roles, permisos).
- **Roles y permisos propios**: catálogo de permisos en un fixture (pks deterministas)
  sincronizado con `sync_permissions`; cada organización arma sus roles. `Group` y los
  permisos de Django quedan ocultos del admin.
- Autenticación JWT: access 15 min, refresh 3 días rotativo que revalida la cuenta;
  activación por invitación, recuperación de contraseña y cambio forzado de contraseña
  temporal; rate limit en endpoints públicos.
- Auditoría de toda mutación, comandos `bootstrap_organization` y `add_permission`,
  tests (21+) y CI de GitHub Actions.

**Frontend (`<proyecto>-front`)** — sobre un `create-next-app` limpio

- Estructura `app/` (rutas delgadas, grupo `(app)` autenticado), `page_components/`,
  `components/`, `actions/`, `redux/`, `libs/`, `hooks/`, `types/` con alias y barrels.
- Sesión: tokens en cookies (los lee `proxy.ts`), perfil en Redux Toolkit persistido,
  cliente axios con refresh proactivo de un solo vuelo, `SessionSync`, `logout()`.
- Páginas funcionales sin estilos: login, olvidé mi contraseña, restablecer contraseña,
  activar cuenta y home.
- Permisos en la UI (`usePermissions`, `<Can>`) espejo del catálogo del backend, y
  mapeo de códigos de error a textos en `libs/api-messages.ts`.

Cada repositorio queda con su `CLAUDE.md`, para que las siguientes sesiones sigan las
mismas convenciones.

## Cómo usarla

Con la skill instalada, pídele algo como:

> "Monta un proyecto nuevo con la skill initial-setup-pdn-stack. Se llama Acme y es una
> plataforma para gestionar órdenes de servicio."

La skill te hará una sola ronda de preguntas (nombre, idioma, zona horaria, dónde crear
los repos, dueño inicial…), te mostrará el plan y, al confirmarlo, generará y
verificará ambos repositorios. Después, describe cada módulo del negocio y lo construirá
siguiendo el playbook.

## Requisitos

Python 3.12+, Node.js 20.9+, PostgreSQL 15+ accesible y git.

## Contenido

```
SKILL.md                     instrucciones para el agente (punto de entrada)
references/                  documentación cargada bajo demanda
  backend-architecture.md    estructura de apps, modelos, settings, migraciones
  access-control.md          usuarios, roles, catálogo de permisos, aislamiento por organización
  auth-and-sessions.md       JWT, refresh, sesión en el front, flujos de contraseña
  api-conventions.md         errores, receta de viewset, listados, auditoría
  frontend-architecture.md   carpetas, páginas, componentes, permisos en la UI
  environments-and-deploy.md variables por entorno, despliegue, CI, checklist de salida
  new-module-playbook.md     cómo agregar un módulo de negocio de punta a punta
assets/backend/              plantilla completa del backend
assets/frontend/             overlay para un proyecto create-next-app
scripts/scaffold.py          copia plantillas, reemplaza placeholders, restaura dotfiles
scripts/pin_requirements.py  fija versiones exactas en requirements.txt
scripts/permission_rows.py   genera/valida filas del fixture de permisos
```

## Verificación de las plantillas

Antes de publicar cada versión se generan ambos proyectos desde cero y se comprueba:
`manage.py check`, migraciones, `sync_permissions`, `bootstrap_organization`, la suite de
tests del backend contra PostgreSQL, `lint` + `tsc` + `build` del frontend y los flujos
completos en navegador (login, refresh, logout, recuperación, activación, cambio forzado).
