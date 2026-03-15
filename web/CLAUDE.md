# Web Frontend Client

SvelteKit application. Communicates with engine via REST API + SSE.

## Key directories
- `src/routes/` — SvelteKit file-based pages
- `src/lib/components/` — Reusable Svelte components
- `src/lib/api/engine.ts` — Typed engine API client (all fetch calls here)
- `src/lib/api/types.ts` — TypeScript types matching engine OpenAPI schema

## Rules
- ALL engine API calls go through `src/lib/api/engine.ts` — never inline fetch
- Use Svelte 5 Runes: `$state()`, `$derived()`, `$effect()` — NOT legacy stores
- SSE handled via `engine.streamBuild()` which returns an async iterable
- Engine base URL read from `VITE_ENGINE_URL` env var (defaults to localhost:8080)
- TailwindCSS only — no custom CSS unless absolutely necessary
- Run type check with: `npm run check`
