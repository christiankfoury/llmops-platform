# Skopeo availability repair — 2026-09-08

The first continuation check confirmed that [CI run 34190019052](https://github.com/christiankfoury/production-ai-platform/actions/runs/34190019052)
on `2b65581e412b736fbd5ed92c2df90d7b389e4238` failed pulling the old
`quay.io/skopeo/stable@sha256:e5d9c4af8ec327785c7ca938d1e4f8452c6a05014850e58e2ff9456899ebd97c`.
Nine validation jobs passed; image promotion and release eligibility failed.

## Repair and focused checks

- Use the maintained [Red Hat UBI 10 Skopeo image](https://catalog.redhat.com/en/software/containers/ubi10/skopeo/673c737a12b9add51a2c29ec),
  resolved and pulled at immutable index digest
  `sha256:59aca4646e8594c191323e9b795e266fbb6ace55cbfd2fb62fd2ce800b5a5701`.
  Linux amd64 manifest: `sha256:3b88efc6cbea91a504bc62f7103c97a749bb54f2a122880ac753c8545f71054a`.
- Explicit `--entrypoint skopeo` in both the local rehearsal and gated ECR
  publisher; runtime probe reports `skopeo version 1.22.2 commit: a02140c778e1f7da4dd7921e10511760c1a0aa39`.
- Trivy 0.70.0, `--exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed
  --scanners vuln,secret`: passed on 2026-09-08, RHEL 10.2 recognized, 199 OS
  packages scanned, no selected vulnerabilities or secrets. Raw local report:
  `.maven-cache/skopeo-repair/ubi-audit.json`, SHA-256
  `5c3a196a048c7b6fffec727033bdd857f0707a1ddf468d3d04d95789df2da522`.
  Distribution RPM advisory coverage is not a proof of vulnerability absence.
- Rejected the available upstream Fedora 44 image
  `sha256:db4108427c05acbadd1447316caa9b5f097a9a737d897d2297443baedff37ded`:
  its successful exit had **unsupported OS** coverage and is not a clean audit.
- Add the replacement tool image to the existing mandatory image scan step.
  Keep digest-preserving copies, root/config digest comparisons, ECR TLS and
  authentication, approval gates and every validation job intact.

## Review and evidence status

Local release archive/release-plan tests, lint, formatting and workflow policy
checks precede commit. The exact pushed revision must pass the full CI, including
the actual three-image OCI registry round trip; that result will be recorded
after readback. No AWS calls or registry authentication changes were made.

This is the independent CI prerequisite repair, not monitoring remediation.
Phase 62 and its preserved workspace remain blocked/deferred. Phase 63 has not
been completed by this repair.
