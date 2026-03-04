"""
Script de prueba del sistema de API Keys
Ejecutar con: python manage.py shell < test_apikey.py
O: python manage.py shell -c "exec(open('test_apikey.py').read())"
"""

from apps.security.models import APIKey
from django.utils import timezone
from datetime import timedelta

print("\n" + "="*70)
print("PRUEBA DEL SISTEMA DE API KEYS")
print("="*70 + "\n")

# 1. Crear una API Key de prueba
print("1. Creando API Key de prueba...")
key, prefix, key_hash = APIKey.generate_key()
api_key = APIKey.objects.create(
    name="App de Prueba",
    description="API Key para testing",
    key_hash=key_hash,
    prefix=prefix,
    rate_limit=100,
    is_active=True
)
print(f"✓ API Key creada: {api_key.name}")
print(f"  ID: {api_key.id}")
print(f"  Key: {key}")
print(f"  Prefijo: {prefix}")
print()

# 2. Verificar la key
print("2. Verificando API Key...")
if api_key.verify_key(key):
    print("✓ Verificación exitosa")
else:
    print("✗ Error en verificación")
print()

# 3. Probar con key incorrecta
print("3. Probando con key incorrecta...")
fake_key = "cinco_fakekeyfakekeyfakekeyfake"
if not api_key.verify_key(fake_key):
    print("✓ Correctamente rechazada")
else:
    print("✗ Error: aceptó key falsa")
print()

# 4. Crear API Key con expiración
print("4. Creando API Key con expiración...")
key2, prefix2, key_hash2 = APIKey.generate_key()
api_key_expiring = APIKey.objects.create(
    name="App Temporal",
    key_hash=key_hash2,
    prefix=prefix2,
    rate_limit=50,
    expires_at=timezone.now() + timedelta(days=30),
    is_active=True
)
print(f"✓ API Key con expiración creada")
print(f"  Expira: {api_key_expiring.expires_at.strftime('%Y-%m-%d')}")
print()

# 5. Crear API Key con IPs restringidas
print("5. Creando API Key con IPs restringidas...")
key3, prefix3, key_hash3 = APIKey.generate_key()
api_key_restricted = APIKey.objects.create(
    name="App Restringida",
    key_hash=key_hash3,
    prefix=prefix3,
    rate_limit=200,
    allowed_ips="192.168.1.100, 10.0.0.50",
    is_active=True
)
print(f"✓ API Key con IPs restringidas creada")
print(f"  IPs: {api_key_restricted.allowed_ips}")
print()

# 6. Listar todas las API Keys
print("6. Listando todas las API Keys...")
all_keys = APIKey.objects.all()
print(f"Total: {all_keys.count()}")
for ak in all_keys:
    status = "✓ Activa" if ak.is_active else "✗ Inactiva"
    print(f"  - {ak.name} ({ak.prefix}...) - {status}")
print()

# 7. Estadísticas
print("7. Estadísticas:")
print(f"  API Keys activas: {APIKey.objects.filter(is_active=True).count()}")
print(f"  API Keys inactivas: {APIKey.objects.filter(is_active=False).count()}")
print(f"  API Keys sin usar: {APIKey.objects.filter(last_used_at__isnull=True).count()}")
print()

print("="*70)
print("PRUEBAS COMPLETADAS")
print("="*70)
print("\n⚠ Recuerda guardar las API Keys generadas si las necesitas:")
print(f"\nAPI Key de prueba: {key}")
print(f"\nPara probar en cURL:")
print(f'curl -H "X-API-Key: {key}" http://localhost:8000/operaciones/actividades/')
print()
