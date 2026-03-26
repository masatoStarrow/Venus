# CI/CD – Venus

## Resumen

Venus tiene tres pipelines de GitHub Actions:

| Pipeline | Trigger | Que hace |
|---|---|---|
| CI | PR o push a `develop`/`main` | pytest, Alembic migrate, Docker build |
| CD Develop | push a `develop` | build + push imagen GHCR, deploy remoto |
| CD Production | push a `main` | build + push imagen GHCR, deploy remoto |

## Imagen Docker

`python:3.13-slim` con `gunicorn` + `uvicorn.workers.UvicornWorker`.

El compose local sigue usando `uvicorn --reload` para desarrollo.

## Despliegue

El script `ops/deploy.sh` se encarga de:

1. Validar variables requeridas
2. Login al registry
3. Pull de la nueva imagen
4. Ejecutar migraciones Alembic
5. `docker compose up -d`
6. Health check
7. Rollback si falla

## Variables requeridas en GitHub Environments

| Variable | Descripcion |
|---|---|
| `SSH_HOST` | Host del servidor |
| `SSH_PORT` | Puerto SSH |
| `SSH_USER` | Usuario SSH |
| `SSH_PRIVATE_KEY` | Clave privada SSH |
| `REGISTRY_USERNAME` | Usuario GHCR |
| `REGISTRY_TOKEN` | Token GHCR |
| `DEPLOY_ENV_FILE` | Contenido del archivo .env del ambiente |

## Health check

`GET /api/v1/health/` debe retornar `200`.

## Nota sobre almacenamiento S3

Venus depende de configuracion S3 para adjuntos. Las variables relevantes son:

- `S3_BUCKET`
- `S3_REGION`
- `S3_ENDPOINT_URL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Estas deben ir en el `DEPLOY_ENV_FILE` del ambiente correspondiente.
