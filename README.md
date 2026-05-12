# CRM Interactions Service (Venus)

Microservicio de **gestión de interacciones** del CRM, construido con **FastAPI** y **arquitectura hexagonal**.

Gestiona llamadas, correos electrónicos, reuniones, tickets y notas asociadas a los clientes del sistema.

## Tecnologías

| Componente | Tecnología |
|---|---|
| Framework | FastAPI 0.135.1 |
| ORM | SQLAlchemy 2.0 (async) |
| Base de datos | PostgreSQL 15 |
| Migraciones | Alembic 1.18 |
| Validación | Pydantic v2 |
| Logging | structlog (JSON) |
| Tests | pytest + pytest-asyncio + SQLite |
| Contenedor | Docker + docker-compose |
| Almacenamiento | AWS S3 (adjuntos) |

## Arquitectura

```
src/
├── domain/          # Entidades, Value Objects, Puertos (ABC)
├── application/     # Casos de uso, DTOs
├── adapters/
│   ├── inbound/     # HTTP (routers, schemas, dependencias)
│   └── outbound/
│       ├── persistence/   # Repositorios, modelos SQLAlchemy
│       └── storage/       # S3 y almacenamiento en memoria (tests)
└── infrastructure/  # Base de datos, logging, inyección de dependencias
```

## Endpoints

| Método | Ruta | Descripción | Roles |
|--------|------|-------------|-------|
| `GET` | `/api/v1/interactions/` | Listar interacciones (filtros, paginación) | Todos* |
| `POST` | `/api/v1/interactions/` | Crear interacción | Admin, Soporte |
| `GET` | `/api/v1/interactions/metrics` | Métricas globales (incluye desglose por cliente) | Todos* |
| `GET` | `/api/v1/interactions/follow-ups/pending` | Seguimientos pendientes | Todos |
| `GET` | `/api/v1/interactions/follow-ups/overdue` | Seguimientos vencidos | Todos |
| `GET` | `/api/v1/interactions/client/{id}` | Historial de cliente | Todos* |
| `GET` | `/api/v1/interactions/client/{id}/summary` | Resumen de cliente | Todos* |
| `GET` | `/api/v1/interactions/{id}` | Detalle de interacción | Todos |
| `PUT` | `/api/v1/interactions/{id}` | Actualizar interacción | Admin, Soporte |
| `DELETE` | `/api/v1/interactions/{id}` | Eliminar (soft delete) | Admin |
| `PATCH` | `/api/v1/interactions/{id}/close` | Cerrar interacción | Admin, Soporte |
| `GET` | `/api/v1/interactions/{id}/audit` | Historial de cambios | Todos |
| `POST` | `/api/v1/interactions/{id}/attachments/` | Subir adjunto (multipart) | Todos |
| `GET` | `/api/v1/interactions/{id}/attachments/` | Listar adjuntos | Todos |
| `GET` | `/api/v1/interactions/{id}/attachments/{att_id}/download` | URL presignada de descarga | Todos |
| `DELETE` | `/api/v1/interactions/{id}/attachments/{att_id}` | Eliminar adjunto (S3 + BD) | Todos |
| `GET` | `/api/v1/health/` | Health check | Público |

> \* Comercial ve todas las interacciones de clientes donde tiene al menos una interacción propia ("clientes asignados"). Para escritura (editar, cerrar, subir/borrar adjuntos), comercial solo puede modificar sus propias interacciones. Follow-ups son siempre propios.

## Parámetros de Filtrado

```
GET /api/v1/interactions/?type=call,email&status=pending&channel=phone
    &date_from=2026-01-01T00:00:00Z&date_to=2026-12-31T23:59:59Z
    &order_by=interaction_date&order_dir=desc
    &page=1&page_size=20
```

## Respuestas Clave

### GET /metrics

```json
{
  "success": true,
  "data": {
    "total_clients": 5,
    "total_interactions": 42,
    "avg_interactions_per_client": 8.4,
    "per_client": [
      {
        "client_id": "uuid",
        "interaction_count": 12,
        "last_interaction_date": "2026-03-08T15:30:00Z"
      }
    ]
  }
}
```

### GET /client/{id}/summary

```json
{
  "success": true,
  "data": {
    "client_id": "uuid",
    "total_interactions": 12,
    "interactions_last_30_days": 3,
    "by_type": { "call": 5, "email": 4, "meeting": 2, "ticket": 1, "note": 0 },
    "by_status": { "pending": 1, "in_progress": 2, "resolved": 6, "closed": 3 },
    "completion_rate": 75.0,
    "last_interaction_date": "2026-03-08T15:30:00Z",
    "next_follow_up_date": "2026-03-15T10:00:00Z",
    "open_tickets": 1
  }
}
```

## Esquema de Base de Datos

### Tabla `interactions`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | UUID PK | Identificador único |
| client_id | UUID | ID del cliente |
| agent_id | UUID | ID del agente que registra |
| type | VARCHAR(20) | call, email, meeting, ticket, note |
| channel | VARCHAR(20) | phone, email, whatsapp, in_person, platform |
| status | VARCHAR(20) | pending, in_progress, resolved, closed |
| subject | VARCHAR(500) | Asunto |
| notes | TEXT | Notas visibles |
| internal_notes | TEXT | Notas internas |
| outcome | VARCHAR(255) | Resultado |
| interaction_date | TIMESTAMPTZ | Fecha de la interacción |
| follow_up_date | TIMESTAMPTZ | Fecha de seguimiento |
| duration_minutes | INTEGER | Duración en minutos |
| is_deleted | BOOLEAN | Soft delete |
| last_edited_by | UUID | Último editor |
| created_at | TIMESTAMPTZ | Fecha de creación |
| updated_at | TIMESTAMPTZ | Fecha de actualización |

### Tabla `interaction_audit`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | UUID PK | Identificador |
| interaction_id | UUID FK | Interacción auditada |
| edited_by | UUID | Quién editó |
| edited_at | TIMESTAMPTZ | Cuándo se editó |
| field_name | VARCHAR(50) | Campo modificado |
| previous_value | TEXT | Valor anterior |
| new_value | TEXT | Valor nuevo |

### Tabla `interaction_attachments`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | UUID PK | Identificador único |
| interaction_id | UUID FK | Interacción asociada (CASCADE) |
| uploaded_by | UUID | Quién subió el archivo |
| file_name | VARCHAR(255) | Nombre original del archivo |
| file_key | VARCHAR(500) | Key en S3 |
| content_type | VARCHAR(100) | Tipo MIME |
| file_size | INTEGER | Tamaño en bytes |
| context | VARCHAR(20) | `internal_note` o `note` |
| created_at | TIMESTAMPTZ | Fecha de subida |

## Desarrollo Local

### Requisitos

- Docker y Docker Compose
- Red Docker compartida: `docker network create crm_network`

### Iniciar

```bash
cd Venus
docker-compose up --build
```

El servicio estará disponible en `http://localhost:8002`.

- Swagger UI: `http://localhost:8002/api/docs`
- ReDoc: `http://localhost:8002/api/redoc`

### Migraciones

```bash
docker-compose exec interactions-service alembic upgrade head
```

### Tests

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar todos los tests
pytest -v

# Solo unitarios
pytest tests/unit/ -v

# Solo integración
pytest tests/integration/ -v
```

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DB_USER` | Usuario PostgreSQL | `postgres` |
| `DB_PASSWORD` | Contraseña | `postgres` |
| `DB_HOST` | Host de la BD | `db` |
| `DB_PORT` | Puerto de la BD | `5432` |
| `DB_NAME` | Nombre de la BD | `crm_interactions_db` |
| `APP_PORT` | Puerto del servicio | `8002` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `POOL_SIZE` | Pool de conexiones | `5` |
| `POOL_MAX_OVERFLOW` | Overflow del pool | `10` |
| `S3_BUCKET` | Bucket S3 para adjuntos | — |
| `S3_REGION` | Región AWS | `us-east-1` |
| `S3_ENDPOINT_URL` | Endpoint custom (LocalStack, MinIO) | — |
| `AWS_ACCESS_KEY_ID` | Credencial AWS | — |
| `AWS_SECRET_ACCESS_KEY` | Credencial AWS | — |
