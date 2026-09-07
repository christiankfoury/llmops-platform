# TargetGroupBinding compatibility experiment

Initial compatibility passed in CI 34139653787 before design adoption. The
regression now renders actual bootstrap RBAC/admission/bindings and reads the
Terraform IAM template. No cloud operation is approved by this evidence.
The inactive scanner proposal is untouched.

`scripts/validate_tgb_controller.py` runs the pinned, unmodified v3.5.0 controller
on disposable Kubernetes 1.36 with real RBAC, CRD admission and CEL policy
enforcement. AWS calls go to a local deny-by-default protocol fixture using fake
credentials. The fixture is not AWS IAM or a data-plane emulator. AWS IAM and
real ALB health/traffic remain separately gated validation.

The experiment must pass before adopting Terraform-owned load balancing. It
retains Ingress read access because v3.5.0 starts that reconciler unconditionally.
It grants no Ingress writes, no TargetGroupBinding create/delete to the
controller, and allows writes only to the approved binding names. Admission
freezes their specs and prevents Ingress creation in the watched namespace.
