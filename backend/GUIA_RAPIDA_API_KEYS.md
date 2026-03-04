# Guía Rápida - Sistema de API Keys

## 🚀 Inicio Rápido

### Paso 1: Crear una API Key

```bash
cd backend
python manage.py create_apikey "Mi Aplicación Externa"
```

Guarda la API Key que te muestra. Ejemplo:
```
cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u
```

### Paso 2: Probar la API Key

```bash
# Windows (PowerShell)
$headers = @{ "X-API-Key" = "cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u" }
Invoke-WebRequest -Uri "http://localhost:8000/operaciones/actividades/" -Headers $headers

# Linux/Mac (curl)
curl -H "X-API-Key: cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u" \
     http://localhost:8000/operaciones/actividades/
```

---

## 📋 Gestión de API Keys

### Crear con opciones avanzadas

```bash
python manage.py create_apikey "App Producción" \
    --description "Sistema de inventario externo" \
    --email "admin@empresa.com" \
    --rate-limit 10000 \
    --allowed-ips "203.0.113.50, 203.0.113.51" \
    --expires-days 180
```

### Ver todas las API Keys

```bash
python manage.py list_apikeys
```

### Ver solo las activas

```bash
python manage.py list_apikeys --active-only
```

### Desactivar una API Key

```bash
python manage.py revoke_apikey 1
```

### Reactivar una API Key

```bash
python manage.py activate_apikey 1
```

### Eliminar permanentemente

```bash
python manage.py revoke_apikey 1 --permanent
```

---

## 🔌 Integración en Aplicaciones

### Python con requests

```python
import requests
import os

API_KEY = os.getenv('API_KEY', 'cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u')
BASE_URL = 'http://localhost:8000'

headers = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
}

# GET
response = requests.get(f'{BASE_URL}/operaciones/actividades/', headers=headers)
print(response.json())

# POST
data = {
    'nombre': 'Nueva actividad',
    'descripcion': 'Desde API externa'
}
response = requests.post(
    f'{BASE_URL}/operaciones/actividades/',
    json=data,
    headers=headers
)
print(response.json())
```

### JavaScript (Node.js) con axios

```javascript
const axios = require('axios');

const API_KEY = process.env.API_KEY || 'cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u';
const BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
  }
});

// GET
async function getActividades() {
  try {
    const response = await api.get('/operaciones/actividades/');
    console.log(response.data);
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

// POST
async function createActividad(data) {
  try {
    const response = await api.post('/operaciones/actividades/', data);
    console.log('Creada:', response.data);
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

getActividades();
```

### JavaScript (Browser) con fetch

```javascript
const API_KEY = 'cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u';
const BASE_URL = 'http://localhost:8000';

// GET
fetch(`${BASE_URL}/operaciones/actividades/`, {
  headers: {
    'X-API-Key': API_KEY
  }
})
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));

// POST
fetch(`${BASE_URL}/operaciones/actividades/`, {
  method: 'POST',
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    nombre: 'Nueva actividad',
    descripcion: 'Desde browser'
  })
})
  .then(response => response.json())
  .then(data => console.log('Creada:', data))
  .catch(error => console.error('Error:', error));
```

### PHP con cURL

```php
<?php

$apiKey = getenv('API_KEY') ?: 'cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u';
$baseUrl = 'http://localhost:8000';

// GET
function getActividades($baseUrl, $apiKey) {
    $ch = curl_init("$baseUrl/operaciones/actividades/");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "X-API-Key: $apiKey",
        "Content-Type: application/json"
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode === 200) {
        return json_decode($response, true);
    }
    return null;
}

// POST
function createActividad($baseUrl, $apiKey, $data) {
    $ch = curl_init("$baseUrl/operaciones/actividades/");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "X-API-Key: $apiKey",
        "Content-Type: application/json"
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode === 201) {
        return json_decode($response, true);
    }
    return null;
}

$actividades = getActividades($baseUrl, $apiKey);
print_r($actividades);
```

### C# con HttpClient

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public class ApiClient
{
    private readonly HttpClient _client;
    private readonly string _apiKey;
    private readonly string _baseUrl;

    public ApiClient(string apiKey, string baseUrl = "http://localhost:8000")
    {
        _apiKey = apiKey;
        _baseUrl = baseUrl;
        _client = new HttpClient();
        _client.DefaultRequestHeaders.Add("X-API-Key", _apiKey);
    }

    public async Task<string> GetActividades()
    {
        var response = await _client.GetAsync($"{_baseUrl}/operaciones/actividades/");
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync();
    }

    public async Task<string> CreateActividad(object data)
    {
        var json = JsonSerializer.Serialize(data);
        var content = new StringContent(json, Encoding.UTF8, "application/json");
        
        var response = await _client.PostAsync(
            $"{_baseUrl}/operaciones/actividades/",
            content
        );
        
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync();
    }
}

// Uso
var client = new ApiClient("cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u");
var actividades = await client.GetActividades();
Console.WriteLine(actividades);
```

---

## 🛡️ Seguridad

### Variables de entorno (recomendado)

Nunca hardcodees las API Keys. Usa variables de entorno:

**Linux/Mac (.bashrc o .zshrc)**
```bash
export API_KEY="cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u"
export API_BASE_URL="http://localhost:8000"
```

**Windows (PowerShell)**
```powershell
$env:API_KEY = "cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u"
$env:API_BASE_URL = "http://localhost:8000"
```

**Archivo .env**
```bash
API_KEY=cinco_xp8KLm3Qw9rYvN2jHbTfZa1cDgEsW5u
API_BASE_URL=http://localhost:8000
```

---

## 🔍 Troubleshooting

### Error: "API Key inválida"

✅ Verifica que la key sea correcta y comience con `cinco_`  
✅ Verifica que la key esté activa: `python manage.py list_apikeys`  
✅ Verifica que estés usando el header correcto: `X-API-Key`

### Error: "IP no autorizada"

✅ Tu IP no está en la lista de permitidas  
✅ Actualiza con: `python manage.py create_apikey ... --allowed-ips "tu.ip.aqui"`

### Error: "Rate limit excedido"

✅ Superaste el límite de requests/hora  
✅ Espera o aumenta el límite creando una nueva key

### Error: "API Key expirada"

✅ La key llegó a su fecha de expiración  
✅ Crea una nueva key o actualiza la fecha desde el admin

---

## 📊 Monitoreo

### Ver logs de seguridad

```bash
tail -f backend/logs/security.log
```

### Desde el admin de Django

1. Accede a: http://localhost:8000/admin/
2. Ve a "Security" → "API Keys"
3. Verás: estado, último uso, rate limit, etc.

---

## ✅ Checklist de Implementación

- [x] Modelo APIKey creado
- [x] Autenticación por API Key implementada
- [x] Permisos configurados
- [x] Rate limiting activado
- [x] Endpoints restringidos
- [x] Comandos de gestión creados
- [x] Admin de Django configurado
- [x] Documentación lista
- [x] Migraciones aplicadas

---

## 🎯 Próximos Pasos

1. **Crear tu primera API Key de producción**
   ```bash
   python manage.py create_apikey "Producción" --rate-limit 50000 --expires-days 365
   ```

2. **Integrar en tu aplicación externa**
   - Usa los ejemplos de código de arriba
   - Guarda la API Key en variables de entorno

3. **Monitorear uso**
   ```bash
   python manage.py list_apikeys
   ```

4. **Configurar restricciones adicionales** (opcional)
   - IPs permitidas
   - Rate limits personalizados
   - Fechas de expiración

---

## 📞 Soporte

Para crear, revocar o gestionar API Keys, contacta al administrador del sistema.

**Documentación completa:** Ver `API_KEYS_README.md`
