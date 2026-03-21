# ResumeForge Web Frontend

SvelteKit web client for ResumeForge. Communicates with the engine via REST API and SSE streaming.

**Stack:** SvelteKit 2 · Svelte 5 Runes · TailwindCSS 4 · TypeScript

---

## Prerequisites

- Node.js 20+ — [nodejs.org](https://nodejs.org)
- ResumeForge engine running at `localhost:8080`

---

## Setup

```bash
cd web
npm install
cp .env.example .env    # optional — set VITE_ENGINE_URL if engine is not at localhost:8080
```

---

## Non-Interactive Testing

```bash
npm run check    # TypeScript + Svelte 5 type check (svelte-check)
```

---

## Interactive Testing

```bash
npm run dev      # development server at http://localhost:5173
```

Routes:
| Route | Description |
|-------|-------------|
| `/` | Dashboard — recent builds, quick actions, engine status |
| `/builder` | Build resume — template picker, format, job selector, SSE progress |
| `/builder/preview` | Preview last built resume (PDF iframe / Markdown) |
| `/analyze` | Run analysis — ATS score, per-analyzer results, findings |
| `/data/[section]` | View and edit resume sections (experience, skills, education...) |
| `/templates` | Template gallery with PDF preview |
| `/jobs` | Saved job descriptions — add, view, delete |
| `/settings` | Config — AI provider, engine URL, style preferences |

---

## Production Build

```bash
npm run build
npm run preview    # preview production build locally
```

---

## Engine URL

The engine URL is read from the `VITE_ENGINE_URL` environment variable (default: `http://localhost:8080`).

```env
# .env
VITE_ENGINE_URL=http://localhost:8080
```

All API calls go through `src/lib/api/engine.ts` — never inline fetch.

---

## Code Conventions

- **Svelte 5 Runes only:** `$state()`, `$derived()`, `$effect()`, `$props()` — no legacy stores
- **TailwindCSS** for all styling — no custom CSS unless layout requires it
- **Engine client** — all fetch calls in `src/lib/api/engine.ts`
- **Types** — TypeScript interfaces in `src/lib/api/types.ts`
