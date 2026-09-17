# Source publication review

Reviewed 2026-09-17 against main `c6fa6e7` and the publication candidate.
Visibility has not changed. This review supports a source-sharing decision, not
AWS deployment or acceptance of the monitoring vulnerabilities.

## Retained GitHub material

The [coverage record](publication-exposure-review.json) inventories 329 runs and
481 artifacts. Downloaded and reviewed 328 log archives and all 471 unexpired
artifacts: 543,159,889 compressed bytes and 5,665 extracted members. ZIP and gzip/TAR
build records were handled separately. Ten artifacts are expired; logs for failed
push run `34151173790` return HTTP 404. Unavailable content was not counted as reviewed.

Gitleaks 8.30.1 scanned the downloads with upstream rules, full redaction and archive
depth three. Its 88 matches were SHA-256 references to retained API audit/SBOM files;
each was verified against the corresponding evidence bytes. No credential was found
in those matches. No scanner rule, exception or historical finding policy changed.

Extracted text was also checked for credential markers, personal paths, contact
details and internal notes. The three large OCI image archives received archive-aware
secret scanning rather than text-only matching. Contact metadata consists of the
maintainer's existing Git identity and upstream package/build authors. Internal-note
matches describe repository implementation and synthetic-data boundaries. These
checks found no customer payloads or private operational credentials.

Git history and build provenance include the maintainer's existing author email.
It will be visible when the source and Actions history become public. Older retained
Actions artifacts also contain built images; keeping current GHCR packages private
does not hide those historical artifacts. They retain normal expiration. Neither
history nor failed-run evidence has been deleted or rewritten.

At baseline, the remote exposes one branch, no tags/releases/release assets, and
one historical closed PR with no issue or inline review comments. Discussions are
disabled; no wiki Git repository was available. The new cleanup PR and its runs
must be included in the final pre-publication review.

## Source and application checks

- Fresh history review: 203 commits, ten existing reviewed synthetic detections,
  zero unreviewed detections. Added candidate text passed a separate staged scan.
  Literal demo keys in newly archived command examples use shell variables;
  original examples remain in history. The complete patch also includes removed
  historical placeholders, which are not new credentials.
- Frontend: 23 tests, lint, type checks and production build passed. Tests cover
  fixture consistency, filters, time bounds, limits, empty results, details,
  blocked writes and absence of backend calls.
- Actual browser captures: [gallery and source hashes](../dashboard-screenshots.md).
  Desktop and mobile layout checked; browser warning/error log empty.
- Default Compose: isolated images/project, successful Flyway job, healthy Java
  and web containers, successful documented mock completion, and one corresponding
  PostgreSQL request row verified. Services stopped; volumes retained.
- CI policy validation and 21 focused supply-chain/registry tests passed.
  Current PR and merged-main mandatory scans/integration evidence remain required.

## Settings and final gate

All three existing CI image packages remain private. Inherited repository
permissions were removed; explicit repository Actions access and owner access
remain. Package identity/digest checks and fail-closed creation policy are unchanged.
The Actions budget was read back as USD 5/month, Stop usage enabled, USD 0 spent;
other product budgets remain zero. Billing figures can lag usage.

Required PR protection, complete candidate/main CI and final settings readbacks
are tracked in [publication decisions](../publication-decisions.md). After those
pass, obtain final visibility approval, then enable GitHub private reporting and
verify public rendering, branch protection, private package access and public CI.
Expired material remains an explicit review limitation, not a pass.
