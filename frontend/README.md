# 📘 Guía paso a paso: Instalación y ejecución de un proyecto Next.js

Este documento describe **cómo preparar el entorno**, **instalar dependencias**, y **ejecutar un proyecto Next.js** de forma segura, pensado para **proyectos grandes o migraciones desde PHP/JS vanilla**, sin alterar configuraciones sensibles.

---

## 1️⃣ Requisitos previos

Antes de comenzar, asegúrate de tener instalado:

- **Node.js LTS (18.x o superior)**
- **npm** (incluido con Node.js) o **pnpm / yarn**
- Acceso a terminal (CMD, PowerShell, Git Bash o terminal Linux/macOS)

Verifica versiones:

```bash
node --version
npm --version
```

> 📌 Recomendado: usar siempre versiones **LTS** para entornos corporativos

---

## 2️⃣ Estructura base esperada del proyecto

Ubícate en la raíz del proyecto (donde exista `package.json`):

```text
frontend/
├── app/        # App Router (Next 13+)
│   ├── layout.tsx
│   └── page.tsx
├── public/
├── package.json
├── next.config.js
└── .env.local
```

---

## 3️⃣ Instalación de dependencias

Desde la raíz del proyecto:

### ▶️ Usando npm

```bash
npm install
```

### ▶️ Usando pnpm (si aplica)

```bash
pnpm install
```

Esto instalará todas las dependencias definidas en `package.json`.

---

## 4️⃣ Variables de entorno

Las variables de entorno **NO deben hardcodearse**.

Archivo recomendado:

```text
.env.local
```

Ejemplo:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
NEXT_PUBLIC_APP_NAME=MiAplicacion
```

> ⚠️ `NEXT_PUBLIC_` expone la variable al navegador

---

## 5️⃣ Ejecutar el servidor Next.js (desarrollo)

### ▶️ Modo desarrollo

```bash
npm run dev
```

El proyecto estará disponible en:

```
http://localhost:3000
```

---

## 6️⃣ Scripts comunes en Next.js

Definidos en `package.json`:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "typecheck": "tsc --noEmit",
    "format": "prettier --write \"**/*.{ts,tsx,js,jsx,css,md,json,yml,yaml}\"",
    "format:check": "prettier --check \"**/*.{ts,tsx,js,jsx,css,md,json,yml,yaml}\"",
    "test": "echo \"No tests configured yet\""
  }
}
```

### ✔️ Scripts permitidos

```bash
npm run dev
npm run lint
npm run typecheck
```

### ⚠️ Scripts a usar con precaución

```bash
npm run build
npm run start
```

> Estos comandos están pensados para **producción**

---

## 7️⃣ Build del proyecto (NO obligatorio para desarrollo)

```bash
npm run build
```

Este comando:

- Valida tipos (TypeScript)
- Optimiza el bundle
- Puede fallar si existen errores de tipado

---

## 8️⃣ Ejecución en modo producción

Después del build:

```bash
npm run start
```

> Normalmente se ejecuta detrás de **Nginx o Apache (proxy reverso)**

---

## 9️⃣ Problemas comunes

### ❌ `node` o `npm` no reconocido

- Reinstala Node.js
- Marca **"Add to PATH"** durante la instalación

### ❌ Error con dependencias

```bash
rm -rf node_modules
rm package-lock.json
npm install
```

### ❌ Variables de entorno no reconocidas

- Reinicia el servidor (`Ctrl + C` → `npm run dev`)

---

## 🔒 Buenas prácticas

- No subir `.env.local` al repositorio
- Usar `eslint` y `lint` en desarrollo
- Ejecutar `typecheck` y `format:check` antes de abrir un PR
- Mantener `node_modules/` fuera del control de versiones
- No ejecutar `build` innecesariamente en desarrollo
- Centralizar el consumo de APIs (services / fetch wrappers)

## ✅ Hooks locales

El proyecto incluye un hook de pre-commit con `husky` + `lint-staged` para:

- formatear con Prettier
- corregir lint basico en archivos staged

---

## ✅ Checklist antes de commit

Flujo corto:

```bash
npm run lint
npm run typecheck
git add .
git commit -m "mensaje"
```

Notas:

- El hook de pre-commit ejecuta `lint-staged` automaticamente.
- Si queres validar formato antes del commit: `npm run format:check`.

---

## ✅ Resumen rápido

```bash
# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm run dev

# Build (solo si aplica)
npm run build

# Producción
npm run start
```

---

📌 **Este README está pensado para proyectos Next.js grandes, modulares y en proceso de migración desde sistemas legacy.**
