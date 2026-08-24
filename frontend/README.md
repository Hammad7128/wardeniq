# WardenIQ Frontend

Production-oriented React + Vite + Tailwind frontend for WardenIQ.

## Development

```bash
npm ci
npm run dev
```

The Vite dev server proxies `/api` to the configured FastAPI backend in `vite.config.js`.

## Quality checks

```bash
npm run lint
npm run build
```

## Architecture

Read [`ARCHITECTURE.md`](./ARCHITECTURE.md) before adding or moving frontend code.

Key rules:

- Put screen code under `src/features/<feature>/`.
- Put reusable product-wide components under `src/components/`.
- Put permanent navigation/chrome under `src/layouts/`.
- Use Tailwind utilities for new React UI.
- Do not add new styles to `src/styles/compat/`.
- Do not create another global runtime file.
- `src/compat/runtime/controllers/` preserves existing behavior while screens are progressively converted from imperative DOM rendering to React state/rendering.
