# CI/CD – Venus

## Resumen

Venus tiene tres pipelines de GitHub Actions:

| Pipeline       | Trigger                      | Que hace                                                         |
| -------------- | ---------------------------- | ---------------------------------------------------------------- |
| CI             | PR o push a `develop`/`main` | pytest, Alembic migrate, Docker build                             |
| CD Develop     | push a `develop`             | build + push a Amazon ECR + redeploy del servicio ECS develop      |
| CD Production  | push a `main`                | build + push a Amazon ECR + redeploy del servicio ECS production   |

## Imagen Docker

`python:3.13-slim` con `uvicorn`.

El contenedor arranca con `entrypoint.sh`, que ejecuta `alembic upgrade head` y luego `uvicorn`.
El compose local sigue usando `uvicorn --reload` para desarrollo.

## Despliegue (AWS ECS Fargate)

El pipeline de CD se encarga de:

1. Validar el CI (pytest, Alembic migrate, Docker build).
2. Configurar credenciales AWS.
3. Login a Amazon ECR.
4. Build y push de la imagen al repositorio ECR (`crm-tic2/venus`) con tags:
   - `develop-<sha>` o `production-<sha>`
   - `develop-latest` o `production-latest`
   - `latest` (consumido por la task definition de ECS)
5. `aws ecs update-service --force-new-deployment` para que ECS levante una nueva task con la imagen recién subida (las migraciones Alembic se ejecutan dentro del contenedor por `entrypoint.sh`).
6. Espera con `aws ecs wait services-stable` para garantizar que el rollout completó.

## Secretos requeridos en GitHub Environments

Configurar en `Settings → Environments → develop` y `production`.

### Secrets

| Secret                  | Descripción                                                  |
| ----------------------- | ------------------------------------------------------------ |
| `AWS_ACCESS_KEY_ID`     | Access Key del usuario IAM o de la sesión de AWS Academy     |
| `AWS_SECRET_ACCESS_KEY` | Secret Key correspondiente                                   |
| `AWS_SESSION_TOKEN`     | Session Token (sólo en AWS Academy / credenciales temporales) |

### Variables (no sensibles)

| Variable          | Valor sugerido                                              |
| ----------------- | ----------------------------------------------------------- |
| `AWS_REGION`      | `us-east-1`                                                 |
| `ECR_REGISTRY`    | `<account-id>.dkr.ecr.us-east-1.amazonaws.com`              |
| `ECR_REPOSITORY`  | `crm-tic2/venus`                                            |
| `ECS_CLUSTER`     | `crm-tic2-cluster-develop` (o `crm-tic2-cluster-production`) |
| `ECS_SERVICE`     | `venus`                                                     |

> Tip: `ECR_REGISTRY` se obtiene con `terraform output ecr_repository_urls` (es la parte antes del nombre del repositorio).

## Health check

`GET /api/v1/health/` debe retornar `200`. ECS usa el target group del ALB para health checks.

## Nota sobre almacenamiento S3

Venus depende de configuración S3 para adjuntos. Las variables relevantes (`S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT_URL`) ya las inyecta la task definition de ECS por Terraform. La autenticación a S3 se realiza con el `LabRole` asociado a la task (no son necesarias `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` dentro del contenedor en AWS).
