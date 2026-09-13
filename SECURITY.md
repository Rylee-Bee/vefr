# Security

VEFR is a small local-first engine: it runs on your machine, talks
to whatever LLM endpoint you point it at, and holds whatever world
pack you give it. The threat model is honest about that. This
document is a starting point, not a promise.

## Supported versions

| Branch | Supported |
| --- | --- |
| `main` (latest release) | yes |
| older release tags | best-effort, security fixes backported by judgement |

The engine is small enough that there is no LTS matrix to maintain.
If you depend on a specific tag, pin to it and check back here when
upgrading.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for anything that
looks like a real vulnerability, an active leak, or a credential
that should not be public.

Use one of these instead:

- **GitHub private vulnerability reporting** — the
  Settings → Code security → Private vulnerability reporting form.
  This is the fastest path when the repo is configured for it.
- **Email** — open a regular GitHub issue titled
  `security: contact request` and a maintainer will reply with an
  address. (We deliberately do not print an email here to keep
  spam harvesters out of it.)
- **GitHub Security Advisories** — the
  `gh-advisories` workflow at `.github/workflows/security.yml`
  is the supported intake when private reporting is enabled.

When you write in:

- describe what you found, where, and how to reproduce
- include the commit SHA or release tag if you have one
- do **not** paste the leaked secret value itself — a fingerprint
  (first 4 + last 4 chars, or the file + line) is enough

You should hear back within a week. A real secret in history is
treated as urgent; a quirk in a docs example is not.

## Reporting a leaked credential in this repo

If you find an SSH key, API token, password, or other credential
that should not be public:

1. Do **not** open a public issue with the value.
2. Use the private channel above. Tell us:
   - the file and line number (commit SHA if you have it)
   - which environment the credential belongs to
   - whether you tested it (please don't, if you can avoid it)
3. We will rotate the credential, scrub the history if needed,
   and publish a post-mortem once the rotation is complete.

We will not ask you to rotate anything on your side; that's on us.

## Threat model in plain English

VEFR is honest about what it is and isn't:

- **What it is** — a FastAPI process that reads a world pack from
  disk, builds a small HTML/JS UI, and calls whatever OpenAI-
  compatible LLM endpoint you point it at.
- **What it isn't** — a hosted service, a multi-tenant system, a
  database, or a daemon that reaches out on its own.

Implications:

- The engine does not phone home. It only talks to endpoints you
  configure (`VEFR_LLAMACPP_URL`, `VEFR_SPARK_URL`,
  `VEFR_GITEA_URL`, plus the Gitea host for `ferry fetch`).
- The engine binds to `127.0.0.1` by default. Exposing it on a
  LAN or WAN is an operator choice; the bundled compose uses
  `network_mode: host` for LAN play.
- World packs are loaded as untrusted data. The geometry/contract
  validator (`maplab.validate()`) runs on every load and rejects
  shapes that violate the pack contract.
- The engine never writes outside `VEFR_HOME` (default
  `~/.local/share/vefr`). Operators who deploy with named volumes
  (`vefr-template` ro, `vefr-worlds` rw, `vefr-data` rw) keep
  state on the deploy host, not in the image.

## Public-private boundary

A public VEFR checkout contains enough information to build a
world, but no information about the private world or
infrastructure of the person who built VEFR. The
`scripts/check_public_surface.py` guard is the tripwire that
enforces this; it is wired into CI and rejects PRs that
re-introduce private LAN IPs, real hostnames, private Gitea
domains, the operator's SSH user, private filesystem paths, or
obvious credential formats.

If a contributor needs to add a *real* host or credential to the
public tree for some reason, that change should come with a
deliberate allowlist update plus a discussion in the PR — not
silently ride along with a feature change.

## What this file does not promise

- No SLA on patch turnaround. We are a small project.
- No backport matrix. If you need a fix on an older tag, the
  fastest path is usually to upgrade.
- No guarantee that every reported issue is in scope. Bug
  reports and feature requests belong in public issues.
