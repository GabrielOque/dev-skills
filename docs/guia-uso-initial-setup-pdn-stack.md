# Guía rápida: skill `initial-setup-pdn-stack`

Esta skill crea un proyecto nuevo con **PostgreSQL + Django (backend) + Next.js
(frontend)**, ya estructurado y con login, roles y permisos funcionando. Le dices de
qué se trata tu proyecto y Claude Code monta y verifica los dos repositorios.

## 1. Antes de empezar

Verifica que tienes:

- [ ] **Claude Code** instalado
- [ ] **Python 3.12+** → `python --version`
- [ ] **Node.js 20.9+** → `node --version`
- [ ] **pnpm** → `npm install -g pnpm`
- [ ] **git**
- [ ] **PostgreSQL 15+** instalado y encendido, con su usuario y contraseña a mano
  (es obligatorio)

Y ten listo:

- [ ] El nombre del proyecto y una frase de qué hace
- [ ] Los datos del primer administrador: nombre de la organización, correo,
  nombre y apellido

## 2. Instalar la skill (una sola vez)

Dentro de Claude Code:

```text
/plugin marketplace add GabrielOque/dev-skills
/plugin install initial-setup-pdn-stack@dev-skills
/reload-plugins
```

## 3. Usarla

1. Abre Claude Code en la carpeta donde quieres que queden los proyectos.
2. Pídelo con tus palabras, por ejemplo:

   > Monta un proyecto nuevo con Django y Next.js. Se llama Acme y es una
   > plataforma para gestionar órdenes de servicio.

3. Responde la ronda de preguntas. Cada pregunta trae un valor por defecto; confirma
   y completa solo tus datos.
4. Revisa el plan que te muestra y confírmalo.
5. Espera a que cree y verifique `acme-back` y `acme-front`.
6. Guarda la **contraseña temporal** del administrador que aparece al final. En el
   primer inicio de sesión el sistema te pedirá cambiarla.

## 4. Seguir construyendo

Describe cada parte de tu negocio y la skill la construye en el backend y el
frontend:

> Ahora necesito el módulo de órdenes: cada orden tiene cliente, técnico asignado,
> estado y fecha de entrega.

Antes de escribir código acuerda contigo los datos, los estados y los permisos.

## 5. Ten en cuenta

- **El diseño lo decides tú**: las pantallas salen sin estilos ni librería de UI.
- Los datos sensibles (contraseñas, llaves) van en los archivos `.env`, que nunca se
  suben a git.
- Para recibir versiones nuevas de la skill:
  `/plugin marketplace update dev-skills`
