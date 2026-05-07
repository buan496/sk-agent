# Phase 7: Frontend Workbench

Status: first usable frontend version complete.

## Goal

Let the user operate SK Agent workflows without relying only on chat.

## Implemented Views

- Status: backend health, canonical file read status, quick status audit
- Files: repository file tree and file content preview
- Search: keyword search and `/ask`
- Audit: status drift audit result
- Agent: product teardown, framework red team, article publish check
- Patch: reviewable patch draft generation

## Verification

```powershell
docker compose run --rm frontend npm run build
docker compose up -d --build frontend
```

Current result:

```text
Next.js build passed
http://localhost:3000 returns 200
```

## Boundaries

- The frontend does not write to the SK repository.
- The frontend does not call GitHub write APIs.
- The patch page only calls `/patch/draft`.
- The Agent page only calls the phase 6 backend workflow APIs.
