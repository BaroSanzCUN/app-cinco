# Patron Unico: ViewSet -> Service -> Serializer

Este documento define la convencion para nuevos endpoints y refactors en el backend.

## Objetivo

Separar responsabilidades para facilitar mantenimiento, pruebas y escalado.

## Contrato por Capa

### 1) ViewSet (capa HTTP)

Responsabilidades:
- Parsear request (query params, body, path params).
- Seleccionar serializer segun accion (`get_serializer_class`).
- Validar entrada con serializer (`is_valid`).
- Llamar al Service con datos validados y contexto minimo (por ejemplo `actor_user`).
- Traducir resultados del Service a respuestas HTTP (`Response`, status codes).

No debe contener:
- Reglas de negocio complejas.
- Construccion de querysets de dominio extensos.
- Reglas de borrado/creacion que pertenezcan al dominio.

### 2) Service (capa dominio/aplicacion)

Responsabilidades:
- Implementar reglas de negocio.
- Orquestar operaciones de modelos y transacciones.
- Encapsular filtros de negocio y validaciones de dominio.
- Exponer metodos claros para ViewSet (por ejemplo `listar`, `crear`, `eliminar`).

Buenas practicas:
- Metodos puros respecto a HTTP (sin depender de `request` o `self` del ViewSet).
- Recibir parametros explicitos (`actor_user`, `filtros`, `validated_data`).
- Mantener operaciones de escritura dentro de `transaction.atomic()` cuando aplique.

### 3) Serializer (capa contrato de datos)

Responsabilidades:
- Validar forma y tipos de datos de entrada/salida.
- Transformar datos entre JSON y entidades.
- Reglas de validacion de campo (`validate_<campo>`).

No debe contener:
- Consultas complejas de negocio.
- Operaciones transaccionales de varias entidades.

## Flujo Recomendado

1. `ViewSet` recibe request.
2. `Serializer` valida input.
3. `Service` ejecuta caso de uso.
4. `ViewSet` serializa salida y responde.

## Estandar aplicado en este repo

- `apps/operaciones/views/actividad_view.py` delega consultas, creacion y eliminacion a `ActividadService`.
- `apps/empleados/views/empleado_view.py` delega consultas y eliminacion a `EmpleadoService`.
- `apps/security/services/menu_service.py` contiene `MenuService` que construye menu dinamico por usuario.
  - `apps/security/views/menu_view.py` delega a `MenuService.obtener_menu_para_usuario()`.
- `apps/authentication/services/authentication_service.py` contiene `AuthenticationService` con metodos:
  - `login(username, password, request)` - autentica usuario y genera tokens JWT.
  - `refresh_tokens(refresh_token_str, request)` - rota refresh token con validacion de fingerprint.
  - `logout(refresh_token_str)` - revoca refresh token.
  - `health_check()` - verifica estado de conexiones a BDs.
  - `get_secure_cookie_settings()` - retorna config para cookies httpOnly.
  - Views refactorizadas: `LoginView`, `RefreshTokenView`, `LogoutView`, `HealthCheckView`.

## Checklist para nuevos endpoints

- [ ] El ViewSet no usa `request` dentro de Service por acoplamiento.
- [ ] Existe un metodo de Service por caso de uso principal.
- [ ] El Serializer valida payload antes de tocar DB.
- [ ] Los codigos HTTP se definen en ViewSet.
- [ ] El Service es testeable sin capa HTTP.
