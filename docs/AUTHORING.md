# Estándar de autoría de skills

Reglas para escribir, probar y publicar skills en este repositorio. Se basan en la
especificación abierta [Agent Skills](https://agentskills.io/specification) y en las
buenas prácticas de Anthropic para skills; donde este documento es más estricto, manda
este documento (lo verifica `scripts/validate_skills.py`).

## 1. ¿Skill, o no?

Crea una skill cuando hay un **trabajo repetible** que un agente debe hacer siempre igual
y que necesita conocimiento que el modelo no tiene: estructura y convenciones propias,
plantillas probadas, scripts deterministas, decisiones ya tomadas.

No es una skill: una preferencia de un solo proyecto (va en el `CLAUDE.md` de ese
proyecto), algo que el modelo ya hace bien sin ayuda, o documentación que nadie ejecuta.

Una skill = una responsabilidad. Si la descripción necesita "y además…", probablemente
son dos skills.

## 2. Anatomía

```
skills/<nombre>/
  SKILL.md          obligatorio — frontmatter + instrucciones para el agente
  README.md         obligatorio — para humanos (español)
  CHANGELOG.md      obligatorio — Keep a Changelog + SemVer
  references/       opcional — documentación que el agente carga bajo demanda
  scripts/          opcional — código que el agente ejecuta (no lee)
  assets/           opcional — plantillas, ejemplos, datos
```

- El nombre de la carpeta es el `name` de la skill.
- Nada de dotfiles dentro de la skill (guárdalos sin punto, p. ej. `gitignore`, y que un
  script los restaure), ni archivos `metadata.json`, ni `__pycache__/`: los instaladores
  los omiten.
- Las plantillas de `assets/` son **código real y probado**, con placeholders
  `{{MAYUSCULAS_CON_GUION_BAJO}}` que un script reemplaza.

## 3. Frontmatter

```yaml
---
name: mi-skill
description: >-
  Does X for Y with Z. Use when the user asks to …, mentions …, or wants to … .
license: MIT
compatibility: Needs … (solo si hay requisitos de entorno)
metadata:
  version: "1.0.0"
  summary: "Una línea en español para el catálogo y el listado del plugin."
  category: "development"
  tags: "tag1,tag2"
---
```

| Campo | Regla |
| --- | --- |
| `name` | 1–64 caracteres, `a-z 0-9` y guiones simples; igual a la carpeta; sin "claude" ni "anthropic" |
| `description` | 1–1024 caracteres, sin etiquetas XML. **Qué hace y cuándo usarla**, en tercera persona, con las frases y palabras clave que deberían activarla (en inglés y en español si los usuarios hablan español) |
| `license` | SPDX (`MIT`) |
| `compatibility` | ≤ 500 caracteres; solo si hay requisitos reales (herramientas, versiones, red) |
| `metadata.version` | SemVer `X.Y.Z` |
| `metadata.summary` | una línea (≤ 160) — alimenta el catálogo y el marketplace |
| `metadata.category` | `development`, `productivity`, `documentation`, `data`, `operations`, `design` |
| `metadata.tags` | separados por comas |

El frontmatter usa un subconjunto simple de YAML (escalares, bloques `>-`, un mapa en
`metadata`); `scripts/skills_lib.py` documenta qué se admite. Claves propias de Claude
Code (`allowed-tools`, `disable-model-invocation`, `argument-hint`…) se aceptan cuando
hacen falta.

**La descripción es lo único que el agente ve antes de decidir usar la skill.** Una
descripción vaga hace que nunca se active; una demasiado amplia, que se active donde no
debe. Pruébala con peticiones reales (sección 8).

## 4. Cuerpo de `SKILL.md`

- **≤ 500 líneas** (mejor ≤ 350). Todo lo que cuesta tokens en cada uso debe ganarse su
  lugar: el modelo ya es capaz; escribe solo lo que no puede inferir.
- Imperativo y concreto: comandos exactos, rutas exactas, resultado esperado.
- Estructura recomendada:
  1. Propósito en 2–3 frases.
  2. **Reglas** (lo que siempre / nunca) y qué decide la skill vs. qué se pregunta.
  3. **Workflow** con checklist copiable y fases que terminan en verificación.
  4. Mapa de referencias: qué archivo leer y **cuándo**.
  5. Scripts disponibles.
  6. Errores comunes.
- Grados de libertad: sé estricto donde un error es caro (migraciones, seguridad,
  comandos destructivos) y deja criterio donde hay varias respuestas buenas.
- Terminología consistente; nada sensible al tiempo ("a partir de mayo…"); sin nombres
  de clientes ni proyectos reales; sin secretos.
- Referencia los recursos con rutas relativas a la skill (`scripts/x.py`,
  `references/y.md`). En Claude Code `${CLAUDE_SKILL_DIR}` es la carpeta de la skill.

## 5. Divulgación progresiva

El agente carga: metadatos (siempre) → `SKILL.md` (al activarse) → recursos (cuando los
necesita). Por eso:

- Mueve el detalle a `references/`, un archivo por tema, enlazado **directamente** desde
  `SKILL.md` (un solo nivel; nada de referencias que remiten a otras referencias).
- Los archivos de más de ~100 líneas empiezan con una tabla de contenidos.
- Prefiere un script que se ejecuta a un bloque de código que el agente tiene que
  reescribir: ahorra contexto y elimina variaciones.

## 6. Scripts

- Python de biblioteca estándar (o Bash/Node si la skill ya los exige), con `--help`,
  docstring de uso y errores que digan qué hacer.
- Deterministas e idempotentes cuando tenga sentido; sin efectos fuera de lo que
  reciben por argumentos.
- Nada de rutas absolutas ni de dependencias del entorno de quien la escribió.

## 7. Idioma y neutralidad

- `SKILL.md` y `references/`: inglés (instrucciones precisas para el agente; el agente
  responde en el idioma del usuario).
- `README.md` y `CHANGELOG.md` de cada skill, y la documentación del repo: español.
- Código generado: identificadores, comentarios y mensajes técnicos en inglés; textos de
  interfaz en el idioma del usuario final.
- Una skill no toma decisiones que no le corresponden (diseño visual, proveedores,
  nombres del producto): las pregunta o las deja abiertas explícitamente.

## 8. Pruebas

1. `python scripts/validate_skills.py` — sin errores.
2. Pruebas automáticas en `tests/<nombre_skill>/` (unittest, biblioteca estándar) para los
   scripts y las plantillas. Si la skill genera proyectos, una prueba de integración en
   CI que los genere y los compile/pruebe.
3. **Evaluación con peticiones reales**: en una sesión nueva, con la skill instalada,
   prueba 3 peticiones que deberían activarla y 2 que no; revisa que se active cuando
   debe, que siga el workflow y que el resultado pase sus propias verificaciones. Ajusta
   la descripción o las instrucciones según lo observado.

## 9. Versiones y publicación

- SemVer por skill: `patch` (correcciones, redacción), `minor` (capacidades nuevas
  compatibles), `major` (cambia lo que genera o lo que espera).
- `python scripts/bump_version.py <skill> patch|minor|major` actualiza la versión, abre la
  entrada del CHANGELOG y sincroniza el catálogo.
- Etiqueta la publicación: `git tag <skill>@X.Y.Z`.
- Nunca edites a mano `.claude-plugin/marketplace.json` ni la tabla del README:
  `python scripts/sync_catalog.py`.

## 10. Checklist antes del pull request

- [ ] `name` = carpeta; descripción con qué + cuándo + palabras clave.
- [ ] `SKILL.md` ≤ 500 líneas, sin TODO, enlaces válidos, referencias a un nivel.
- [ ] README y CHANGELOG actualizados; versión subida si cambió el comportamiento.
- [ ] Plantillas probadas; scripts con `--help`.
- [ ] `python scripts/validate_skills.py` y `python -m unittest discover -s tests` en verde.
- [ ] Probada con peticiones reales en una sesión nueva.
- [ ] Sin nombres de clientes/proyectos, sin secretos, sin decisiones de diseño impuestas.
