"""Render every environment and verify Java runtime/network/secret boundaries offline."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HELM = os.environ.get("HELM", "helm")
CHART = "infra/helm/ai-platform"
SECRET_KEYS = {
    "JDBC_DATABASE_URL",
    "DATABASE_USERNAME",
    "DATABASE_PASSWORD",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_USERNAME",
    "REDIS_PASSWORD",
}


def run(*args: str, success: bool = True) -> str:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=60)
    if success:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0, "Unsafe metrics configuration rendered successfully"
    return result.stdout


def check(output: str, expected_environment: str) -> None:
    docs = [doc for doc in yaml.safe_load_all(output) if doc]
    assert all(
        d["kind"]
        not in {
            "Namespace",
            "ClusterSecretStore",
            "ExternalSecret",
            "ClusterRole",
            "ClusterRoleBinding",
            "Job",
        }
        for d in docs
    ), "App releases must remain namespace-scoped and cannot own migration jobs"
    indexed = {(d["kind"], d["metadata"]["name"]): d for d in docs}
    assert len(indexed) == len(docs), "Duplicate rendered resource identity"
    for component in ("api", "web"):
        deployment = next(
            d
            for d in docs
            if d["kind"] == "Deployment"
            and d["metadata"]["labels"]["app.kubernetes.io/component"] == component
        )
        pod = deployment["spec"]["template"]["spec"]
        container = pod["containers"][0]
        config = indexed["ConfigMap", container["envFrom"][0]["configMapRef"]["name"]]["data"]
        assert config["ENVIRONMENT"] == expected_environment
        assert all(isinstance(value, str) for value in config.values())
        assert container["securityContext"]["readOnlyRootFilesystem"]
        assert container["securityContext"]["allowPrivilegeEscalation"] is False
        assert container["securityContext"]["runAsUser"] == 10001
        assert (
            container["securityContext"]["runAsGroup"] == pod["securityContext"]["fsGroup"] == 10001
        )
        assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
        assert pod["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
        mounts = {m["mountPath"] for m in container["volumeMounts"]}
        assert "/tmp" in mounts
        assert all("sizeLimit" in v["emptyDir"] for v in pod["volumes"] if "emptyDir" in v)
        if component == "api":
            assert container["resources"]["limits"]["memory"] == "1Gi"
            assert "-Xmx512m" in config["JAVA_TOOL_OPTIONS"]
            assert pod["terminationGracePeriodSeconds"] >= 50
            assert container["startupProbe"]["httpGet"]["path"] == "/health/live"
            assert container["readinessProbe"]["httpGet"]["path"] == "/health/ready"
            assert config["DATABASE_MIGRATIONS_ENABLED"] == config["SEED_LOCAL_DATA"] == "false"
            assert config["REDIS_TLS_ENABLED"] == "true"
            assert config["MANAGEMENT_PORT"] == "9080"
            assert set(e["name"] for e in container["env"]) == SECRET_KEYS
            assert all("secretKeyRef" in e["valueFrom"] for e in container["env"])
            assert SECRET_KEYS.isdisjoint(config)
        else:
            assert "/app/.next/cache" in mounts
            assert config["API_BASE_URL"].startswith("http://")
            assert "NEXT_PUBLIC_API_BASE_URL" not in config
            assert "OIDC_AUDIENCE" in config
            if config["WEB_AUTH_MODE"] == "oidc":
                assert config["OIDC_AUDIENCE"] == "https://api.fixture.invalid"
                assert config["OIDC_ISSUER"] and config["OIDC_CLIENT_ID"] and config["WEB_ORIGIN"]
            assert SECRET_KEYS.isdisjoint(config)
            assert all(e["name"] not in SECRET_KEYS for e in container.get("env", []))
    metrics = next(
        d for d in docs if d["kind"] == "Service" and d["metadata"]["name"].endswith("-metrics")
    )
    assert metrics["spec"]["type"] == "ClusterIP"
    assert metrics["spec"]["ports"] == [{"name": "metrics", "port": 9080, "targetPort": "metrics"}]
    assert metrics["metadata"]["annotations"]["prometheus.io/path"] == "/actuator/prometheus"
    policies = [d for d in docs if d["kind"] == "NetworkPolicy"]
    rules = [
        r
        for d in policies
        for r in d["spec"].get("ingress", [])
        if any(p["port"] == 9080 for p in r.get("ports", []))
    ]
    assert len(rules) == 1 and len(rules[0]["from"]) == 1
    peer = rules[0]["from"][0]
    assert peer["namespaceSelector"]["matchLabels"] == {
        "kubernetes.io/metadata.name": "observability"
    }
    assert peer["podSelector"]["matchLabels"] == {"app.kubernetes.io/name": "prometheus"}
    assert any(d["spec"]["podSelector"] == {} and not d["spec"].get("ingress") for d in policies)
    for ingress in (d for d in docs if d["kind"] == "Ingress"):
        for rule in ingress["spec"]["rules"]:
            for path in rule["http"]["paths"]:
                service = path["backend"]["service"]
                assert service["name"] != metrics["metadata"]["name"]
                assert service["port"].get("number") != 9080


def main() -> None:
    for environment in (None, "dev", "staging", "prod"):
        values = [] if environment is None else ["-f", CHART + "/values-" + environment + ".yaml"]
        run(HELM, "lint", CHART, "--strict", *values)
        check(run(HELM, "template", "ai-platform", CHART, *values), environment or "dev")
        print("Helm Java runtime boundaries:", environment or "base")
    check(
        run(
            HELM,
            "template",
            "ai-platform",
            CHART,
            "--set",
            "web.config.authMode=oidc,api.config.oidcAudience=https://api.fixture.invalid,web.config.oidcIssuer=https://identity.fixture.invalid,web.config.oidcClientId=fixture-client",
        ),
        "dev",
    )
    run(
        HELM,
        "template",
        "ai-platform",
        CHART,
        "--set",
        "networkPolicy.enabled=false",
        success=False,
    )
    for environment in (None, "dev", "staging", "prod"):
        path = "infra/k8s/" + ("base" if environment is None else "overlays/" + environment)
        check(run("kubectl", "kustomize", path), environment or "dev")
        print("Kustomize Java runtime boundaries:", environment or "base")
    print("Optional OIDC configuration and refusal of unprotected metrics passed")


if __name__ == "__main__":
    main()
