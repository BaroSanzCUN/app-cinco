"""
Script de Prueba Completa del Sistema de Autenticación

Ejecutar con:
  python test_complete_auth.py

Requisitos:
  pip install requests
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"
COLORS = {
    'GREEN': '\033[92m',
    'RED': '\033[91m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'END': '\033[0m'
}

def print_section(title):
    print(f"\n{COLORS['BLUE']}{'='*70}{COLORS['END']}")
    print(f"{COLORS['BLUE']}{title.center(70)}{COLORS['END']}")
    print(f"{COLORS['BLUE']}{'='*70}{COLORS['END']}\n")

def print_success(msg):
    print(f"{COLORS['GREEN']}✓ {msg}{COLORS['END']}")

def print_error(msg):
    print(f"{COLORS['RED']}✗ {msg}{COLORS['END']}")

def print_info(msg):
    print(f"{COLORS['YELLOW']}ℹ {msg}{COLORS['END']}")

def test_health_endpoint():
    """Probar endpoint público (no requiere autenticación)"""
    print_section("TEST 1: Endpoint Público (Health Check)")
    
    try:
        response = requests.get(f"{BASE_URL}/auth/health/")
        if response.status_code == 200:
            print_success(f"Health check exitoso: {response.json()}")
            return True
        else:
            print_error(f"Health check falló: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error conectando al servidor: {e}")
        print_info("Asegúrate de que el servidor esté corriendo: python manage.py runserver")
        return False

def test_protected_without_auth():
    """Probar endpoint protegido sin autenticación"""
    print_section("TEST 2: Endpoint Protegido Sin Autenticación")
    
    try:
        response = requests.get(f"{BASE_URL}/operaciones/actividades/")
        if response.status_code == 401:
            print_success("Correctamente rechazado (401 Unauthorized)")
            print_info(f"Mensaje: {response.json().get('detail', 'N/A')}")
            return True
        else:
            print_error(f"Debería retornar 401, pero retornó: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_with_api_key(api_key):
    """Probar endpoint protegido con API Key"""
    print_section("TEST 3: Autenticación con API Key")
    
    if not api_key:
        print_info("No hay API Key para probar")
        print_info("Crea una con: python manage.py create_apikey 'Test App'")
        return False
    
    try:
        headers = {'X-API-Key': api_key}
        response = requests.get(f"{BASE_URL}/operaciones/actividades/", headers=headers)
        
        if response.status_code == 200:
            print_success("Autenticación con API Key exitosa")
            data = response.json()
            print_info(f"Resultados obtenidos: {len(data) if isinstance(data, list) else 'N/A'}")
            return True
        elif response.status_code == 401:
            print_error("API Key rechazada (inválida o expirada)")
            print_info(f"Mensaje: {response.json().get('detail', 'N/A')}")
            return False
        else:
            print_error(f"Status inesperado: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_with_invalid_api_key():
    """Probar con API Key inválida"""
    print_section("TEST 4: API Key Inválida")
    
    try:
        invalid_key = "cinco_invalidkeyinvalidkeyinvalidkey"
        headers = {'X-API-Key': invalid_key}
        response = requests.get(f"{BASE_URL}/operaciones/actividades/", headers=headers)
        
        if response.status_code == 401:
            print_success("API Key inválida correctamente rechazada")
            print_info(f"Mensaje: {response.json().get('detail', 'N/A')}")
            return True
        else:
            print_error(f"Debería rechazar, pero retornó: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_with_jwt(username, password):
    """Probar autenticación JWT completa"""
    print_section("TEST 5: Autenticación JWT (Usuario)")
    
    if not username or not password:
        print_info("No hay credenciales para probar JWT")
        print_info("Proporciona usuario y contraseña como argumentos")
        return False
    
    # 1. Login
    print("  → Paso 1: Login")
    try:
        login_data = {
            'username': username,
            'password': password
        }
        response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
        
        if response.status_code == 200:
            print_success("Login exitoso")
            
            # Obtener token de la cookie o del response
            cookies = response.cookies
            token = None
            
            # Intentar obtener de cookies
            if 'access_token' in cookies:
                token = cookies['access_token']
                print_info("Token obtenido de cookie")
            
            # Si no está en cookie, intentar del body
            if not token:
                data = response.json()
                token = data.get('access_token') or data.get('access')
                if token:
                    print_info("Token obtenido del response body")
            
            if not token:
                print_error("No se pudo obtener el token")
                return False
            
            # 2. Usar token para acceder a endpoint protegido
            print("  → Paso 2: Acceder a endpoint protegido con token")
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{BASE_URL}/operaciones/actividades/",
                headers=headers,
                cookies=cookies
            )
            
            if response.status_code == 200:
                print_success("Acceso con JWT exitoso")
                data = response.json()
                print_info(f"Resultados obtenidos: {len(data) if isinstance(data, list) else 'N/A'}")
                return True
            else:
                print_error(f"Acceso falló: {response.status_code}")
                print_info(f"Mensaje: {response.json().get('detail', 'N/A')}")
                return False
        else:
            print_error(f"Login falló: {response.status_code}")
            print_info(f"Mensaje: {response.json().get('detail', 'N/A')}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def main():
    print(f"{COLORS['BLUE']}")
    print("="*70)
    print("PRUEBA COMPLETA DEL SISTEMA DE AUTENTICACIÓN".center(70))
    print("="*70)
    print(f"{COLORS['END']}")
    
    # Obtener parámetros
    api_key = None
    username = None
    password = None
    
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    if len(sys.argv) > 2:
        username = sys.argv[2]
    if len(sys.argv) > 3:
        password = sys.argv[3]
    
    print_info("Parámetros de prueba:")
    print(f"  - Base URL: {BASE_URL}")
    print(f"  - API Key: {'✓ Proporcionada' if api_key else '✗ No proporcionada'}")
    print(f"  - JWT Credentials: {'✓ Proporcionadas' if username and password else '✗ No proporcionadas'}")
    print()
    
    # Ejecutar pruebas
    results = []
    
    results.append(("Health Check", test_health_endpoint()))
    results.append(("Protección sin auth", test_protected_without_auth()))
    results.append(("API Key válida", test_with_api_key(api_key)))
    results.append(("API Key inválida", test_with_invalid_api_key()))
    results.append(("JWT (Usuario)", test_with_jwt(username, password)))
    
    # Resumen
    print_section("RESUMEN DE PRUEBAS")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        color = COLORS['GREEN'] if result else COLORS['RED']
        print(f"{color}{status}{COLORS['END']} - {test_name}")
    
    print()
    print(f"Total: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print_success("¡Todas las pruebas pasaron! 🎉")
    elif passed > 0:
        print_info("Algunas pruebas pasaron. Revisa los detalles arriba.")
    else:
        print_error("Todas las pruebas fallaron. Revisa la configuración.")
    
    print()
    print_info("Para pruebas completas, ejecuta:")
    print(f"  python {sys.argv[0]} <api_key> <username> <password>")
    print()
    print_info("Ejemplo:")
    print(f"  python {sys.argv[0]} cinco_abc123... admin admin123")
    print()

if __name__ == "__main__":
    main()
