# Public Hosting Without Replacing the Local App

## Boundaries

The original `uv run job-agent ui` and Cloudflare sharing remain available.
`job_agent/hosting/` exports a second deployment, never moves or deletes the
original environment, documents, results, or logged-in browser profiles.

| Component | Public deployment | Existing local app |
| --- | --- | --- |
| Hosting | Vercel static files + one Python function | Laptop Python server / optional Cloudflare |
| Profile and history | Per-tab browser RAM; reset on reload | Personal files under `result/` |
| Deterministic execution | Stateless request using the same Python workflows | Existing `WorkspaceService` |
| Personal model/search keys | Never exported, never callable | Existing optional owner settings |
| Portal login / MFA / saving | Own-PC connector, explicit review | Dedicated local browser |
| Supabase | Not connected; no database needed | Not required |

Standard JSON upload/download, source review, manual-posting filtering,
verbatim resume reordering, and reviewed company-form conversion are available.
Live job scraping, cloud portal browsers, mobile-only portal saving and automatic
application submission are not added by hosting migration.

## Preserve and Export

Run in `resum/` (PowerShell or Linux):

```sh
python -m job_agent.hosting.build --backup
```

The private ZIP under `result/hosting/backups/` includes the current source,
instructions, dependency manifests and the existing `.env`, if present.
**Never upload this ZIP.** Personal documents/results/browser profiles remain in
their original directories. `.venv` itself is not copied: recreate the existing
environment with `uv sync --locked --extra browser`. Keep the original `.env`
only in the private environment; it is not a public deployment dependency.

The separately printed public directory contains only allowlisted runtime code,
static UI, a blank profile template, a code-only own-PC connector ZIP and a minimal
`httpx==0.28.1` dependency. No `knowledge/`, `more_info/`, results, environment keys,
browser sessions, agent settings or existing resume is copied to it.
Existing nonempty export directories are refused rather than overwritten.

An optional public contact can be supplied with `--privacy-contact`.
That value is intentionally public; do not use a private address without consent.

## Local Public-Build Preview

```sh
python -m job_agent.hosting.build --output result/hosting/my-public-build
python -m job_agent.hosting.preview result/hosting/my-public-build --port 8790
```

Open `http://127.0.0.1:8790`. This is the separate public UI, not the existing
personal workspace. Choose another unused port if necessary.

## Vercel

Verified production URL: <https://job-agent-resume-web.vercel.app>.
This is a stable Vercel production alias, not the temporary Cloudflare tunnel.
The original server does not have to stay on for the public web to work.
Own-PC portal automation still requires the user's connector running locally.

The exported API contains an explicit top-level `handler` class: Vercel's static
entrypoint detection does not accept an import-only handler file in this setup.
The production build uses standard `functions` + `public` output, not legacy builds.

Use only the exported directory, not the parent monorepo or a private backup:

```sh
vercel login
vercel link --yes --project job-agent-resume-web --scope YOUR_HOBBY_TEAM --cwd result/hosting/my-public-build
vercel deploy --dry --json --scope YOUR_HOBBY_TEAM --cwd result/hosting/my-public-build
vercel deploy --prod --yes --scope YOUR_HOBBY_TEAM --cwd result/hosting/my-public-build
```

Inspect the dry-run file list before uploading. Vercel may create `.env.local`
with an OIDC token while linking; `.env*` is excluded from upload.
The function receives JSON POSTs only from the same origin, accepts at most 2MB,
does not load dotenv, rejects every model/search provider, and cleans its
request workspace in `finally`. No application body logs or persisted profile
API exist. Results return to the requesting tab, with at most 20 / about 10MB
of recent records retained there. Browser profile operations use no network.
Do not add model/search keys or private resume files to Vercel settings.

Headers disable content sniffing/framing and restrict scripts/connections to the
same origin. Application session cookies and automatic localStorage/IndexedDB
resume persistence are not used. Hosting-provider access logs, OS swap/dumps and
browser recovery are not an infrastructure-wide no-retention guarantee.

After publication verify the unauthenticated production URL, actual `/api/run`,
uploads, downloads, per-tab isolation, no paid-provider calls, responsive layout,
and own-PC handoff from the real HTTPS origin. Do not equate local preview tests
with a successful Vercel runtime deployment.

## Own-PC Connector

Use the command shown on the public site's platform-connection page. It includes
the exact deployed origin, which replaces the old temporary Cloudflare origin:

```sh
uv sync --extra browser
uv run job-agent ui --port 8780 --handoff-origin https://YOUR-PRODUCTION-HOST
```

Public web transmission consent and a separate local import approval are required.
Only the profile travels to the user's PC. Passwords, OTPs, cookies and API tokens
stay there. Direct portal login/MFA and selected-field/save review remain required.

## GitHub and Free Tiers

`deploy/github/vercel-workflow.yml` is a manual-run CI template for the parent
monorepo, scoped to exporting `resum/`. It is **not activated** merely by storing
this file. Install it as `.github/workflows/resume-public.yml` after review, then
run it against `job_agent`. The build needs only Python's standard library.
It uploads a code-only artifact with three-day retention. With deployment
credentials absent it never deploys. Configure `VERCEL_TOKEN`, `VERCEL_ORG_ID`,
and `VERCEL_PROJECT_ID` as GitHub secrets only when CI deployment is desired.
Never put personal model keys, `.env`, private snapshots or resumes in artifacts.

The initial CLI deployment does not imply GitHub automatic deployment is connected.
The direct GitHub connection attempted by Vercel can require separately authorizing
the Vercel GitHub integration. Do not connect the raw monorepo with default settings:
its private local files and full LLM dependencies are not this export's environment.
No other project branches are merged for deployment.

Initial verified state: CLI 63.1.0 authenticated and Hobby production deployed;
Codex Vercel plugin installed at user scope; global shared MCP endpoint registered,
but its separate OAuth / authenticated tool verification is not complete. The
current session has not reloaded the newly installed plugin. No paid AI Gateway
was enabled. Direct GitHub integration failed to connect during project linking;
the workflow template remains inactive. Existing local deployment is preserved.

Vercel Hobby is for personal noncommercial use and has quotas. No paid plan,
database, AI Gateway, paid API or custom domain purchase is necessary for this
version. GitHub Actions also has plan-dependent limits; manual triggers avoid
unnecessary runs. Supabase remains optional for a future, separately approved
account/settings feature and is not a place for portal credentials or resume facts.

Sources:

- [Vercel Hobby](https://vercel.com/docs/plans/hobby)
- [Python API functions](https://vercel.com/docs/functions/runtimes/python/api-directory)
- [Vercel GitHub deployment](https://vercel.com/docs/git/vercel-for-github)
- [GitHub Actions billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions)
- [Vercel agent setup](https://vercel.com/get-started.md)
