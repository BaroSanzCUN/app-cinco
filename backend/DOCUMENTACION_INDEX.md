# 🔐 Documentación del Sistema de Autenticación y API Keys

## 📚 Índice de Documentación

Este directorio contiene toda la documentación del nuevo sistema de autenticación dual (JWT + API Keys) implementado en el backend.

---

## 📄 Archivos de Documentación

### 1. **RESUMEN_API_KEYS.md** ⭐ EMPEZAR AQUÍ
**Audiencia:** Administradores, Team Leads, DevOps  
**Contenido:** Resumen ejecutivo completo del sistema
- Arquitectura general
- Casos de uso
- Comandos de gestión
- Seguridad y mejores prácticas
- Monitoreo y mantenimiento
- Checklist de despliegue

### 2. **GUIA_RAPIDA_API_KEYS.md** 
**Audiencia:** Desarrolladores, Integradores  
**Contenido:** Guía práctica paso a paso
- Inicio rápido en 2 pasos
- Gestión de API Keys
- Ejemplos de código en múltiples lenguajes (Python, JS, PHP, C#)
- Configuración de seguridad
- Troubleshooting

### 3. **API_KEYS_README.md**
**Audiencia:** Desarrolladores Backend, Arquitectos  
**Contenido:** Documentación técnica detallada
- Características del sistema
- Configuración interna
- Uso avanzado
- Permisos personalizados
- Monitoreo y logs
- Ejemplos de integración completos

### 4. **COMPATIBILIDAD_FRONTEND.md**
**Audiencia:** Desarrolladores Frontend  
**Contenido:** Impacto en el frontend existente
- Compatibilidad retroactiva (sin cambios requeridos)
- Orden de autenticación
- Diferencias entre JWT y API Keys
- FAQ y troubleshooting

---

## 🧪 Scripts de Prueba

### test_apikey.py
**Descripción:** Prueba básica del modelo APIKey
**Uso:**
```bash
python manage.py shell < test_apikey.py
```

### test_complete_auth.py
**Descripción:** Suite completa de pruebas de autenticación
**Uso:**
```bash
python test_complete_auth.py [api_key] [username] [password]
```

**Ejemplo:**
```bash
python test_complete_auth.py cinco_abc123... admin admin123
```

---

## 🚀 Inicio Rápido

### Para Administradores

1. **Leer documentación principal:**
   ```bash
   cat RESUMEN_API_KEYS.md
   ```

2. **Aplicar migraciones:**
   ```bash
   python manage.py migrate
   ```

3. **Crear primera API Key:**
   ```bash
   python manage.py create_apikey "Mi Primera App"
   ```

4. **Verificar estado:**
   ```bash
   python manage.py list_apikeys
   ```

### Para Desarrolladores de Frontend

1. **Leer compatibilidad:**
   ```bash
   cat COMPATIBILIDAD_FRONTEND.md
   ```

2. **Conclusión:** Tu código sigue funcionando sin cambios ✅

### Para Desarrolladores de Integraciones

1. **Leer guía rápida:**
   ```bash
   cat GUIA_RAPIDA_API_KEYS.md
   ```

2. **Solicitar API Key al administrador**

3. **Integrar usando ejemplos de código de la guía**

---

## 📋 Comandos Principales

### Gestión de API Keys

```bash
# Crear
python manage.py create_apikey "Nombre" [--opciones]

# Listar
python manage.py list_apikeys [--active-only]

# Revocar
python manage.py revoke_apikey <ID> [--permanent]

# Reactivar
python manage.py activate_apikey <ID>
```

### Administración

```bash
# Admin web
http://localhost:8000/admin/security/apikey/

# Ver logs
tail -f logs/security.log

# Documentación OpenAPI
http://localhost:8000/api/docs/
```

---

## 🏗️ Estructura de Archivos

```
backend/
├── 📖 Documentación
│   ├── RESUMEN_API_KEYS.md          # Resumen ejecutivo
│   ├── GUIA_RAPIDA_API_KEYS.md      # Guía práctica
│   ├── API_KEYS_README.md           # Doc técnica completa
│   ├── COMPATIBILIDAD_FRONTEND.md   # Info para frontend
│   └── DOCUMENTACION_INDEX.md       # Este archivo
│
├── 🧪 Scripts de Prueba
│   ├── test_apikey.py               # Test básico
│   └── test_complete_auth.py        # Test completo
│
└── apps/security/
    ├── models.py                    # Modelo APIKey
    ├── admin.py                     # Admin Django
    ├── authentication/
    │   └── api_key_authentication.py
    ├── permissions/
    │   └── api_permissions.py
    ├── throttling/
    │   └── api_throttling.py
    └── management/commands/
        ├── create_apikey.py
        ├── list_apikeys.py
        ├── revoke_apikey.py
        └── activate_apikey.py
```

---

## 🎯 Casos de Uso por Rol

### 👤 Soy Administrador del Sistema
**Necesito:** Gestionar API Keys de producción  
**Leo:** `RESUMEN_API_KEYS.md`  
**Hago:** 
1. Crear API Keys para sistemas autorizados
2. Configurar rate limits y restricciones
3. Monitorear logs de seguridad
4. Revocar keys comprometidas

### 👨‍💻 Soy Desarrollador Backend
**Necesito:** Entender cómo funciona el sistema  
**Leo:** `API_KEYS_README.md`  
**Hago:**
1. Entender la arquitectura
2. Crear permisos personalizados si es necesario
3. Implementar lógica específica por tipo de auth
4. Testing con ambos métodos de autenticación

### 👩‍💻 Soy Desarrollador Frontend
**Necesito:** Saber si debo cambiar algo  
**Leo:** `COMPATIBILIDAD_FRONTEND.md`  
**Hago:**
1. Confirmar que no hay cambios requeridos
2. Verificar que mi app sigue funcionando
3. Opcional: Mejorar manejo de errores

### 🔌 Soy Desarrollador de Integración
**Necesito:** Consumir la API desde sistema externo  
**Leo:** `GUIA_RAPIDA_API_KEYS.md`  
**Hago:**
1. Solicitar API Key al admin
2. Usar ejemplos de código de la guía
3. Implementar manejo de errores
4. Configurar variables de entorno

### 🧪 Soy QA / Tester
**Necesito:** Probar el sistema  
**Leo:** Esta guía (`DOCUMENTACION_INDEX.md`)  
**Hago:**
1. Ejecutar `test_complete_auth.py`
2. Probar casos de error (API Key inválida, etc.)
3. Verificar rate limiting
4. Documentar resultados

---

## ⚠️ Importante

### ✅ Esto Funciona Sin Cambios
- Frontend existente
- Autenticación JWT de usuarios
- Login/Logout
- Refresh de tokens
- Todas las funcionalidades actuales

### 🆕 Esto es Nuevo
- Autenticación por API Key
- Restricción de endpoints antes públicos
- Rate limiting por API Key
- Gestión de aplicaciones externas autorizadas

### ⚡ Acción Requerida
- [ ] Aplicar migraciones: `python manage.py migrate`
- [ ] Crear API Keys para sistemas externos que lo necesiten
- [ ] Informar a equipos externos sobre el nuevo sistema
- [ ] Monitorear logs en los primeros días

---

## 📞 Contacto

**Para API Keys de producción:**  
Contactar al administrador del sistema

**Para soporte técnico:**  
Ver logs en `backend/logs/security.log`

**Para reportar problemas de seguridad:**  
Contactar inmediatamente al equipo de seguridad

---

## 🔄 Actualizaciones

**Versión:** 1.0  
**Fecha:** 4 de marzo de 2026  
**Autor:** GitHub Copilot  
**Estado:** ✅ Producción

### Historial de Cambios
- **v1.0 (2026-03-04):** Implementación inicial
  - Modelo APIKey
  - Autenticación dual (JWT + API Key)
  - Permisos y throttling
  - Comandos de gestión
  - Documentación completa
  - Restricción de todos los endpoints

---

## 🎓 Material de Capacitación

### Sesión 1: Introducción (30 min)
**Para:** Todo el equipo  
**Material:** `RESUMEN_API_KEYS.md`  
**Temas:**
- ¿Por qué API Keys?
- Arquitectura del sistema
- Impacto en cada rol

### Sesión 2: Administración (45 min)
**Para:** Admins, DevOps  
**Material:** `RESUMEN_API_KEYS.md` + Comandos  
**Temas:**
- Crear y gestionar API Keys
- Configurar restricciones
- Monitoreo y logs
- Buenas prácticas de seguridad

### Sesión 3: Integración (60 min)
**Para:** Desarrolladores de integraciones  
**Material:** `GUIA_RAPIDA_API_KEYS.md`  
**Temas:**
- Solicitar API Key
- Ejemplos de código
- Manejo de errores
- Testing

### Sesión 4: Desarrollo Avanzado (45 min)
**Para:** Desarrolladores backend  
**Material:** `API_KEYS_README.md`  
**Temas:**
- Arquitectura interna
- Permisos personalizados
- Diferenciar entre usuarios y API Keys
- Casos de uso avanzados

---

## 📊 Métricas de Éxito

### Semana 1
- [ ] Migraciones aplicadas
- [ ] API Keys de producción creadas
- [ ] Sistemas externos migrados
- [ ] 0 incidentes de seguridad
- [ ] Frontend funcionando sin problemas

### Mes 1
- [ ] Monitoreo automatizado configurado
- [ ] Logs revisados semanalmente
- [ ] Rate limits ajustados según uso real
- [ ] Documentación actualizada según feedback
- [ ] Equipo capacitado completamente

### Trimestre 1
- [ ] Sistema estable sin incidentes
- [ ] Métricas de uso recopiladas
- [ ] Optimizaciones implementadas
- [ ] Proceso de gestión de keys documentado
- [ ] Plan de rotación de keys establecido

---

**Última actualización:** 4 de marzo de 2026  
**Próxima revisión:** 4 de abril de 2026
