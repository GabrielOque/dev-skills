## Qué cambia

<!-- Skill(s) afectada(s) y resumen del cambio. -->

## Tipo

- [ ] Skill nueva
- [ ] Cambio en una skill (versión subida con `scripts/bump_version.py`)
- [ ] Herramientas / documentación del repo

## Checklist

- [ ] `python scripts/validate_skills.py` sin errores
- [ ] `python scripts/sync_catalog.py --check` en sync
- [ ] `python -m unittest discover -s tests` en verde
- [ ] CHANGELOG de la skill actualizado
- [ ] Probada con peticiones reales en una sesión nueva (se activa cuando debe y no cuando no)
- [ ] Sin nombres de clientes/proyectos, secretos ni decisiones de diseño impuestas
