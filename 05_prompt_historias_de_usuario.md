# HISTORIAS DE USUARIO — CRM Módulo de Historial de Interacciones

---

## Principios técnicos globales

Estas decisiones aplican a **todo el módulo** sin excepción:

| Decisión | Regla | Razón |
|---|---|---|
| Filtros | Siempre **backend** vía query params | Un cliente puede tener cientos de interacciones. Filtrar en JS no escala |
| Métricas y conteos | Siempre **backend** con SQL (`COUNT`, `AVG`, `GROUP BY`) | El frontend nunca suma listas traídas del servidor |
| Fechas relativas ("hace X tiempo") | **Frontend** con `date-fns` | Es solo formateo visual, no lógica de negocio |
| Agrupación visual por fecha en timeline | **Frontend** | Los datos llegan ordenados del backend, el frontend solo los agrupa visualmente |
| Paginación | Siempre **backend** | El response siempre incluye `total`, `page`, `page_size`, `pages` |
| Ordenamiento default | `interaction_date DESC` | Más reciente primero |
| Roles que pueden editar | Solo `admin` y `soporte` | `comercial` es solo lectura en interacciones |
| Auditoría de cambios | Tabla `interaction_audit` separada | Decisión de esquema pendiente — ver HU-11 |

---

## Mapa de endpoints del módulo

Resumen de todos los endpoints necesarios para cubrir las HUs. Los marcados con 🆕 son nuevos respecto al MD original.

### interactions-service

| Método | Ruta | HU relacionada |
|---|---|---|
| GET | `/api/v1/interactions/` | HU-02, HU-06, HU-10 |
| POST | `/api/v1/interactions/` | HU-09 |
| GET | `/api/v1/interactions/{id}` | HU-08, HU-12 |
| PUT | `/api/v1/interactions/{id}` | HU-11 |
| DELETE | `/api/v1/interactions/{id}` | — |
| PATCH | `/api/v1/interactions/{id}/close` | — |
| GET | `/api/v1/interactions/client/{client_id}` | HU-02, HU-07 |
| GET | `/api/v1/interactions/client/{client_id}/summary` 🆕 | HU-04, HU-05 |
| GET | `/api/v1/interactions/metrics` 🆕 | HU-01 |
| GET | `/api/v1/interactions/follow-ups/pending` | — |
| GET | `/api/v1/interactions/follow-ups/overdue` | — |

### users-service

| Método | Ruta | HU relacionada |
|---|---|---|
| GET | `/api/v1/users/agents` 🆕 | HU-10 (filtro por agente) |

---

## HU-01 — Métricas generales de cartera

**Como** usuario del CRM
**Quiero** visualizar métricas generales de clientes
**Para** entender rápidamente el estado de mi cartera

### Criterios de aceptación
- Tarjeta "Total de clientes"
- Tarjeta "Interacciones totales"
- Tarjeta "Promedio de interacciones por cliente"
- Formato numérico destacado
- Respetar diseño visual aprobado

### Decisión técnica
**Backend.** Endpoint dedicado en `interactions-service`. El frontend nunca trae todos los registros para contar — el backend hace un `COUNT` y `AVG` en SQL en milisegundos.

### Endpoint

```
GET /api/v1/interactions/metrics
Headers: X-User-Id, X-User-Role
```

**Query params opcionales:**
```
?agent_id=uuid    → si el rol es comercial, el gateway inyecta su propio ID automáticamente
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_clients":          120,
    "total_interactions":     843,
    "avg_interactions_per_client": 7.03
  }
}
```

**Implementación SQL (interactions-service):**
```sql
SELECT
  COUNT(DISTINCT client_id)                              AS total_clients,
  COUNT(*)                                               AS total_interactions,
  ROUND(COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT client_id), 0), 2) AS avg_interactions_per_client
FROM interactions
WHERE is_deleted = FALSE
  AND (agent_id = :agent_id OR :agent_id IS NULL);  -- filtro por rol comercial
```

### Frontend
- Componente: `MetricsBar` (organismo) → 3 tarjetas `MetricCard` (molécula)
- TanStack Query: `useQuery({ queryKey: ['interactions', 'metrics'] })`
- Revalidar cuando se crea una nueva interacción: `invalidateQueries(['interactions', 'metrics'])`

---

## HU-02 — Contador de interacciones encontradas + última interacción

**Como** usuario
**Quiero** ver cuántas interacciones tiene el historial y la última interacción
**Para** saber el volumen total mostrado

### Criterios de aceptación
- Texto "X interacciones encontradas"
- Columna "Última interacción" en formato relativo ("hace 2 días")
- Se actualiza al aplicar filtros
- Coincide con resultados visibles

### Decisión técnica
**Backend para el conteo.** El campo `total` ya viene en el response paginado de `GET /interactions/`. El frontend solo lo muestra. La fecha relativa ("hace 2 días") la formatea el **frontend** con `date-fns`.

### Endpoint

```
GET /api/v1/interactions/client/{client_id}
```

El response ya incluye `total` en la paginación:

```json
{
  "success": true,
  "data": {
    "items": [...],
    "total":     47,
    "page":       1,
    "page_size": 20,
    "pages":      3
  }
}
```

El texto "47 interacciones encontradas" se construye en frontend con `data.total`.

### Frontend
```typescript
// utils/format.utils.ts
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

export const toRelativeDate = (date: string) =>
  formatDistanceToNow(new Date(date), { addSuffix: true, locale: es })
// → "hace 2 días", "hace 3 horas"
```

---

## HU-03 — Interacciones de los últimos 30 días

**Como** usuario del CRM
**Quiero** ver cuántas interacciones hubo en los últimos 30 días
**Para** analizar actividad reciente de un cliente

### Criterios de aceptación
- Calculado dinámicamente
- Considera fecha actual - 30 días
- Se actualiza automáticamente

### Decisión técnica
**Backend.** El frontend calcula la fecha `hoy - 30 días` y la envía como query param. El backend filtra con SQL. No se trae toda la lista para contar en JS.

### Endpoint

```
GET /api/v1/interactions/client/{client_id}/summary
```

Este endpoint ya calcula el período internamente. Ver HU-04 para el response completo.

**Alternativamente**, si se necesita como lista:
```
GET /api/v1/interactions/client/{client_id}
  ?date_from={fecha_hace_30_dias}
  &date_to={fecha_hoy}
```

El frontend construye las fechas:
```typescript
// hooks/queries/useRecentInteractions.ts
const dateFrom = subDays(new Date(), 30).toISOString()
const dateTo   = new Date().toISOString()
```

### Frontend
- El conteo viene en `data.total` del response paginado
- TanStack Query revalida automáticamente cuando se crea una nueva interacción

---

## HU-04 — Total de interacciones del cliente

**Como** usuario del CRM
**Quiero** visualizar el total de interacciones del cliente
**Para** medir su nivel de actividad

### Criterios de aceptación
- Tarjeta "Total interacciones"
- Valor calculado dinámicamente
- Se actualiza tras crear nueva interacción

### Decisión técnica
**Backend.** Endpoint `/summary` del cliente calcula totales con SQL agregado.

### Endpoint 🆕

```
GET /api/v1/interactions/client/{client_id}/summary
Headers: X-User-Id, X-User-Role
```

**Response:**
```json
{
  "success": true,
  "data": {
    "client_id":                "uuid",
    "total_interactions":       47,
    "interactions_last_30_days": 8,
    "by_type": {
      "call":    12,
      "email":   15,
      "meeting":  8,
      "ticket":   7,
      "note":     5
    },
    "by_status": {
      "pending":     5,
      "in_progress": 3,
      "resolved":   28,
      "closed":     11
    },
    "completion_rate":        83.0,
    "last_interaction_date":  "2024-11-20T14:30:00Z",
    "next_follow_up_date":    "2024-12-01T09:00:00Z",
    "open_tickets":            2
  }
}
```

**Implementación SQL:**
```sql
SELECT
  COUNT(*)                                        AS total_interactions,
  COUNT(*) FILTER (
    WHERE interaction_date >= NOW() - INTERVAL '30 days'
  )                                               AS interactions_last_30_days,
  COUNT(*) FILTER (WHERE type = 'call')           AS type_call,
  COUNT(*) FILTER (WHERE type = 'email')          AS type_email,
  COUNT(*) FILTER (WHERE type = 'meeting')        AS type_meeting,
  COUNT(*) FILTER (WHERE type = 'ticket')         AS type_ticket,
  COUNT(*) FILTER (WHERE type = 'note')           AS type_note,
  COUNT(*) FILTER (
    WHERE status IN ('resolved', 'closed')
  ) * 100.0 / NULLIF(COUNT(*), 0)                AS completion_rate,
  MAX(interaction_date)                           AS last_interaction_date,
  MIN(follow_up_date) FILTER (
    WHERE follow_up_date > NOW()
    AND status NOT IN ('resolved','closed')
  )                                               AS next_follow_up_date,
  COUNT(*) FILTER (
    WHERE type = 'ticket'
    AND status IN ('pending','in_progress')
  )                                               AS open_tickets
FROM interactions
WHERE client_id = :client_id
  AND is_deleted = FALSE;
```

### Frontend
- TanStack Query: `useQuery({ queryKey: ['interactions', 'summary', clientId] })`
- `invalidateQueries` al crear o editar una interacción

---

## HU-05 — Tasa de interacciones completadas

**Como** usuario del CRM
**Quiero** ver la tasa de interacciones completadas
**Para** medir eficiencia de gestión

### Criterios de aceptación
- Calculada como porcentaje
- Considera estados `cerrado` / `resuelto` vs total
- Formato `%`
- Se actualiza automáticamente

### Decisión técnica
**Backend.** El campo `completion_rate` ya viene calculado en el endpoint `/summary` (HU-04). El frontend solo formatea el número.

### Endpoint
Mismo que HU-04: `GET /api/v1/interactions/client/{client_id}/summary`

El campo `completion_rate: 83.0` se muestra como `83%` en frontend:

```typescript
// utils/format.utils.ts
export const toPercent = (value: number) => `${Math.round(value)}%`
```

### Frontend
- Componente: tarjeta `MetricCard` con valor `83%`
- Mismo query que HU-04 — no hace una llamada extra

---

## HU-06 — Agrupación temporal del timeline

**Como** usuario
**Quiero** ver las interacciones agrupadas por fecha
**Para** entender la secuencia temporal

### Criterios de aceptación
- Fecha como separador visual entre grupos
- Ordenado de más reciente a más antiguo
- Fecha relativa ("hace 2 días")

### Decisión técnica
**Backend ordena, frontend agrupa visualmente.** El backend retorna la lista ordenada por `interaction_date DESC`. El frontend la agrupa por día para mostrar los separadores de fecha.

### Endpoint
```
GET /api/v1/interactions/client/{client_id}?order_by=interaction_date&order_dir=desc
```

### Frontend — lógica de agrupación
```typescript
// utils/timeline.utils.ts
import { format, isToday, isYesterday } from 'date-fns'
import { es } from 'date-fns/locale'
import type { Interaction } from '@types/interaction.types'

interface GroupedInteractions {
  dateLabel: string
  interactions: Interaction[]
}

export const groupByDate = (interactions: Interaction[]): GroupedInteractions[] => {
  const groups = new Map<string, Interaction[]>()

  interactions.forEach((interaction) => {
    const date = new Date(interaction.interaction_date)
    const key  = format(date, 'yyyy-MM-dd')

    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(interaction)
  })

  return Array.from(groups.entries()).map(([key, items]) => ({
    dateLabel: formatGroupLabel(new Date(key)),
    interactions: items,
  }))
}

const formatGroupLabel = (date: Date): string => {
  if (isToday(date))     return 'Hoy'
  if (isYesterday(date)) return 'Ayer'
  return format(date, "d 'de' MMMM yyyy", { locale: es })
}
```

---

## HU-07 — Card de interacción en el timeline

**Como** usuario
**Quiero** visualizar cada interacción en formato card
**Para** entender rápidamente su contenido

### Criterios de aceptación
- Tipo de interacción
- Estado (badge visual)
- Asunto
- Descripción
- Agente
- Fecha
- Duración
- Diferenciación visual de notas internas

### Decisión técnica
**Solo frontend.** Los datos ya vienen del endpoint de lista. La card es un componente de presentación puro.

### Datos que consume del API

```typescript
// types/interaction.types.ts
export interface Interaction {
  id:               string
  client_id:        string
  agent_id:         string
  type:             InteractionType    // 'call' | 'email' | 'meeting' | 'ticket' | 'note'
  channel:          Channel
  status:           InteractionStatus  // 'pending' | 'in_progress' | 'resolved' | 'closed'
  subject:          string
  notes:            string | null
  internal_notes:   string | null      // estilo diferenciado si tiene valor
  outcome:          string | null
  interaction_date: string             // ISO 8601
  duration_minutes: number | null
  tags:             string[]
  created_by:       string             // uuid del agente creador
  created_at:       string
  updated_at:       string
  last_edited_by:   string | null      // uuid del último editor — HU-12
}
```

### Frontend — componentes
```
InteractionCard (organismo)
├── InteractionTypeBadge (átomo)   → ícono + label del tipo
├── InteractionStatusBadge (átomo) → badge con color por estado
├── Text subject (átomo)           → título principal
├── Text notes (átomo)             → descripción
├── InternalNotesBlock (molécula)  → fondo diferenciado, solo si hay notas internas
├── AgentInfo (molécula)           → avatar + nombre del agente
└── InteractionMeta (molécula)     → fecha relativa + duración
```

**Colores de estado sugeridos (variables CSS):**
```css
--status-pending:     #ca8a04;  /* amarillo */
--status-in-progress: #2563eb;  /* azul */
--status-resolved:    #16a34a;  /* verde */
--status-closed:      #6b7280;  /* gris */
```

---

## HU-08 — Crear nueva interacción (modal)

**Como** usuario del CRM
**Quiero** registrar una nueva interacción mediante un modal
**Para** documentar la gestión realizada con el cliente

### Criterios de aceptación
- Modal "Nueva Interacción" con formulario completo
- Campos: tipo, estado, asunto, descripción, notas internas (opcional), adjuntos (opcional)
- Validaciones en frontend y backend
- Al guardar: actualiza el timeline y las métricas

### Decisión técnica
- Validación en **frontend** con Zod (UX inmediata)
- Validación en **backend** con serializers (fuente de verdad)
- Los adjuntos se guardan en **S3** (o local en desarrollo) — el campo guarda la URL

### Endpoint

```
POST /api/v1/interactions/
Headers: X-User-Id, X-User-Role
```

**Request body:**
```json
{
  "client_id":        "uuid",
  "type":             "call",
  "channel":          "phone",
  "status":           "pending",
  "subject":          "Seguimiento propuesta comercial",
  "notes":            "Se discutieron los términos del contrato...",
  "internal_notes":   "Cliente interesado, cerrar antes de fin de mes",
  "interaction_date": "2024-11-20T14:30:00Z",
  "follow_up_date":   "2024-12-01T09:00:00Z",
  "duration_minutes": 30,
  "tags":             ["propuesta", "urgente"]
}
```

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id":             "uuid-generado",
    "client_id":      "uuid",
    "agent_id":       "uuid-del-agente",
    "type":           "call",
    "status":         "pending",
    "subject":        "Seguimiento propuesta comercial",
    "created_at":     "2024-11-20T14:35:00Z"
  }
}
```

### Validación Zod (frontend)

```typescript
// organisms/InteractionModal/InteractionModal.schema.ts
import { z } from 'zod'

export const interactionSchema = z.object({
  type: z.enum(['call','email','message','meeting','note'], {
    required_error: 'Selecciona un tipo de interacción',
  }),
  status: z.enum(['pending','in_progress','resolved','closed'], {
    required_error: 'Selecciona un estado',
  }),
  subject: z
    .string()
    .min(1, 'El asunto es requerido')
    .max(200, 'Máximo 200 caracteres'),
  notes: z
    .string()
    .min(1, 'La descripción es requerida'),
  internal_notes: z.string().optional(),
  interaction_date: z.string().min(1, 'La fecha es requerida'),
  follow_up_date:   z.string().optional(),
  duration_minutes: z.number().min(1).max(600).optional(),
})

export type InteractionFormValues = z.infer<typeof interactionSchema>
```

### Frontend — TanStack Query mutation
```typescript
// hooks/mutations/useInteraction.mutation.ts
export const useCreateInteractionMutation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateInteractionDTO) => interactionService.create(data),
    onSuccess: (_, variables) => {
      // Invalidar todas las queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['interactions'] })
      queryClient.invalidateQueries({ queryKey: ['interactions', 'summary', variables.client_id] })
      queryClient.invalidateQueries({ queryKey: ['interactions', 'metrics'] })
    },
  })
}
```

### Roles permitidos
| Acción | Admin | Soporte | Comercial |
|---|---|---|---|
| Crear interacción | ✅ | ✅ | ❌ |

---

## HU-09 — Tipo de interacción en el formulario

**Como** usuario del CRM
**Quiero** seleccionar el tipo de interacción al crear un registro
**Para** clasificar correctamente la gestión

### Criterios de aceptación
- Dropdown obligatorio
- Opciones: Llamada, Correo, Mensaje, Reunión, Nota
- No permite guardar sin selección
- Se muestra correctamente en el timeline

### Decisión técnica
Las opciones son **estáticas** — no vienen del backend. Son un enum conocido. Se definen como constantes en el frontend.

```typescript
// constants/interaction.constants.ts
export const INTERACTION_TYPES = [
  { value: 'call',    label: 'Llamada'  },
  { value: 'email',   label: 'Correo'   },
  { value: 'message', label: 'Mensaje'  },
  { value: 'meeting', label: 'Reunión'  },
  { value: 'note',    label: 'Nota'     },
] as const

export const INTERACTION_STATUSES = [
  { value: 'pending',     label: 'Pendiente'    },
  { value: 'in_progress', label: 'En progreso'  },
  { value: 'resolved',    label: 'Resuelto'     },
  { value: 'closed',      label: 'Cerrado'      },
] as const
```

---

## HU-10 — Filtros en el timeline

**Como** usuario del CRM
**Quiero** filtrar las interacciones por diferentes criterios
**Para** analizar la gestión en periodos y variables específicas

### Criterios de aceptación
- Panel de filtros combinables
- Filtros: rango de fecha, tipo (múltiple), estado (múltiple), agente (múltiple)
- Limpiar filtros
- Actualiza timeline dinámicamente

### Decisión técnica
**Todos los filtros van al backend como query params.** El frontend solo construye la URL. La lista de agentes se trae del `users-service` mediante un endpoint dedicado.

### Endpoints

**Filtros de interacciones** (ya existente, se expanden los params):
```
GET /api/v1/interactions/client/{client_id}
  ?type=call,email              → múltiples valores separados por coma
  ?status=pending,in_progress
  ?agent_id=uuid1,uuid2
  ?date_from=2024-01-01T00:00:00Z
  ?date_to=2024-11-30T23:59:59Z
  ?page=1
  ?page_size=20
```

**Lista de agentes para el filtro** 🆕:
```
GET /api/v1/users/agents
Headers: X-User-Id, X-User-Role
```

**Response:**
```json
{
  "success": true,
  "data": [
    { "id": "uuid", "full_name": "María García", "role": "soporte" },
    { "id": "uuid", "full_name": "Carlos López", "role": "comercial" }
  ]
}
```

> **Nota:** Este endpoint solo retorna usuarios con `is_active=True` y rol `soporte` o `comercial` (agentes operativos). No incluye admin.

### Frontend — manejo de filtros con TanStack Query

```typescript
// hooks/queries/useInteractions.query.ts
interface InteractionFilters {
  type?:      string[]
  status?:    string[]
  agent_id?:  string[]
  date_from?: string
  date_to?:   string
  page?:      number
  page_size?: number
}

export const useInteractionsQuery = (clientId: string, filters: InteractionFilters) => {
  return useQuery({
    queryKey: ['interactions', clientId, filters],  // filters en la key → refetch automático
    queryFn:  () => interactionService.list(clientId, filters),
    staleTime: 30_000,
  })
}
```

Cuando el usuario cambia un filtro, el estado del componente cambia → la `queryKey` cambia → TanStack Query hace el fetch automáticamente. No se necesita lógica manual de refetch.

### Estado de filtros en frontend (Zustand)

```typescript
// store/ui.store.ts — agregar slice de filtros
interface InteractionFiltersState {
  filters: InteractionFilters
  setFilter:   (key: keyof InteractionFilters, value: unknown) => void
  clearFilters: () => void
}
```

---

## HU-11 — Editar interacción existente

**Como** usuario con permisos
**Quiero** editar una interacción registrada
**Para** corregir o actualizar la información

### Criterios de aceptación
- Solo `admin` y `soporte` pueden editar
- Campos editables: tipo, estado, asunto, descripción, notas internas
- Auditoría: registrar editor, fecha, valor anterior y nuevo valor
- Notas internas: cada edición genera nueva versión
- Los cambios se reflejan inmediatamente en el timeline

### Decisión técnica
**Backend valida el rol** a través del header `X-User-Role`. Si el rol es `comercial`, el endpoint retorna `403`. La auditoría se almacena en una tabla separada `interaction_audit` (esquema propuesto abajo — decisión de implementación pendiente).

### Endpoint

```
PUT /api/v1/interactions/{interaction_id}
Headers: X-User-Id, X-User-Role
```

**Request body:**
```json
{
  "type":           "email",
  "status":         "resolved",
  "subject":        "Seguimiento propuesta — actualizado",
  "notes":          "Se acordó reunión para la próxima semana",
  "internal_notes": "Versión actualizada de las notas internas"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "id":          "uuid",
    "updated_at":  "2024-11-21T10:00:00Z",
    "last_edited_by": "uuid-del-editor"
  }
}
```

**Response 403 (si rol es comercial):**
```json
{
  "success": false,
  "error": {
    "code":    "FORBIDDEN",
    "message": "No tienes permisos para editar interacciones"
  }
}
```

### Tabla de auditoría — propuesta de esquema 🆕

> **Decisión pendiente.** Se presentan dos opciones para que elijas:

**Opción A — Tabla `interaction_audit` separada (recomendada)**
```sql
CREATE TABLE interaction_audit (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interaction_id   UUID NOT NULL REFERENCES interactions(id) ON DELETE CASCADE,
    edited_by        UUID NOT NULL,           -- X-User-Id del editor
    edited_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    field_name       VARCHAR(50) NOT NULL,    -- 'type', 'status', 'subject', etc.
    previous_value   TEXT,
    new_value        TEXT
);

CREATE INDEX idx_audit_interaction_id ON interaction_audit(interaction_id);
CREATE INDEX idx_audit_edited_by ON interaction_audit(edited_by);
```

✅ Pros: historial completo campo por campo, consultas eficientes, no infla la tabla principal
❌ Cons: requiere insertar N filas por edición (una por campo modificado)

**Opción B — Campo JSON en `interactions`**
```sql
ALTER TABLE interactions
ADD COLUMN audit_log JSONB DEFAULT '[]';
-- [{ "edited_by": "uuid", "edited_at": "...", "changes": { "status": { "from": "pending", "to": "resolved" } } }]
```

✅ Pros: simple, todo en una tabla
❌ Cons: el JSON crece indefinidamente, difícil de consultar, no tiene índices eficientes

**Recomendación: Opción A.** Más trabajo inicial pero escala correctamente.

### Lógica de auditoría en el use case (interactions-service)

```python
# application/use_cases/update_interaction.py

async def execute(self, interaction_id: UUID, dto: UpdateInteractionDTO, editor_id: UUID):

    current = await self.repo.get_by_id(interaction_id)

    if not current:
        raise InteractionNotFoundError()

    # Detectar campos que cambiaron
    audit_entries = []
    fields = ['type', 'status', 'subject', 'notes', 'internal_notes']

    for field in fields:
        previous = getattr(current, field)
        new      = getattr(dto, field, None)
        if new is not None and previous != new:
            audit_entries.append(AuditEntry(
                interaction_id=interaction_id,
                edited_by=editor_id,
                field_name=field,
                previous_value=str(previous),
                new_value=str(new),
            ))

    # Actualizar interacción
    updated = await self.repo.update(interaction_id, dto, editor_id)

    # Guardar auditoría
    if audit_entries:
        await self.audit_repo.bulk_save(audit_entries)

    return updated
```

### Frontend — TanStack Query mutation
```typescript
export const useUpdateInteractionMutation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateInteractionDTO }) =>
      interactionService.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['interactions'] })
      queryClient.invalidateQueries({ queryKey: ['interactions', variables.id] })
    },
  })
}
```

### Roles permitidos

| Acción | Admin | Soporte | Comercial |
|---|---|---|---|
| Editar tipo | ✅ | ✅ | ❌ |
| Editar estado | ✅ | ✅ | ❌ |
| Editar asunto | ✅ | ✅ | ❌ |
| Editar descripción | ✅ | ✅ | ❌ |
| Editar notas internas | ✅ | ✅ | ❌ |

---

## HU-12 — Trazabilidad de la interacción

**Como** usuario
**Quiero** visualizar información técnica y de trazabilidad
**Para** conocer quién creó y quién editó la interacción

### Criterios de aceptación
- Agente creador original (nunca cambia)
- Fecha de creación
- Fecha de última actualización
- Duración
- ID de la interacción
- Si fue editada, se actualiza "última actualización"
- Lista de editores almacenada en backend

### Decisión técnica
Los campos de trazabilidad vienen del endpoint `GET /interactions/{id}`. La lista de editores se consulta desde `interaction_audit`. Se crea un endpoint adicional para el historial de ediciones.

### Endpoint principal (ya existente, se expande el response)

```
GET /api/v1/interactions/{interaction_id}
```

**Response expandido:**
```json
{
  "success": true,
  "data": {
    "id":              "uuid",
    "type":            "call",
    "status":          "resolved",
    "subject":         "Seguimiento propuesta",
    "notes":           "...",
    "internal_notes":  "...",
    "interaction_date": "2024-11-20T14:30:00Z",
    "duration_minutes": 30,
    "created_by":      "uuid-agente-creador",
    "created_at":      "2024-11-20T14:35:00Z",
    "updated_at":      "2024-11-21T10:00:00Z",
    "last_edited_by":  "uuid-ultimo-editor"
  }
}
```

### Endpoint historial de ediciones 🆕

```
GET /api/v1/interactions/{interaction_id}/audit
Headers: X-User-Id, X-User-Role
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "edited_by":     "uuid",
      "edited_at":     "2024-11-21T10:00:00Z",
      "field_name":    "status",
      "previous_value":"pending",
      "new_value":     "resolved"
    }
  ]
}
```

### Frontend — panel lateral de trazabilidad
```
InteractionDetailPanel (organismo)
├── TraceabilityBlock (molécula)
│   ├── Text "Creado por: María García"
│   ├── Text "Fecha creación: 20 nov 2024"
│   ├── Text "Última actualización: hace 2 horas"
│   ├── Text "Duración: 30 min"
│   └── Text "ID: xxxxxxxx"
└── AuditLog (molécula)        → solo si hubo ediciones
    └── AuditEntry (átomo)     → por cada cambio registrado
```

---

## Resumen de nuevos endpoints por servicio

### interactions-service — endpoints nuevos 🆕

| Método | Ruta | HU | Descripción |
|---|---|---|---|
| GET | `/api/v1/interactions/metrics` | HU-01 | Métricas globales del dashboard |
| GET | `/api/v1/interactions/client/{id}/summary` | HU-04, HU-05 | Métricas del cliente |
| GET | `/api/v1/interactions/{id}/audit` | HU-12 | Historial de ediciones |

### users-service — endpoints nuevos 🆕

| Método | Ruta | HU | Descripción |
|---|---|---|---|
| GET | `/api/v1/users/agents` | HU-10 | Lista de agentes para filtro |

### interactions — tabla nueva 🆕

| Tabla | HU | Estado |
|---|---|---|
| `interaction_audit` | HU-11, HU-12 | Pendiente decisión de esquema |

---

## Resumen de decisiones técnicas tomadas

| # | Decisión | Resultado |
|---|---|---|
| 1 | ¿Dónde se filtran las interacciones? | Backend — query params |
| 2 | ¿Dónde se calculan las métricas? | Backend — SQL agregado |
| 3 | ¿Dónde se formatea "hace X tiempo"? | Frontend — `date-fns` |
| 4 | ¿Dónde se agrupa el timeline por fecha? | Frontend — utilidad `groupByDate` |
| 5 | ¿Quién puede editar interacciones? | Solo `admin` y `soporte` |
| 6 | ¿Dónde vive la auditoría? | Tabla `interaction_audit` separada (opción A) — **pendiente confirmar** |
| 7 | ¿Las opciones de tipo/estado son estáticas? | Sí — constantes en frontend, enums en backend |
| 8 | ¿La lista de agentes viene del backend? | Sí — `GET /users/agents` |
| 9 | ¿Dónde se calculan los últimos 30 días? | Backend filtra con SQL, frontend solo calcula la fecha |
| 10 | ¿Se invalidan las métricas al crear/editar? | Sí — `invalidateQueries` en las mutations de TanStack Query |
