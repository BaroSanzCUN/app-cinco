
# 📘 Guía paso a paso: Entorno virtual y ejecución de Django

Este documento describe **cómo crear y usar un entorno virtual en Python**, **cómo ejecutar un proyecto Django**, y **los comandos básicos necesarios**, con **énfasis explícito en NO ejecutar migraciones**.

---

## 1️⃣ Requisitos previos

Antes de comenzar, asegúrate de tener instalado:

- Python **3.11.9**
- `pip` (incluido normalmente con Python)
- Acceso a terminal (CMD, PowerShell, Git Bash o terminal Linux/macOS)

Verifica versiones:

```bash
python --version
pip --version
```

---

## 2️⃣ Crear un entorno virtual (virtualenv)

El entorno virtual permite aislar las dependencias del proyecto y evitar conflictos con otros proyectos o con el sistema.

### 📁 Ubicación recomendada

Ubícate en la **raíz del proyecto Django** (donde estará `manage.py`):

```bash
cd ruta/del/proyecto
```

### ▶️ Crear el entorno virtual

```bash
python -m venv env
```

Esto creará una carpeta llamada `env/` que contendrá el entorno virtual.

> 📌 **Convención**: se recomienda usar el nombre `env` o `.env`

---

## 3️⃣ Activar el entorno virtual

### 🪟 Windows (CMD / PowerShell)

```bash
env\Scripts\activate
```

### 🐧 Linux / macOS

```bash
source env/bin/activate
```

Si el entorno está activo verás algo como:

```text
(env) ruta/del/proyecto
```

---

## 4️⃣ Instalar dependencias del proyecto

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

## 5️⃣ Ejecutar el servidor Django

⚠️ **IMPORTANTE**: En este paso **NO se deben correr migraciones** (`migrate`, `makemigrations`).

### ▶️ Ejecutar servidor de desarrollo

```bash
python manage.py runserver
```

Por defecto el servidor estará disponible en:

```
http://127.0.0.1:8000/
```

Para usar otro puerto:

```bash
python manage.py runserver 8080
```

---

## 6️⃣ Comandos básicos de Django (uso seguro)

### ✔️ Comandos permitidos

```bash
python manage.py runserver
python manage.py check
python manage.py showmigrations
python manage.py createsuperuser  # SOLO si el proyecto lo permite
```

### ❌ Comandos que **NO debes ejecutar**

🚫 **NO ejecutar bajo ninguna circunstancia**:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py flush
```

Estos comandos modifican la base de datos y **pueden romper un entorno existente**, especialmente en proyectos heredados o compartidos.

---

## 7️⃣ Verificar configuración sin afectar la base de datos

Para validar que el proyecto está bien configurado:

```bash
python manage.py check
```

Para ver migraciones existentes **sin ejecutarlas**:

```bash
python manage.py showmigrations
```

---

## 8️⃣ Crear una nueva app
Cuando se necesite agregar nuevos modulos al proyecto, se puede crear una nueva app *(ten en cuenta que el nombre de la app debe ser unico dentro del proyecto y primero se debe crear la carpeta dentro de apps)*

```bash
python manage.py startapp nombre_de_la_app apps/nombre_de_la_carpeta
```


---

## 8️⃣ Desactivar el entorno virtual

Cuando termines de trabajar:

```bash
deactivate
```

---

## 9️⃣ Problemas comunes

### ❌ `python` no reconocido

- Reinstala Python y marca **"Add Python to PATH"**

### ❌ Error al activar el entorno en PowerShell

Ejecuta como administrador:

```powershell
Set-ExecutionPolicy RemoteSigned
```

### ❌ Django no encontrado

Verifica que esté instalado en el entorno:

```bash
pip install django
```

---

## 🔒 Buenas prácticas

- Nunca ejecutes Django sin activar el entorno virtual
- No corras migraciones sin autorización
- Mantén `env/` fuera del control de versiones (`.gitignore`)
- Usa `requirements.txt` para controlar dependencias

---

## ✅ Resumen rápido

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

📌 **Este README está pensado para entornos controlados donde la base de datos ya existe y NO debe ser alterada.**

