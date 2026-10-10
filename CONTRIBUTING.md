# Contribuir

1. Lee [`docs/AUTHORING.md`](docs/AUTHORING.md): es el estándar que cumple cada skill.
2. Crea una rama: `skill/<nombre>` para una skill nueva, `fix/<nombre>-…` o
   `feat/<nombre>-…` para cambios.
3. Skill nueva: `python scripts/new_skill.py <nombre> --summary "…" --description "…"`.
   Cambio a una existente: anótalo en `## [Unreleased]` de su `CHANGELOG.md` y sube la
   versión con `python scripts/bump_version.py <nombre> patch|minor|major`.
4. Antes de abrir el pull request:

   ```bash
   python scripts/sync_catalog.py
   python scripts/validate_skills.py
   python -m unittest discover -s tests
   ```

5. Abre el pull request contra `main` con la plantilla completa. CI debe quedar en verde.
6. Tras el merge, etiqueta la versión: `git tag <nombre>@X.Y.Z && git push --tags`.

Mensajes de commit en estilo [Conventional Commits](https://www.conventionalcommits.org/es/):
`feat(<skill>): …`, `fix(<skill>): …`, `docs: …`, `chore(repo): …`.
