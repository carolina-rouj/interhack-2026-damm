# Cómo arrancar el proyecto

## Requisitos previos

- Python 3.12+
- Node.js 18+
- Expo Go instalado en el móvil (o un emulador Android/iOS)

---

## 1. Backend

Desde la raíz del proyecto:

```bash
pip install -r requirements.txt --break-system-packages
uvicorn backend.main:app --reload --port 8000
```

Verifica que funciona:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/zona/list
```

> **Nota:** Si el puerto 8000 está ocupado por otro proceso (comprueba con `lsof -i:8000`), para ese proceso primero. Si es un contenedor Docker: `docker stop <nombre_contenedor>`.

---

## 2. Panel web

```bash
cd frontend
npm install
npm run dev
```

Abre **http://localhost:5173** en el navegador.

El servidor Vite hace proxy automático de `/api` hacia `localhost:8000`, así que el backend tiene que estar corriendo antes.

---

## 3. App móvil

```bash
cd mobile
npm install
npx expo start --clear
```

Escanea el QR con Expo Go desde el móvil.

**Importante:** el móvil y el ordenador tienen que estar en la misma red WiFi. Edita `mobile/src/constants.js` y pon la IP local de tu máquina:

```js
// Ejemplo — sustituye por tu IP
const BASE_URL = 'http://192.168.1.42:8000'
```

Para saber tu IP local: `ip addr show | grep "inet " | grep -v 127`

---

## Orden de arranque recomendado

```
Terminal 1 → backend   (uvicorn ...)
Terminal 2 → frontend  (npm run dev en /frontend)
Terminal 3 → mobile    (npx expo start --clear en /mobile)
```
