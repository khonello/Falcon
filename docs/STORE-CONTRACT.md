# The store contract: what the Falcon store does for the product

*14 Nov 2026. The store is its own project (`store/`, its own session): Next.js, Supabase (PostgreSQL, Auth with Google and email, Edge
Functions), payments by **Paddle**. This document is what the store must do for Falcon, and what Falcon expects of it; neither side changes it
alone. Why it is shaped this way: `docs/SEATS-AND-SETUP.md`.*

## 1. What the store holds

| Thing | What it is |
|---|---|
| **company** | an account bought for one organisation: a name, an owner |
| **member** | a person allowed to act for the company: the owner, or someone the owner invited by email; the owner can remove members. Sign-in with Google or email. |
| **engine** | one Falcon Engine of a company, registered by its setup: id, names, port, its certificate(s), a token it uses to ask for its grants |
| **grant** | "N seats of a kind (admin or worker) for this Engine, from date to date": made from a Paddle purchase; a renewal or an upgrade is a new grant |
| **admin claim** | a one-time permission for one PC to join one Engine as an Admin's workstation, issued to a signed-in member |

Grants are never edited or deleted once issued. A refund or chargeback is recorded in the store; it does not reach the Engine (the user,
14 Nov 2026: bought seats are not re-checked).

## 2. Signed documents

Everything the store tells a Falcon machine that matters is a **signed document**:

```json
{"doc": { ...fields... }, "kid": "store-2026-1", "sig": "<base64 of the Ed25519 signature>"}
```

- **Signed bytes**: the `doc` object as canonical JSON: UTF-8, keys sorted, no insignificant whitespace (`separators=(",", ":")`), no
  floating-point numbers (integers and strings only; times are ISO 8601 strings in UTC with a trailing `Z`).
- **Algorithm**: Ed25519. **`kid`** names the store key that signed it; Falcon carries every public key it trusts, by `kid`
  (`common/store_keys.py`), so the store's key can be replaced later without breaking machines already installed.
- **The private key** lives only in the store's server environment (a Supabase Edge Function secret), never in the browser, the database or the repository.
- Every document has `"kind"` as its first field, and Falcon refuses a document of the wrong kind.

### `company` — the company file (`<company>.falcon`)

```json
{"kind": "company", "company_id": "c_…", "company_name": "Acme Ltd", "engine_id": "e_…",
 "names": ["falcon.internal", "ENG-01"], "port": 7400,
 "certificates": ["-----BEGIN CERTIFICATE-----…"],          // the current one; during a rollover, current and next
 "issued_at": "2026-11-14T10:00:00Z"}
```

Made when an Engine registers, and again whenever its certificates change. The newest one wins (by `issued_at`).

### `grant`

```json
{"kind": "grant", "grant_id": "g_…", "company_id": "c_…", "engine_id": "e_…", "role": "worker", "seats": 20,
 "valid_from": "2026-11-14T00:00:00Z", "valid_until": "2027-11-14T00:00:00Z", "paddle_ref": "sub_…", "issued_at": "…"}
```

### `admin_claim`

```json
{"kind": "admin_claim", "claim_id": "a_…", "company_id": "c_…", "engine_id": "e_…", "member_email": "kofi@acme.com",
 "hostname": "IT-01", "hardware_id": "…", "issued_at": "…", "expires_at": "…"}            // expires 10 minutes after issue
```

The Engine accepts each `claim_id` once.

## 3. The API (HTTPS, JSON)

### Sign-in from a setup (Engine setup, Admin setup)

OAuth 2.0 authorization code with PKCE (RFC 7636), loopback redirect (RFC 8252), the way desktop applications sign in:

1. The setup listens on `http://127.0.0.1:<random port>/callback` and opens the browser at
   `GET /oauth/authorize?client_id=falcon-setup&redirect_uri=…&state=…&code_challenge=…&code_challenge_method=S256`.
2. The person signs in (Google or email) on the store's own page, and the store redirects to the callback with `code` and `state`.
3. The setup exchanges it: `POST /oauth/token {grant_type: authorization_code, code, redirect_uri, code_verifier}` -> `{access_token, expires_in}`
   (short-lived; never stored by the setup after it finishes).

### For the Engine setup

- `GET /api/me/companies` -> the companies the signed-in member belongs to (a new owner names theirs: `POST /api/companies {name}`).
- `POST /api/companies/{company_id}/engines` `{names, port, certificate}` -> `{engine_id, engine_token, company: <signed company>, grants: [<signed grant>, …]}`.
  `engine_token` is a long random secret, shown once, kept by the Engine in its protected data folder.

### For the Engine, while it runs (with `Authorization: Bearer <engine_token>`)

- `GET /api/engines/{engine_id}/grants` -> `{grants: [<signed grant>, …]}`: every grant ever made for this Engine. The Engine adds the ones it
  does not have. Asked once a day and when an Admin asks.
- `PUT /api/engines/{engine_id}/certificates` `{certificates: [current, next]}` -> `{company: <signed company>}`. Used for renewal (the
  Engine sends its current and its next certificate) and for a change of names.
- `POST /api/engines/{engine_id}/usage` `{admin_in_use, worker_in_use}` -> `{}`: counts only, so the store can show them on the account
  page; nothing about machines or people.

### For the Admin setup (signed in)

- `GET /api/me/engines` -> `[{engine_id, company_name, names, admin_seats_free_hint}]` (the hint is from the last usage report; the Engine decides).
- `POST /api/engines/{engine_id}/admin-claims` `{hostname, hardware_id}` -> `{claim: <signed admin_claim>, company: <signed company>}`.
  Refused unless the signed-in person is a member of that Engine's company.

### Public

- `GET /downloads/{falcon-engine-setup.exe | falcon-admin-setup.exe | falcon-worker-setup.exe}`: the signed setups, the same for everyone.
- `GET /.well-known/falcon-store-keys.json` -> `{keys: [{kid, ed25519_public_key (base64)}]}`, for reference only (Falcon trusts the keys built into it, not this).

## 4. Paddle

- Products: an **Admin seat** and a **Worker seat**, sold as yearly subscriptions with a quantity.
- On Paddle's `subscription.created` / `subscription.updated` (quantity up) / renewal webhooks, the store issues a **grant** for the company's
  Engine (the purchase names it; a company with one Engine has it chosen for it). The webhook's signature is checked with Paddle's secret.
- Before relying on Paddle: confirm with Paddle that it pays out to Ghana (bank transfer or Payoneer in USD) and accepts the product.

## 5. What Falcon does with all this

- Checks every signature itself, with the keys built into it, with no internet.
- Keeps every grant verbatim and checks it each time it reads one.
- Asks for grants only to find new ones; never re-checks or removes one it has.
- Never sends the store anything about machines, people, files or activity: only its names, port, certificates, and two seat counts.

## 6. Testing without the store

`scripts/store_stub.py` serves this same API on localhost with a test signing key (`kid` `test-1`), which Falcon trusts only when
`FALCON_STORE_TEST_KEY=1` is set (the test suite and drills). A real build never trusts it.
