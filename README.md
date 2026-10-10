# dev-skills

Repositorio de **Agent Skills** de ingeniería: paquetes de instrucciones, referencias,
plantillas y scripts que enseñan a un agente (Claude Code y cualquier cliente compatible
con el estándar [Agent Skills](https://agentskills.io)) a hacer un trabajo concreto con
nuestros estándares.

Cada skill vive en su propia carpeta bajo [`skills/`](skills/), se versiona por separado
y se instala de forma independiente.

## Catálogo

<!-- skills-catalog:start -->
| Skill | Versión | Categoría | Qué hace |
| --- | --- | --- | --- |
| [`initial-setup-pdn-stack`](skills/initial-setup-pdn-stack/) | 1.0.0 | development | Monta back (Django + DRF + PostgreSQL) y front (Next.js) con auth JWT, roles/permisos propios y estructura lista para crecer por módulos. |
<!-- skills-catalog:end -->

> El catálogo y [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) se
> generan desde el frontmatter de cada `SKILL.md` con `python scripts/sync_catalog.py`.

## Instalación

Reemplaza `TU-USUARIO` por el usuario u organización de GitHub donde vive este repo.

### Claude Code — marketplace de plugins (recomendado)

```text
/plugin marketplace add TU-USUARIO/dev-skills
/plugin install initial-setup-pdn-stack@dev-skills
```

O desde la terminal:

```bash
claude plugin marketplace add TU-USUARIO/dev-skills
claude plugin install initial-setup-pdn-stack@dev-skills
```

Cada skill es un plugin propio: instala solo las que necesites. Para recibir versiones
nuevas: `/plugin marketplace update dev-skills`. Si el repo es privado, Claude Code usa
tus credenciales de git (`gh auth login` o SSH).

### Cualquier agente compatible — CLI `skills`

```bash
npx skills add TU-USUARIO/dev-skills --skill initial-setup-pdn-stack -a claude-code      # en el proyecto
npx skills add TU-USUARIO/dev-skills --skill initial-setup-pdn-stack -a claude-code -g   # global
```

### Manual

```bash
git clone https://github.com/TU-USUARIO/dev-skills.git
cp -r dev-skills/skills/initial-setup-pdn-stack ~/.claude/skills/        # personal
cp -r dev-skills/skills/initial-setup-pdn-stack <proyecto>/.claude/skills/  # solo un proyecto
```

### Uso

Una vez instalada, Claude la activa sola cuando tu petición encaja con su descripción
("monta un proyecto nuevo con Django y Next.js…"), o puedes invocarla explícitamente:
`/initial-setup-pdn-stack` (instalación manual) o
`/initial-setup-pdn-stack:initial-setup-pdn-stack` (instalada como plugin).

## Estructura del repositorio

```
.claude-plugin/marketplace.json   marketplace de Claude Code (generado: un plugin por skill)
skills/<nombre>/                  una skill = una carpeta
  SKILL.md                        frontmatter + instrucciones para el agente (≤ 500 líneas)
  README.md                       documentación para humanos
  CHANGELOG.md                    historial de versiones de la skill
  references/                     documentación cargada bajo demanda (opcional)
  scripts/                        utilidades ejecutables (opcional)
  assets/                         plantillas y recursos (opcional)
template/                         plantilla base para skills nuevas
scripts/                          herramientas del repo: crear, validar, sincronizar, versionar
tests/                            pruebas de las herramientas y de las plantillas de cada skill
docs/AUTHORING.md                 estándar de autoría de skills
AGENTS.md                         instrucciones para agentes que trabajen en este repo
```

## Crear una skill nueva

Con Claude Code abierto en este repo basta con pedirlo:

> "Créame una skill que …"

Claude sigue [`AGENTS.md`](AGENTS.md) y [`docs/AUTHORING.md`](docs/AUTHORING.md): te
pregunta lo necesario, genera la carpeta con `scripts/new_skill.py`, escribe la skill,
la valida y la deja registrada en el catálogo. A mano:

```bash
python scripts/new_skill.py mi-skill \
  --summary "Una línea: qué hace" \
  --description "What it does and when to use it, with the phrases that should trigger it" \
  --category development --tags "tag1,tag2"
# completa SKILL.md / README.md, agrega references/ scripts/ assets/ si hacen falta
python scripts/validate_skills.py
```

## Validación y CI

```bash
python scripts/validate_skills.py      # spec Agent Skills + convenciones del repo
python scripts/sync_catalog.py --check # marketplace y catálogo al día
python -m unittest discover -s tests   # herramientas y plantillas
claude plugin validate .               # (opcional) validador oficial de Claude Code
```

GitHub Actions ejecuta lo mismo en cada push y pull request; las skills con plantillas
tienen además su prueba de integración (por ejemplo, `initial-setup-pdn-stack` genera los
dos proyectos, corre migraciones y tests contra PostgreSQL y compila el frontend).

## Versionado

Cada skill sigue SemVer en `metadata.version` y documenta los cambios en su
`CHANGELOG.md`:

```bash
python scripts/bump_version.py initial-setup-pdn-stack minor
git tag initial-setup-pdn-stack@1.1.0 && git push --tags
```

## Licencia

[MIT](LICENSE).
