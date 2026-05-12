# PROMPT — `crm-interactions-service`

## Contexto general del proyecto

Eres el **microservicio de historial de interacciones** de un CRM empresarial en migración a AWS. Este servicio es el núcleo del módulo de gestión de clientes: permite registrar, consultar y analizar todas las interacciones entre los agentes del CRM y los clientes a lo largo del tiempo. Una interacción puede ser una llamada, un email, una reunión, un ticket de soporte o una nota interna.

Todas las peticiones provienen del API Gateway, que inyecta headers internos (`X-User-Id`, `X-User-Role`, `X-Request-Id`). **Este servicio nunca valida JWT.**

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Framework | FastAPI |
| Lenguaje | Python |
| ORM | SQLAlchemy 2.0 async |
| Driver PostgreSQL | asyncpg |
| Migraciones | Alembic |
| Base de datos | PostgreSQL 15 (Docker local → AWS RDS en producción) |
| Validación | Pydantic v2 |
| Documentación | FastAPI nativo (Swagger UI + ReDoc) |
| Testing | pytest + pytest-asyncio + httpx AsyncClient |
| Containerización | Docker + docker-compose |
| Variables de entorno | pydantic-settings (BaseSettings) |

---

## Arquitectura: Hexagonal (Ports & Adapters)

```
src/
├── domain/                              # DOMINIO PURO — cero imports de frameworks
│   ├── entities/
│   │   └── interaction.py               # @dataclass Interaction
│   ├── value_objects/
│   │   ├── interaction_type.py          # Enum: call, email, meeting, ticket, note
│   │   ├── channel.py                   # Enum: phone, email, whatsapp, in_person, platform
│   │   └── interaction_status.py        # Enum: pending, in_progress, resolved, closed
│   ├── repositories/
│   │   └── interaction_repository.py    # ABC InteractionRepository
│   └── exceptions.py                    # InteractionNotFoundError, ClientNotFoundError
│
├── application/
│   ├── use_cases/
│   │   ├── get_interaction.py           # Obtener por ID
│   │   ├── list_interactions.py         # Historial con filtros y paginación
│   │   ├── list_by_client.py            # Historial completo de un cliente
│   │   ├── create_interaction.py        # Registrar nueva interacción
│   │   ├── update_interaction.py        # Editar interacción existente
│   │   └── close_interaction.py         # Marcar como cerrada/resuelta
│   └── dtos/
│       └── interaction_dto.py           # CreateInteractionDTO, UpdateInteractionDTO, InteractionResponseDTO
│
├── adapters/
│   ├── inbound/
│   │   └── http/
│   │       ├── routers/
│   │       │   └── interaction_router.py
│   │       ├── schemas/
│   │       │   └── interaction_schema.py
│   │       └── dependencies.py          # Extrae contexto de headers internos
│   │
│   └── outbound/
│       └── persistence/
│           ├── models/
│           │   └── interaction_model.py  # SQLAlchemy ORM Model
│           └── interaction_pg_repository.py # Implementa InteractionRepository ABC
│
└── infrastructure/
    ├── database/
    │   ├── connection.py
    │   └── migrations/
    ├── logging/
    │   └── setup.py
    └── di/
        └── container.py
```

---

## Modelo de base de datos

### Tabla `interactions`

```sql
CREATE TABLE interactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Quién y con quién
    client_id       UUID NOT NULL,          -- ID del cliente (viene del users-service)
    agent_id        UUID NOT NULL,          -- ID del agente que registra (X-User-Id del Gateway)

    -- Tipo y canal
    type            VARCHAR(20) NOT NULL
                    CHECK (type IN ('call','email','meeting','ticket','note')),
    channel         VARCHAR(20) NOT NULL
                    CHECK (channel IN ('phone','email','whatsapp','in_person','platform')),

    -- Estado del seguimiento
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','in_progress','resolved','closed')),

    -- Contenido
    subject         VARCHAR(500) NOT NULL,  -- Asunto o título de la interacción
    notes           TEXT,                   -- Descripción detallada / cuerpo
    outcome         VARCHAR(255),           -- Resultado: "Cotización enviada", "Ticket resuelto"

    -- Fechas
    interaction_date TIMESTAMPTZ NOT NULL,  -- Cuándo ocurrió la interacción (puede ser pasado)
    follow_up_date   TIMESTAMPTZ,           -- Fecha de próximo seguimiento programado
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Metadatos
    duration_minutes INTEGER,              -- Duración (útil para llamadas/reuniones)
    tags             TEXT[],               -- Etiquetas: ["urgente", "propuesta", "renovacion"]
    is_deleted       BOOLEAN NOT NULL DEFAULT FALSE  -- Soft delete
);

-- Índices de performance (críticos para CRM con alto volumen)
CREATE INDEX idx_interactions_client_id ON interactions(client_id);
CREATE INDEX idx_interactions_agent_id ON interactions(agent_id);
CREATE INDEX idx_interactions_type ON interactions(type);
CREATE INDEX idx_interactions_status ON interactions(status);
CREATE INDEX idx_interactions_date ON interactions(interaction_date DESC);
CREATE INDEX idx_interactions_client_date ON interactions(client_id, interaction_date DESC);
CREATE INDEX idx_interactions_follow_up ON interactions(follow_up_date) WHERE follow_up_date IS NOT NULL;
```

---

## Endpoints a implementar

### Interacciones `/api/v1/interactions`

| Método | Ruta | Descripción | Roles |
|--------|------|-------------|-------|
| GET | `/api/v1/interactions/` | Listar interacciones con filtros y paginación | Todos |
| POST | `/api/v1/interactions/` | Crear nueva interacción | admin, soporte |
| GET | `/api/v1/interactions/{id}` | Obtener interacción por ID | Todos |
| PUT | `/api/v1/interactions/{id}` | Actualizar interacción | admin, soporte |
| DELETE | `/api/v1/interactions/{id}` | Soft delete | admin |
| PATCH | `/api/v1/interactions/{id}/close` | Marcar como resuelta/cerrada | admin, soporte |

### Historial por cliente

| Método | Ruta | Descripción | Roles |
|--------|------|-------------|-------|
| GET | `/api/v1/interactions/client/{client_id}` | Historial completo de un cliente ordenado por fecha | Todos |
| GET | `/api/v1/interactions/client/{client_id}/summary` | Resumen: total por tipo, última interacción, próximo follow-up | Todos |

### Follow-ups

| Método | Ruta | Descripción | Roles |
|--------|------|-------------|-------|
| GET | `/api/v1/interactions/follow-ups/pending` | Follow-ups pendientes del agente autenticado | Todos |
| GET | `/api/v1/interactions/follow-ups/overdue` | Follow-ups vencidos (fecha_follow_up < hoy) | admin, soporte |

### Health

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health/` | Estado del servicio y conexión a DB |

---

## Filtros disponibles en `GET /interactions/`

```
?client_id=uuid
?agent_id=uuid
?type=call|email|meeting|ticket|note
?channel=phone|email|whatsapp|in_person|platform
?status=pending|in_progress|resolved|closed
?date_from=2024-01-01
?date_to=2024-12-31
?tags=urgente,propuesta       (AND entre tags)
?page=1
?page_size=20
?order_by=interaction_date    (default: DESC)
```

---

## Schemas Pydantic clave

### Request — Crear interacción

```python
class CreateInteractionSchema(BaseModel):
    client_id:          UUID
    type:               InteractionType
    channel:            Channel
    subject:            str = Field(..., min_length=3, max_length=500)
    notes:              Optional[str] = None
    outcome:            Optional[str] = Field(None, max_length=255)
    interaction_date:   datetime
    follow_up_date:     Optional[datetime] = None
    duration_minutes:   Optional[int] = Field(None, ge=1, le=600)
    tags:               Optional[list[str]] = []
```

### Response — Interacción

```python
class InteractionResponseSchema(BaseModel):
    id:               UUID
    client_id:        UUID
    agent_id:         UUID
    type:             InteractionType
    channel:          Channel
    status:           InteractionStatus
    subject:          str
    notes:            Optional[str]
    outcome:          Optional[str]
    interaction_date: datetime
    follow_up_date:   Optional[datetime]
    duration_minutes: Optional[int]
    tags:             list[str]
    created_at:       datetime
    updated_at:       datetime
```

### Response — Resumen de cliente

```python
class ClientInteractionSummarySchema(BaseModel):
    client_id:              UUID
    total_interactions:     int
    by_type:                dict[str, int]   # {"call": 5, "email": 3, ...}
    by_status:              dict[str, int]
    last_interaction_date:  Optional[datetime]
    next_follow_up_date:    Optional[datetime]
    open_tickets:           int
```

---

## Contrato de respuestas HTTP

```json
// Lista paginada
{
  "success": true,
  "data": {
    "items": [...],
    "total": 120,
    "page": 1,
    "page_size": 20,
    "pages": 6
  }
}

// Objeto único
{
  "success": true,
  "data": { ... }
}

// Error
{
  "success": false,
  "error": {
    "code": "INTERACTION_NOT_FOUND",
    "message": "No existe una interacción con ese ID"
  }
}
```

---

## Configuración

### `.env.example`

```env
DB_NAME=crm_interactions_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

APP_ENV=local
APP_PORT=8002
LOG_LEVEL=INFO
```

---

## Conexión a base de datos

Usar el mismo patrón que `users-service`:

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,       # Obligatorio para AWS RDS
    pool_recycle=3600,
    echo=settings.app_env == "local",
)
```

---

## Docker

### `docker-compose.yml`

```yaml
version: "3.9"
services:
  interactions-service:
    build: .
    ports:
      - "8002:8002"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: crm_interactions_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5434:5432"          # Puerto distinto para no colisionar con otros servicios
    volumes:
      - interactions_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  interactions_postgres_data:
```

---

## Documentación (Swagger)

```python
app = FastAPI(
    title="CRM Interactions Service",
    description="""
    Microservicio de historial de interacciones del CRM.

    Permite registrar y consultar todas las interacciones entre agentes y clientes:
    llamadas, emails, reuniones, tickets de soporte y notas internas.

    **Nota:** Este servicio solo acepta tráfico desde el API Gateway. No exponer directamente.
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
```

---

## Testing

### Estructura

```
tests/
├── conftest.py
│     # fixtures: DB test, cliente_id de prueba, agent_id de prueba,
│     # interacciones de distintos tipos, headers internos simulados
├── unit/
│   ├── test_create_interaction.py
│   ├── test_list_interactions.py       # Filtros, paginación, orden
│   ├── test_client_summary.py          # Cálculo de resumen
│   └── test_follow_ups.py              # Pendientes y vencidos
└── integration/
    ├── test_interaction_crud.py
    ├── test_client_history.py
    └── test_follow_up_endpoints.py
```

### Casos de prueba obligatorios

**CRUD básico:**
- ✅ Crear interacción con todos los campos → 201, retorna objeto completo
- ✅ Crear interacción mínima (sin notas, sin follow-up) → 201
- ❌ Crear sin `client_id` → 422
- ❌ Crear con `type` inválido → 422
- ✅ Obtener por ID existente → 200
- ❌ Obtener ID inexistente → 404
- ✅ Actualizar subject y notes → 200
- ✅ Soft delete → `is_deleted=True`, no aparece en listados
- ✅ Close interaction → status=closed, sin poder reabrirse

**Filtros y paginación:**
- ✅ Filtrar por `client_id` → solo interacciones de ese cliente
- ✅ Filtrar por `type=call` → solo llamadas
- ✅ Filtrar por rango de fechas `date_from` / `date_to`
- ✅ Paginación correcta: `total`, `pages`, `page_size`
- ✅ Orden descendente por `interaction_date` por defecto

**Historial y resumen:**
- ✅ GET `/client/{id}` → todas las interacciones ordenadas por fecha DESC
- ✅ GET `/client/{id}/summary` → totales correctos por tipo y estado
- ✅ `open_tickets` cuenta solo tickets `pending` o `in_progress`

**Follow-ups:**
- ✅ `follow-ups/pending` → interacciones con `follow_up_date` futuro del agente autenticado
- ✅ `follow-ups/overdue` → interacciones con `follow_up_date` pasado y status != closed

---

## Uso del rol en los microservicios

**Este servicio no autoriza — eso ya lo hizo el Gateway.** El rol (`X-User-Role`) se usa únicamente para **filtrar qué datos retorna cada endpoint**.

```python
# src/adapters/inbound/http/routers/interaction_router.py

@router.get("/")
async def list_interactions(
    context: UserContext = Depends(get_current_user_context),
    use_case: ListInteractions = Depends(get_list_interactions_use_case),
):
    if context.role == UserRole.COMERCIAL:
        # Comercial solo ve interacciones de sus propios clientes
        return await use_case.execute(filters={"agent_id": context.user_id})
    # Admin y Soporte ven todas
    return await use_case.execute()


@router.get("/client/{client_id}")
async def list_by_client(
    client_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    use_case: ListByClient = Depends(get_list_by_client_use_case),
):
    if context.role == UserRole.COMERCIAL:
        owned_client_ids = await _get_comercial_owned_client_ids(context, db)
        if client_id not in owned_client_ids:
            return empty_response()
        return await use_case.execute(client_id=client_id)
    return await use_case.execute(client_id=client_id)
```

> **Regla de visibilidad por rol:**
> - **Admin/Soporte:** ven todo.
> - **Comercial READ:** ve TODAS las interacciones de clientes donde tiene al menos una interacción propia ("clientes asignados"). Usa `get_owned_client_ids(agent_id)` para obtener la lista.
> - **Comercial WRITE:** solo puede editar/cerrar/subir adjuntos a interacciones donde `agent_id == user_id`.
> - **Follow-ups:** siempre propios (`agent_id == user_id`).
> - **Regla general:** autorización → Gateway. Filtrado de datos → microservicio.
---

## Paso a paso de implementación

1. **Setup inicial**
   - `pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic-settings pytest pytest-asyncio httpx structlog`
   - Crear estructura de carpetas

2. **Dominio**
   - Crear dataclass `Interaction` con todos los campos
   - Crear value objects: `InteractionType`, `Channel`, `InteractionStatus`
   - Definir ABC `InteractionRepository`
   - Definir excepciones: `InteractionNotFoundError`

3. **Base de datos**
   - Configurar `connection.py` con pool async
   - Crear `InteractionModel` SQLAlchemy con todos los índices
   - Inicializar y configurar Alembic para async
   - Generar migración inicial

4. **Casos de uso + DTOs**
   - Implementar los 6 casos de uso CRUD
   - Implementar `ListByClient` con ordenamiento
   - Implementar `GetClientSummary` con agregaciones
   - Implementar `ListFollowUps` con filtro por fecha

5. **Adaptador outbound**
   - Implementar `InteractionPgRepository`
   - Incluir queries con filtros dinámicos (construir WHERE dinámico con SQLAlchemy)

6. **Adaptador inbound**
   - Crear `interaction_router.py` con todos los endpoints
   - Crear schemas Pydantic con validaciones
   - Implementar `dependencies.py`

7. **Infraestructura**
   - `container.py` con inyección de dependencias
   - Logging estructurado

8. **Main + Swagger**
   - Configurar `main.py`
   - Documentar con descripciones en cada endpoint

9. **Tests**
   - `conftest.py` con DB de test y fixtures
   - Tests unitarios e integración

10. **Docker**
    - Dockerfile + docker-compose
    - Verificar con `docker-compose up`

---

## Notas arquitectónicas importantes

- **`client_id` es una referencia lógica**, no una FK a base de datos de otro servicio. Los microservicios no comparten DB. La integridad referencial se garantiza a nivel de aplicación en el Gateway.
- **Los índices son críticos** para un CRM. Un cliente puede tener cientos de interacciones. Siempre filtrar por `client_id` en queries de historial.
- **`is_deleted=True`** nunca aparece en listados públicos. Agregar filtro automático `WHERE is_deleted = FALSE` en el repositorio.
- **Los tags usan `TEXT[]`** de PostgreSQL (array nativo). SQLAlchemy soporta esto con `ARRAY(String)`.
- **El resumen de cliente debe calcularse con una sola query SQL** usando `GROUP BY` y `COUNT`, no iterando en Python.
- **Follow-ups:** usar `TIMESTAMPTZ` siempre, nunca `TIMESTAMP` sin zona horaria (crucial para CRM multiregión).
- **No exponer este servicio directamente a Internet.** Solo debe recibir tráfico desde el Gateway.

---

## Mapa completo de puertos Docker (referencia)

| Servicio | Puerto interno | Puerto externo Docker |
|---|---|---|
| crm-api-gateway | 8000 | 8000 |
| crm-users-service | 8001 | 8001 |
| crm-interactions-service | 8002 | 8002 |
| Gateway DB (PostgreSQL) | 5432 | 5432 |
| Users DB (PostgreSQL) | 5432 | 5433 |
| Interactions DB (PostgreSQL) | 5432 | 5434 |
