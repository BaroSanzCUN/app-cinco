
# ðŸ“˜ GuÃ­a paso a paso: Entorno virtual y ejecuciÃ³n de Django

Este documento describe **cÃ³mo crear y usar un entorno virtual en Python**, **cÃ³mo ejecutar un proyecto Django**, y **los comandos bÃ¡sicos necesarios**, con **Ã©nfasis explÃ­cito en NO ejecutar migraciones**.

---

## 1ï¸âƒ£ Requisitos previos

Antes de comenzar, asegÃºrate de tener instalado:

- Python **3.11.9**
- `pip` (incluido normalmente con Python)
- Acceso a terminal (CMD, PowerShell, Git Bash o terminal Linux/macOS)

Verifica versiones:

```bash
python --version
pip --version
```

---

## 2ï¸âƒ£ Crear un entorno virtual (virtualenv)

El entorno virtual permite aislar las dependencias del proyecto y evitar conflictos con otros proyectos o con el sistema.

### ðŸ“ UbicaciÃ³n recomendada

UbÃ­cate en la **raÃ­z del proyecto Django** (donde estarÃ¡ `manage.py`):

```bash
cd ruta/del/proyecto
```

### â–¶ï¸ Crear el entorno virtual

```bash
python -m venv env
```

Esto crearÃ¡ una carpeta llamada `env/` que contendrÃ¡ el entorno virtual.

> ðŸ“Œ **ConvenciÃ³n**: se recomienda usar el nombre `env` o `.env`

---

## 3ï¸âƒ£ Activar el entorno virtual

### ðŸªŸ Windows (CMD / PowerShell)

```bash
env\Scripts\activate
```

### ðŸ§ Linux / macOS

```bash
source env/bin/activate
```

Si el entorno estÃ¡ activo verÃ¡s algo como:

```text
(env) ruta/del/proyecto
```

---

## 4ï¸âƒ£ Instalar dependencias del proyecto

Si el proyecto tiene un archivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

Actualizar `requirements.txt`
```bash
pip freeze > requirements.txt
```


Verifica dependencias instaladas:

```bash
pip list
```

---

## 5ï¸âƒ£ Ejecutar el servidor Django

âš ï¸ **IMPORTANTE**: En este paso **NO se deben correr migraciones** (`migrate`, `makemigrations`).

### ▶️ Inicio rápido desde terminal de VS Code (recomendado)

Usa una ruta **genérica** a la carpeta `backend` de tu clonado local:

```powershell
cd "ruta\a\tu\repositorio\app-cinco\backend"
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Ejemplo (solo referencia local):

```powershell
cd "ruta\a\tu\repositorio\\app-cinco\backend"
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Si ya activaste el entorno virtual, puedes usar:

```powershell
python manage.py runserver 127.0.0.1:8000
```

### â–¶ï¸ Ejecutar servidor de desarrollo

```bash
python manage.py runserver
```

Por defecto el servidor estarÃ¡ disponible en:

```
http://127.0.0.1:8000/
```

Para usar otro puerto:

```bash
python manage.py runserver 8080
```

---

## 6ï¸âƒ£ Comandos bÃ¡sicos de Django (uso seguro)

### âœ”ï¸ Comandos permitidos

```bash
python manage.py runserver
python manage.py check
python manage.py showmigrations
python manage.py createsuperuser  # SOLO si el proyecto lo permite
```

### âŒ Comandos que **NO debes ejecutar**

ðŸš« **NO ejecutar bajo ninguna circunstancia**:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py flush
```

Estos comandos modifican la base de datos y **pueden romper un entorno existente**, especialmente en proyectos heredados o compartidos.

---

## 7ï¸âƒ£ Verificar configuraciÃ³n sin afectar la base de datos

Para validar que el proyecto estÃ¡ bien configurado:

```bash
python manage.py check
```

Para ver migraciones existentes **sin ejecutarlas**:

```bash
python manage.py showmigrations
```

---

## 8ï¸âƒ£ Crear una nueva app
Cuando se necesite agregar nuevos modulos al proyecto, se puede crear una nueva app *(ten en cuenta que el nombre de la app debe ser unico dentro del proyecto y primero se debe crear la carpeta dentro de apps)*

```bash
python manage.py startapp nombre_de_la_app apps/nombre_de_la_carpeta
```


---

## 8ï¸âƒ£ Desactivar el entorno virtual

Cuando termines de trabajar:

```bash
deactivate
```

---

## 9ï¸âƒ£ Problemas comunes

### âŒ `python` no reconocido

- Reinstala Python y marca **"Add Python to PATH"**

### âŒ Error al activar el entorno en PowerShell

Ejecuta como administrador:

```powershell
Set-ExecutionPolicy RemoteSigned
```

### âŒ Django no encontrado

Verifica que estÃ© instalado en el entorno:

```bash
pip install django
```

---

## ðŸ”’ Buenas prÃ¡cticas

- Nunca ejecutes Django sin activar el entorno virtual
- No corras migraciones sin autorizaciÃ³n
- MantÃ©n `env/` fuera del control de versiones (`.gitignore`)
- Usa `requirements.txt` para controlar dependencias

---

## âœ… Resumen rÃ¡pido

```bash
# Crear entorno
python -m venv env

# Activar
source env/bin/activate  # Linux/macOS
env\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python manage.py runserver

# Salir
deactivate
```

---

ðŸ“Œ **Este README estÃ¡ pensado para entornos controlados donde la base de datos ya existe y NO debe ser alterada.**



