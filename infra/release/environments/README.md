# Approved environment inputs

`dev.example.json` is a nonsecret, deliberately non-executable input example. Do not fill it with real secrets. At the AWS launch approval gate, prepare and review separate `dev.json`, `staging.json`, or `prod.json` using approved Terraform outputs and identity/HTTPS configuration. Those files are not created automatically. Follow `docs/immutable-release-runbook.md` and keep the workflow cloud jobs hard-held until explicit environment approval.
