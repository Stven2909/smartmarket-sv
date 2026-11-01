# SmartMarket SV — Frontend (React + PWA)

PWA de SmartMarket SV: comparación de precios, listas de compra, optimización por costo/distancia/
tiempo, historial de precios y chat explicativo del Sistema Experto. Consume únicamente la API de
Laravel; nunca llama al servicio Python directamente.

## Stack

| Componente | Tecnología |
|---|---|
| UI | React 19 + TypeScript |
| Build | Vite 8 |
| Estilos | Tailwind CSS 4 + `globals.css` |
| Gráficas | Recharts |
| Iconos | lucide-react |
| PWA | vite-plugin-pwa (Workbox) |
| Lint | oxlint |

## Requisitos

- Node.js 20+ y npm
- Backend Laravel corriendo en `http://127.0.0.1:8000` (ver `backend-laravel/README.md`)

## Instalación

```bash
npm install
cp .env.example .env.local   # ajustar VITE_API_URL si hace falta
npm run dev
```

La app queda en `http://localhost:5173`.

### Variables de entorno

```dotenv
# URL base de la API de Laravel (sin trailing slash)
VITE_API_URL=http://127.0.0.1:8000/api
```

Si el backend se sirve con Laragon, usá la URL del virtual host, por ejemplo
`http://smartmarket-sv.test:8080/api`. El origen del frontend debe estar permitido en
`backend-laravel/config/cors.php`.

## Scripts

```bash
npm run dev      # servidor de desarrollo con HMR
npm run build    # tsc -b + build de producción + service worker
npm run lint     # oxlint
npm run preview  # servir el build localmente
```

## Estructura

```
src/
├── api/            # cliente HTTP (token Bearer) y endpoints por dominio
├── components/     # vistas y componentes de UI
├── context/        # AuthContext (sesión Sanctum)
├── lib/            # formato, presentación y hook de instalación PWA
├── types/          # tipos de la API y adaptadores al dominio
├── App.tsx         # gate de autenticación y ruteo
└── main.tsx

public/
├── mascota/        # Smarty (versiones .webp usadas en pantalla)
├── manifest.webmanifest
└── pwa-*.png       # iconos de instalación
```

## Funcionalidades

- Login/registro con token Sanctum persistido en `localStorage`.
- Catálogo, buscador universal, categorías y detalle de producto.
- Listas de compra con productos esenciales/opcionales y presupuesto.
- Comparador y optimización según geolocalización del usuario.
- Promociones de la lista, ahorro por categoría e historial de precios con Recharts.
- Badge de recomendación del Sistema Experto + chat explicativo con Smarty.
- PWA instalable (manifest, service worker y prompt de instalación).

## PWA

El manifest es estático (`public/manifest.webmanifest`) y el service worker lo genera
`vite-plugin-pwa` en el build. Las hojas de diseño de la mascota (>1 MB) se excluyen del precache
desde `vite.config.ts`; la app solo consume las versiones `.webp` y `favicon-64.png`.

## Calidad

Actualmente no hay suite de tests de componentes. Como mínimo, antes de integrar cambios:

```bash
npm run lint
npm run build
```

## Documentación

- `../docs/02-arquitectura.md` — arquitectura y ADRs
- `../docs/03-plan-implementacion.md` — roadmap
- `../docs/09-preguntas-chat-experto.md` — temas del chat
- `../docs/CONTEXTO-SISTEMA-EXPERTO.md` — integración con el Sistema Experto
