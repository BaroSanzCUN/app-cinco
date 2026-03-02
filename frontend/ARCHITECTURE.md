# Arquitectura del Proyecto Frontend

## 📐 Principios de Diseño

Este proyecto sigue una **arquitectura modular escalable** basada en:

1. **Clean Code** - Código limpio y legible
2. **SOLID Principles** - Principios de diseño orientado a objetos
3. **Separation of Concerns** - Separación clara de responsabilidades
4. **Feature-Based Structure** - Organización por features/módulos

## 🗂️ Estructura de Carpetas

```
frontend/src/
├── app/                          # Next.js App Router (rutas)
├── components/                   # Componentes reutilizables
│   ├── common/                   # Componentes comunes (DataTable, Modal, etc.)
│   │   └── [Component]/         # Cada componente en su carpeta modular
│   │       ├── index.tsx        # Exportación pública
│   │       ├── Component.tsx    # Componente principal
│   │       ├── Component.utils.ts    # Utilidades
│   │       ├── Component.hooks.ts    # Custom hooks
│   │       ├── Component.types.ts    # Tipos (opcional)
│   │       ├── components/      # Sub-componentes
│   │       └── README.md        # Documentación
│   ├── form/                    # Componentes de formulario
│   └── ui/                      # Componentes UI básicos (Button, Input)
│
├── hooks/                       # Custom hooks globales
│   ├── useTableUrlState.ts     # Hook para estado de tabla en URL
│   └── [feature]Hook.ts        # Hooks por feature
│
├── modules/                     # Módulos de negocio (features)
│   └── [domain]/               # Por dominio de negocio
│       └── [entity]/           # Por entidad
│           ├── index.tsx       # Vista principal
│           ├── [entity]Columns.tsx          # Definición de columnas
│           ├── [entity]Table.utils.ts       # Utilidades de tabla
│           ├── Modal[Entity].tsx            # Modal específico
│           └── components/     # Componentes del módulo
│
├── services/                    # Capa de servicios (API calls)
│   ├── api.ts                  # Cliente HTTP base
│   └── [entity]Service.ts      # Servicios por entidad
│
├── store/                       # Estado global (Zustand/Redux)
│   └── [entity].store.ts       # Store por entidad
│
├── schemas/                     # Esquemas de validación (Zod)
│   └── [entity].schema.ts      # Schemas por entidad
│
├── types/                       # Tipos TypeScript globales
│   ├── table.ts                # Tipos de tabla
│   ├── api.ts                  # Tipos de API
│   └── [feature].ts            # Tipos por feature
│
├── utils/                       # Utilidades globales
│   ├── csv.ts                  # Exportación CSV
│   ├── format.ts               # Formateo de datos
│   └── validation.ts           # Validaciones comunes
│
└── context/                     # React Context (si necesario)
    └── [Feature]Context.tsx
```

## 🎯 Convenciones de Código

### 1. Nomenclatura

#### Archivos
- **Componentes**: PascalCase - `DataTable.tsx`, `UserCard.tsx`
- **Utilidades**: camelCase - `formatDate.ts`, `validateEmail.ts`
- **Hooks**: camelCase con prefijo `use` - `useTableState.ts`
- **Tipos**: camelCase - `table.ts`, `api.types.ts`
- **Constantes**: UPPER_SNAKE_CASE - `API_BASE_URL`

#### Carpetas
- **Componentes**: PascalCase - `DataTable/`, `UserProfile/`
- **Módulos**: camelCase - `operaciones/`, `empleados/`
- **Utilidades**: camelCase - `utils/`, `hooks/`

### 2. Estructura de Componentes

Cada componente complejo debe tener su propia carpeta:

```
ComponentName/
├── index.tsx                    # ⚠️ SIEMPRE: Punto de entrada
├── ComponentName.tsx            # Componente principal
├── ComponentName.utils.ts       # Funciones helper
├── ComponentName.hooks.ts       # Custom hooks
├── ComponentName.types.ts       # Tipos específicos (opcional)
├── components/                  # Sub-componentes
│   ├── SubComponent1.tsx
│   └── SubComponent2.tsx
└── README.md                    # Documentación (componentes grandes)
```

**Regla de oro**: Si un componente supera **150 líneas**, separarlo en sub-componentes.

### 3. Separación de Responsabilidades

#### ✅ Hacer: Single Responsibility

```typescript
// ❌ MAL: Todo mezclado
const UserProfile = () => {
  const [user, setUser] = useState();
  const formatDate = (date) => { /* ... */ };
  const fetchUser = async () => { /* ... */ };
  
  return (
    <div>
      {/* 500 líneas de JSX */}
    </div>
  );
};

// ✅ BIEN: Separado por responsabilidad
// UserProfile.tsx - Solo renderizado
// UserProfile.hooks.ts - Custom hook useUserData
// UserProfile.utils.ts - formatDate, validateUser
// components/UserHeader.tsx - Header separado
// components/UserDetails.tsx - Detalles separados
```

#### Niveles de Abstracción

1. **Componente Principal** (Orquestador)
   - Coordina sub-componentes
   - Maneja estado de alto nivel
   - Define layout general
   - **NO** contiene lógica de negocio compleja

2. **Hooks** (Lógica de Estado)
   - Encapsulan lógica reutilizable
   - Manejan efectos secundarios
   - Interactúan con APIs
   - **NO** contienen JSX

3. **Utils** (Funciones Puras)
   - Transformaciones de datos
   - Validaciones
   - Formateo
   - **NO** tienen efectos secundarios
   - **NO** usan hooks

4. **Sub-componentes** (Presentación)
   - Componentes especializados
   - Reciben props específicas
   - Mínima lógica interna
   - **Reutilizables** cuando sea posible

## 🧩 Patrones de Diseño

### 1. Composition Pattern

**Preferir composición sobre props complejas**:

```typescript
// ❌ Evitar: Props complejos
<DataTable
  showSearch
  showColumnToggle
  showExport
  searchPlaceholder="..."
  exportFormat="csv"
/>

// ✅ Mejor: Composición
<DataTable
  toolbarActions={
    <>
      <SearchInput />
      <ColumnToggle />
      <ExportButton format="csv" />
    </>
  }
/>
```

### 2. Render Props / Children Pattern

```typescript
// Flexible y extensible
<DataTable
  data={users}
  columns={columns}
  renderRowActions={(row) => (
    <div>
      <EditButton row={row} />
      <DeleteButton row={row} />
    </div>
  )}
/>
```

### 3. Custom Hooks Pattern

```typescript
// Encapsular lógica compleja
const useTableWithUrl = (config) => {
  const { globalFilter, setGlobalFilter } = useTableUrlState(config);
  const { data, isLoading } = useTableData();
  
  return {
    // Estado completo listo para usar
    globalFilter,
    setGlobalFilter,
    data,
    isLoading,
  };
};

// Uso limpio en componentes
const MyTable = () => {
  const table = useTableWithUrl({ pageSize: 10 });
  
  return <DataTable {...table} />;
};
```

### 4. Container/Presenter Pattern

```typescript
// Container (lógica)
const UserListContainer = () => {
  const { users, loading } = useUsers();
  const handleDelete = (id) => { /* ... */ };
  
  return (
    <UserListPresenter
      users={users}
      loading={loading}
      onDelete={handleDelete}
    />
  );
};

// Presenter (UI pura)
const UserListPresenter = ({ users, loading, onDelete }) => {
  if (loading) return <Spinner />;
  
  return (
    <ul>
      {users.map(user => (
        <UserItem key={user.id} user={user} onDelete={onDelete} />
      ))}
    </ul>
  );
};
```

## 📦 Módulos por Feature

### Estructura de un Módulo

```
modules/operaciones/actividad/
├── index.tsx                           # Vista principal
├── gestionActividadesView.tsx         # Container component
├── actividadColumns.tsx               # Definición de columnas tabla
├── actividadTable.utils.ts            # Config tabla (CSV, etc.)
├── ModalActividad.tsx                 # Modal CRUD
├── components/                         # Componentes locales
│   ├── ActividadCard.tsx
│   └── ActividadFilters.tsx
└── README.md                           # Documentación del módulo
```

### Reglas para Módulos

1. **Cada módulo es auto-contenido**
   - No depende de otros módulos
   - Puede tener sus propios componentes
   - Comparte solo via hooks/services globales

2. **Reutilizar componentes comunes**
   - Usar `DataTable` para tablas
   - Usar `Modal` para modales
   - Crear nuevos solo si es específico del dominio

3. **Mantener consistencia**
   - Misma estructura en todos los módulos
   - Mismas convenciones de nombres
   - Mismo patrón de hooks

## 🔌 Integración de Servicios

### Capa de Servicios

```typescript
// services/actividadService.ts
import { apiClient } from './api';
import { ActividadFormData } from '@/schemas/actividades.schema';

export const actividadService = {
  getAll: () => apiClient.get<ActividadFormData[]>('/actividades'),
  getById: (id: number) => apiClient.get<ActividadFormData>(`/actividades/${id}`),
  create: (data: ActividadFormData) => apiClient.post('/actividades', data),
  update: (id: number, data: ActividadFormData) => apiClient.put(`/actividades/${id}`, data),
  delete: (id: number) => apiClient.delete(`/actividades/${id}`),
};
```

### Store (Estado Global)

```typescript
// store/actividad.store.ts
import { create } from 'zustand';
import { actividadService } from '@/services/actividadService';

interface ActividadStore {
  actividades: ActividadFormData[];
  isLoading: boolean;
  loadActividades: () => Promise<void>;
  createActividad: (data: ActividadFormData) => Promise<void>;
}

export const useActividadStore = create<ActividadStore>((set) => ({
  actividades: [],
  isLoading: false,
  
  loadActividades: async () => {
    set({ isLoading: true });
    try {
      const data = await actividadService.getAll();
      set({ actividades: data, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },
  
  createActividad: async (data) => {
    await actividadService.create(data);
    // Recargar lista después de crear
    await get().loadActividades();
  },
}));
```

## 🎨 Estilos y Theming

### Convenciones de Clases

1. **Usar TailwindCSS** como base
2. **Variantes dark mode** con `dark:` prefix
3. **Clases responsive** con breakpoints (`md:`, `lg:`)
4. **Evitar inline styles** cuando sea posible

```typescript
// ✅ Bien
className="px-4 py-2 rounded bg-blue-500 hover:bg-blue-600 dark:bg-blue-700"

// ❌ Evitar
style={{ padding: '8px 16px', borderRadius: '4px' }}
```

## 🧪 Testing

### Niveles de Testing

```
tests/
├── unit/                        # Unit tests (utils, hooks)
│   ├── utils/
│   │   └── csv.test.ts
│   └── hooks/
│       └── useTableUrlState.test.ts
│
├── integration/                 # Integration tests (componentes)
│   └── components/
│       └── DataTable.test.tsx
│
└── e2e/                        # End-to-end tests (Playwright/Cypress)
    └── actividades.spec.ts
```

### Qué Testear

1. **Utils**: Todas las funciones puras
2. **Hooks**: Lógica de estado y efectos
3. **Componentes**: Interacciones y renderizado
4. **Integración**: Flujos completos

## 📝 Documentación

### Niveles de Documentación

1. **JSDoc** en funciones públicas
   ```typescript
   /**
    * Exporta datos a CSV con configuración flexible.
    *
    * @template TData - Tipo de datos
    * @param data - Array de datos a exportar
    * @param config - Configuración de columnas y nombre de archivo
    */
   export const exportToCsv = <TData>(/* ... */) => {
     // ...
   };
   ```

2. **README.md** en componentes complejos
   - Arquitectura del componente
   - Ejemplos de uso
   - Props disponibles
   - Casos de edge

3. **ARCHITECTURE.md** (este archivo)
   - Decisiones de arquitectura
   - Patrones del proyecto
   - Convenciones

## 🚀 Escalabilidad

### Agregar Nueva Feature

1. **Identificar dominio** - ¿A qué módulo pertenece?
2. **Reutilizar componentes** - Usar `DataTable`, `Modal`, etc.
3. **Crear service** - API calls en `services/`
4. **Crear store** - Estado global en `store/`
5. **Crear schemas** - Validación con Zod en `schemas/`
6. **Crear vista** - Módulo en `modules/`
7. **Documentar** - README en el módulo

### Refactorizar Código Legacy

1. **Identificar responsabilidades** mezcladas
2. **Extraer utils** a archivos separados
3. **Extraer hooks** customizados
4. **Separar en sub-componentes**
5. **Agregar tipos** de TypeScript
6. **Documentar** con JSDoc
7. **Testear** funcionalidad

## ✅ Checklist de Code Review

- [ ] **Separación de responsabilidades**: ¿Cada archivo tiene una única responsabilidad?
- [ ] **Tamaño de archivos**: ¿Todos los archivos < 200 líneas?
- [ ] **Nomenclatura**: ¿Sigue convenciones del proyecto?
- [ ] **Tipos**: ¿Todo tiene tipos de TypeScript?
- [ ] **Documentación**: ¿Funciones públicas tienen JSDoc?
- [ ] **Reutilización**: ¿Se reutilizan componentes comunes?
- [ ] **Performance**: ¿Se usan useMemo/useCallback apropiadamente?
- [ ] **Accesibilidad**: ¿Componentes tienen aria-labels?
- [ ] **Tests**: ¿Hay tests para nueva funcionalidad?
- [ ] **Consistencia**: ¿Sigue patrones existentes?

## 📚 Referencias

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Atomic Design](https://bradfrost.com/blog/post/atomic-web-design/)
- [React Best Practices](https://react.dev/learn/thinking-in-react)
- [TypeScript Best Practices](https://www.typescriptlang.org/docs/handbook/)

---

**Última actualización**: Marzo 2026  
**Versión**: 1.0.0
