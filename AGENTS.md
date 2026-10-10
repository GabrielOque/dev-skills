# Instrucciones para agentes — repositorio dev-skills

Este repositorio publica **Agent Skills**. Cada skill es una carpeta en `skills/<nombre>/`
y se distribuye como un plugin independiente del marketplace
`.claude-plugin/marketplace.json`. El estándar completo está en
[`docs/AUTHORING.md`](docs/AUTHORING.md): léelo antes de crear o modificar una skill.

## Cuando el usuario pide una skill nueva

1. **Entiende el trabajo antes de escribir.** Pregunta en un solo mensaje lo que falte:
   qué tarea debe resolver, para quién, qué debe decidir la skill y qué debe preguntar,
   qué entradas recibe y qué entrega, ejemplos reales de cómo la pedirían, y si hay
   proyectos o documentos de referencia (que se usan para extraer prácticas, **nunca**
   para copiar nombres, marcas o decisiones de diseño).
2. **Propón el diseño** en pocas líneas: nombre (kebab-case, verbo o resultado:
   `scaffold-…`, `review-…`, `setup-…`), resumen, descripción (qué + cuándo + frases que
   la activan), workflow por fases y qué irá en `references/`, `scripts/` y `assets/`.
   Espera confirmación.
3. **Genera la carpeta**:
   `python scripts/new_skill.py <nombre> --summary "…" --description "…" --category … --tags "…"`
4. **Escribe la skill** siguiendo `docs/AUTHORING.md`: `SKILL.md` conciso (≤ 500 líneas)
   con reglas, workflow verificable y mapa de referencias; el detalle en `references/`;
   lo repetible y determinista en `scripts/`; plantillas probadas en `assets/`.
5. **Prueba lo que generes**: ejecuta los scripts, genera algo real con las plantillas en
   un directorio temporal y verifica que funciona. Agrega pruebas en
   `tests/<nombre_con_guiones_bajos>/` y, si la skill genera proyectos, un workflow de
   integración en `.github/workflows/`.
6. **Valida y sincroniza**:
   `python scripts/sync_catalog.py && python scripts/validate_skills.py && python -m unittest discover -s tests`
7. Resume al usuario qué se creó, cómo probarla y qué quedó abierto. Haz commit o push
   solo si lo pide.

## Cuando el usuario pide cambiar una skill existente

- Lee su `SKILL.md`, sus referencias y su `CHANGELOG.md` antes de tocar nada.
- Cambia lo mínimo; mantén plantillas, referencias y `SKILL.md` coherentes entre sí.
- Documenta el cambio en `## [Unreleased]` del CHANGELOG y sube la versión con
  `python scripts/bump_version.py <skill> patch|minor|major`.
- Vuelve a correr las pruebas de la skill (y su integración si aplica).

## Reglas del repositorio

- El frontmatter de `SKILL.md` es la fuente de verdad: `marketplace.json` y el catálogo
  del README se regeneran con `python scripts/sync_catalog.py`; no se editan a mano.
- Nada de nombres de clientes o proyectos reales, secretos ni rutas de una máquina en
  particular dentro de una skill.
- Dentro de `skills/` no van dotfiles, `metadata.json` ni `__pycache__/`.
- Herramientas del repo en Python de biblioteca estándar, compatibles con Python 3.10+.
- `SKILL.md` y `references/` en inglés; README, CHANGELOG y documentación del repo en
  español.

## Comandos

```bash
python scripts/new_skill.py <nombre> --summary "…" --description "…"   # crear
python scripts/validate_skills.py [<nombre>]                           # validar
python scripts/sync_catalog.py [--check]                               # marketplace + catálogo
python scripts/bump_version.py <nombre> patch|minor|major              # versionar
python -m unittest discover -s tests                                   # pruebas
claude plugin validate .                                               # validador de Claude Code
```
