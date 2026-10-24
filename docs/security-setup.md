# Development API security setup

- Cloudflare Worker: bonch-dev, with D1 binding DB (bonch-dev-db).
- Clerk issuer: fancy-terrier-7430.clerk.accounts.dev.
- Administrator identity: stored as Worker configuration, never trusted from client-side UI.
- API bearer JWT signature is checked against Clerk JWKS (RS256); issuer, expiry, not-before, issued-at, optional authorized party, and administrator subject are checked.
- GET /api/health is public; GET /api/admin/me and GET /api/admin/notes require a valid Clerk session JWT for the configured administrator.
- Non-GET API calls are denied by default. No editing API is exposed yet.
- To initialize the database, run `npx wrangler d1 execute bonch-dev-db --remote --file=db/schema.sql` using Cloudflare credentials, or paste schema.sql into the D1 console.
- The original spreadsheet contains the notes to import later; no notes are committed to public GitHub assets.
- NOTE: test.bonch.fyi currently uses GitHub Pages. Worker API requests must target the bonch-dev.workers.dev hostname until custom domain routing is configured. CORS is intentionally not enabled yet.
- IMPORTANT: Do not treat UI-only restrictions on GitHub Pages as security boundaries.
