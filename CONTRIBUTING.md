# Contribuir

## Reglas de ramas y merge

- `main` esta protegida y solo acepta merges desde `develop` mediante Pull Requests.
- No se permiten pushes directos a `main`.
- Todos los cambios deben seguir este orden de merge:
  - `feat/*` -> `develop`
  - `fix/*` -> `develop`
  - `develop` -> `main`

## Requisitos de Pull Request

- El PR debe tener como destino `main` solo si la rama de origen es `develop`.
- El workflow `check-source-branch` debe pasar antes del merge.
- Mantener `develop` actualizada con `main` antes de abrir un PR hacia `main`.

## Flujo sugerido

1. Crear una rama de feature desde `develop`.
2. Abrir un PR hacia `develop`.
3. Luego de aprobar y hacer merge en `develop`, abrir un PR desde `develop` hacia `main`.

## Notas

- Si se crea un PR hacia `main` desde cualquier rama distinta de `develop`, el check de CI fallara.
- Si necesitas una excepcion, solicita ayuda a un administrador del repositorio.
