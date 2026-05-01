# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.
Provides a professional REST API wrapping Clipfly.ai and GeminiGen.ai AI services.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)
- **HTTP client**: axios + form-data (for proxying to external AI APIs)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)

## API Endpoints

### Health
- `GET /api/healthz` — server health check

### Clipfly (AI Image & Video)
- `POST /api/clipfly/register` — auto-register a Clipfly account, returns token
- `POST /api/clipfly/upload` — upload base64 image to Clipfly storage
- `POST /api/clipfly/text-to-image` — generate image from text prompt
- `POST /api/clipfly/image-to-image` — transform image with prompt
- `POST /api/clipfly/image-combination` — combine multiple images
- `POST /api/clipfly/text-to-video` — generate video from text prompt
- `POST /api/clipfly/image-to-video` — generate video from image
- `GET  /api/clipfly/image-status?queue_id=&token=` — poll image task status
- `GET  /api/clipfly/video-status?queue_id=&token=` — poll video task status

### GeminiGen (AI Video — Veo/Grok)
- `POST /api/geminigen/token` — activate device and get access token
- `POST /api/geminigen/video-gen` — generate video (veo_fast, veo_lite, grok)
- `GET  /api/geminigen/status/:uuid?access_token=` — check video task status

## Testing

Run `python3 test_api.py` to test all endpoints.
Set BASE_URL at the top of the file to point to your deployment URL.

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.
