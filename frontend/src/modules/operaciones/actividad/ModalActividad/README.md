# ModalActividad - Modal Especializado

## 📋 Visión General

ModalActividad es un modal especializado para crear/editar actividades, construido sobre la base modular de Modal y ApplicationForm. Sigue los mismos principios de **Clean Code** y **SOLID**.

## 🏗️ Arquitectura

```
ModalActividad/
├── index.tsx                              # Exportación pública
├── ModalActividad.tsx                    # Componente principal (60 líneas)
├── ModalActividad.utils.ts               # Utilidades (40 líneas)
├── ModalActividad.hooks.ts               # Custom hooks (35 líneas)
└── components/
    ├── ActividadFormContainer.tsx        # Contenedor de formulario
    └── index.ts                          # Exportación de componentes
```

## 🎯 Principios

### Single Responsibility
- `ModalActividad.tsx`: Orquesta modal + formulario
- `ModalActividad.utils.ts`: Lógica pura (defaults, títulos, config)
- `ModalActividad.hooks.ts`: Manejo de estado y submit
- `ActividadFormContainer.tsx`: Renderiza solo el formulario

### Composition
```tsx
<Button onClick={open} />
<Modal isOpen>
  <Modal.Header />     ← Composición
  <Modal.Content>      ← Composición
    <ActividadForm /> ← Sub-componente interno
  </Modal.Content>
</Modal>
```

## 📁 Archivos

### `ModalActividad.tsx` (60 líneas)
Componente principal:
- Gestiona apertura/cierre del modal
- Orquesta formulario dentro del modal
- Maneja submit y errores
- Renderiza título dinámico según modo

### `ModalActividad.utils.ts` (40 líneas)
Funciones helper:
- `getDefaultValues()` - Obtiene valores por defecto
- `getModalTitle()` - Obtiene título dinámico
- `MODAL_ACTIVIDAD_CONFIG` - Configuración constante

### `ModalActividad.hooks.ts` (35 líneas)
Custom hook:
- `useModalActividadLogic()` - Lógica integrada:
  - Submission del formulario
  - Manejo de errores
  - Estados de carga

### `ActividadFormContainer.tsx` (20 líneas)
Contenedor simple:
- Renderiza ActividadForm con props adecuados
- Aísla la lógica de presentación

## 🔄 Flujo

```
Usuario clickea botón
      ↓  
Modal se abre
      ↓
Usuario completa formulario
      ↓
Submit → Validación
      ↓
Api call → Manejo de errores
      ↓
Cierre automático o mostrar error
```

## 📊 Mejoras respecto a versión anterior

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Líneas totales** | 60 | 155 | 
| **Separación de concerns** | Nula | Total |
| **Documentación** | 0% | 100% |
| **Testabilidad** | Baja | Alta |
| **Reutilización de lógica** | Nula | Alta |

## 🚀 Uso

### Crear Actividad
```tsx
<ModalActividad
  mode="create"
  textButton="Nueva Actividad"
  iconButton={<PlusIcon />}
/>
```

### Editar Actividad
```tsx
<ModalActividad
  mode="edit"
  actividad={actividad}
  textButton="Editar"
/>
```

## 🧪 Testing

### Hook Testing
```typescript
describe('useModalActividadLogic', () => {
  it('should call onClose after successful submit', () => {
    // Test del hook
  });
});
```

### Component Testing
```typescript
describe('ModalActividad', () => {
  it('should display create title in create mode', () => {
    render(<ModalActividad mode="create" />);
    expect(screen.getByText('Crear Nueva Actividad')).toBeInTheDocument();
  });
});
```

---

**Última actualización**: Marzo 2026  
**Versión**: 2.0.0 (Modular)
