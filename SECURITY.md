# Security policy and threat model

NovaUI is an early-stage framework. Its loopback server and event bridge are intended for local development and desktop hosting; they are not a hardened public deployment server. Passing tests does not establish production security.

## Current protections

- The app server accepts only `127.0.0.1` or `localhost` bind addresses and rejects non-loopback Host authorities.
- Tree-fetch requests require the frontend's `X-NovaUI-Request: tree` header, preventing simple cross-site GET embeddings from invoking route factories.
- State-changing event requests require JSON content type and a matching loopback `Origin`; missing or cross-origin Origin headers are rejected.
- Event bodies are capped at 16 KiB, input strings at 8,000 characters, and form submissions at 100 fields. App-generated event IDs use 256 bits of cryptographic randomness, are one-shot, and are replaced on tree serialization.
- The threaded server accepts at most 32 active requests, uses a 10 second socket timeout, and rejects new work when full.
- Project assets must resolve under the configured `assets/` directory; files larger than 32 MiB are rejected.
- The renderer maps known component types and uses `textContent` for user-provided text. Browser requests never supply Python source, callable names, or filesystem paths for execution.
- HTTP responses use `nosniff`, a Content Security Policy, frame denial, and a no-referrer policy. Inline styles remain permitted because the renderer assigns validated style properties dynamically.
- Framework logs do not include form values, passwords, tokens, event bodies, or callback exception messages. Debug HTTP responses reveal exception type names only.

## Remaining risks and limits

- There is no authentication, user/session isolation, CSRF token, TLS, or public hosting mode. Origin checks mitigate ordinary cross-site browser requests but do not authenticate local software or defend against every browser/plugin/extension compromise.
- Other processes able to connect to loopback can interact with the running local app. Do not run untrusted local applications in the same user account and assume NovaUI isolates them.
- Application callbacks and route factories execute synchronously in request threads. A callback can block the app or consume CPU even though concurrent requests are bounded.
- The server is not a substitute for a production reverse proxy, authentication layer, trusted backend validation, or operational security review.
- Uploaded files, downloads, and rich HTML are not implemented. If added, they require independent server-side validation and sanitization.
- Accessibility and platform behavior have only partial automated coverage; NovaUI does not claim WCAG conformance.

## Reporting a vulnerability

This repository has not configured GitHub private vulnerability reporting or published a private security contact. Do not post exploit details in a public issue. Before a public release, maintainers should enable GitHub private vulnerability reporting or document a monitored private address here. Until then, contact the repository owner privately through the hosting service, if a private route is available; if no private route is available, do not send exploit details publicly.

Include the affected version or commit, environment, a minimal reproduction, impact, and any suggested mitigation. Do not include real user data or credentials. The maintainer should acknowledge receipt, triage severity and affected versions, coordinate a fix and disclosure with the reporter, and communicate the fix through a changelog or repository security advisory. There is currently no published response-time guarantee or configured advisory endpoint.

## Dependency audit status

The base package currently declares no runtime dependencies. Desktop hosting is optional (`pywebview>=5.0`); the installed 6.2.1 metadata reports BSD-3-Clause. The optional Qt backend brings PyQt6/PyQt6-WebEngine, whose installed metadata reports GPL-3.0-only; check licensing obligations before distributing applications with that backend. The checked development tools (`pytest`, `ruff`, `build`) report MIT licenses; installed transitive webview helpers `bottle` and `proxy_tools` also report MIT. This is a metadata spot check, not a complete transitive license inventory.

On 2026-10-23, `pip-audit` was not installed in the available environment, so no advisory-database scan was completed. CI is configured to run `pip-audit` against the installed development and desktop extras; its results have not yet been observed and must be reviewed for each release.

The upstream pywebview GitHub advisory page showed no published advisories when reviewed, but this is not a substitute for a full ecosystem scan. PyPI metadata for the installed pywebview 6.2.1 release reports that it was not uploaded with trusted-publishing provenance. See the [upstream advisory page](https://github.com/r0x0r/pywebview/security/advisories) and [PyPI release metadata](https://pypi.org/project/pywebview/6.2.1/). The new CI workflow uses official GitHub actions pinned to full commit SHAs, but has not yet run on the remote service.
