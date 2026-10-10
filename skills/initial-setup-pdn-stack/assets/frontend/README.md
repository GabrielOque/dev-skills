# {{PROJECT_NAME}} — frontend

Next.js (App Router) + React + TypeScript + Redux Toolkit, talking to the
Django backend with JWT sessions.

## Getting started

```bash
cp .env.example .env.local     # backend URL
pnpm install
pnpm dev                       # http://localhost:3000
```

| Command | What it does |
| --- | --- |
| `pnpm dev` | Development server |
| `pnpm lint` | ESLint |
| `pnpm exec tsc --noEmit` | Type check |
| `pnpm build` | Production build |

`NEXT_PUBLIC_*` variables are inlined at build time: each environment
(test, production) builds with its own values.

Structure, session handling and conventions are in [`CLAUDE.md`](./CLAUDE.md).
