"""Offline schema, privilege and bootstrap checks. No cluster or cloud credentials used."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".maven-cache/aws-manifest-validation"
SCHEMAS = ROOT / "infra/validation/schemas"
HELM = os.environ.get("HELM", "helm")
KUBECONFORM = os.environ.get("KUBECONFORM", "kubeconform")
BOOTSTRAP = "infra/bootstrap/ai-platform-bootstrap"


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys before flattening upstream List wrappers."""


def unique_mapping(loader, node, deep=False):
    keys = [loader.construct_object(key, deep=deep) for key, _ in node.value]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate YAML mapping key")
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def documents(text):
    result = []
    for doc in yaml.load_all(text, Loader=UniqueLoader):
        if doc:
            result.extend(doc["items"] if doc.get("kind") == "List" else [doc])
    return result


def run(*args):
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def verify(path, digest):
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Pinned source checksum mismatch: " + str(path))


def verify_sources():
    for directory in [
        ROOT / BOOTSTRAP / "files",
        ROOT / "infra/terraform/modules/cluster/policies",
    ]:
        for name, source in json.loads(
            (directory / "sources.json").read_text(encoding="utf-8")
        ).items():
            verify(directory / name, source["sha256"])
    for name, source in json.loads(
        (SCHEMAS / "kubernetes/sources.json").read_text(encoding="utf-8")
    )["files"].items():
        verify(SCHEMAS / "kubernetes" / name, source["sha256"])
    source = json.loads((SCHEMAS / "crd-source.json").read_text(encoding="utf-8"))
    verify(ROOT / source["path"], source["sha256"])
    charts = json.loads((ROOT / "infra/validation/charts.json").read_text(encoding="utf-8"))
    for chart in charts.values():
        verify(ROOT / chart["path"], chart["sha256"])
    return charts


def convert(schema):
    """Visit schema-valued keywords, never confuse property names with schema keywords."""
    result = copy.deepcopy(schema)
    for key in ("properties", "patternProperties", "definitions", "$defs"):
        if key in result:
            result[key] = {name: convert(value) for name, value in result[key].items()}
    for key in ("additionalProperties", "items", "not", "contains"):
        if isinstance(result.get(key), dict):
            result[key] = convert(result[key])
    for key in ("allOf", "anyOf", "oneOf"):
        if key in result:
            result[key] = [convert(value) for value in result[key]]
    if result.get("x-kubernetes-int-or-string"):
        result.pop("type", None)
        result["anyOf"] = [{"type": "integer"}, {"type": "string"}]
    if result.get("properties") and not result.get("x-kubernetes-preserve-unknown-fields"):
        result.setdefault("additionalProperties", False)
    if result.pop("nullable", False):
        return {"anyOf": [result, {"type": "null"}]}
    return result


def prepare_schemas(controller_docs):
    generated = CACHE / "schemas"
    generated.mkdir(parents=True, exist_ok=True)
    source = json.loads((SCHEMAS / "crd-openapi-v1.36.0.json").read_text(encoding="utf-8"))
    crd = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "$ref": "#/components/schemas/io.k8s.apiextensions-apiserver.pkg.apis.apiextensions.v1.CustomResourceDefinition",
        "components": {
            "schemas": {
                name: convert(schema) for name, schema in source["components"]["schemas"].items()
            }
        },
    }
    (generated / "customresourcedefinition-apiextensions-v1.json").write_text(
        json.dumps(crd), encoding="utf-8"
    )
    metadata = json.loads((SCHEMAS / "kubernetes/configmap-v1.json").read_text(encoding="utf-8"))[
        "properties"
    ]["metadata"]
    for doc in controller_docs:
        if doc["kind"] != "CustomResourceDefinition":
            continue
        spec = doc["spec"]
        for version in spec["versions"]:
            if not version["served"]:
                continue
            schema = convert(version["schema"]["openAPIV3Schema"])
            schema["$schema"] = "http://json-schema.org/draft-04/schema#"
            schema.setdefault("properties", {})["metadata"] = copy.deepcopy(metadata)
            schema["required"] = sorted(
                set(schema.get("required", [])) | {"apiVersion", "kind", "metadata"}
            )
            schema["properties"]["apiVersion"] = {"enum": [spec["group"] + "/" + version["name"]]}
            schema["properties"]["kind"] = {"enum": [spec["names"]["kind"]]}
            filename = (
                spec["names"]["kind"].lower()
                + "-"
                + spec["group"].split(".")[0]
                + "-"
                + version["name"]
                + ".json"
            )
            (generated / filename).write_text(json.dumps(schema), encoding="utf-8")
    return generated


def validate(name, docs, generated, valid=True):
    path = CACHE / (name + ".yaml")
    path.write_text(yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8", newline="\n")
    result = subprocess.run(
        [
            KUBECONFORM,
            "-strict",
            "-summary",
            "-output",
            "json",
            "-kubernetes-version",
            "1.36.0",
            "-schema-location",
            str(SCHEMAS / "kubernetes" / "{{.ResourceKind}}{{.KindSuffix}}.json"),
            "-schema-location",
            str(generated / "{{.ResourceKind}}{{.KindSuffix}}.json"),
            str(path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if valid:
        if result.returncode:
            raise RuntimeError(name + ": " + result.stdout + result.stderr)
        summary = json.loads(result.stdout)["summary"]
        assert summary["skipped"] == summary["invalid"] == summary["errors"] == 0
        assert summary["valid"] == len(docs)
        print(name + ": " + str(len(docs)) + " resources valid; none skipped")
    else:
        assert result.returncode != 0, "Invalid or unknown resource was accepted: " + name


def bootstrap_boundaries(docs, environment):
    app = "ai-platform-" + environment
    migration = app + "-migration"
    stores = [doc for doc in docs if doc["kind"] == "ClusterSecretStore"]
    assert len(stores) == 2
    for store in stores:
        reader = store["metadata"]["name"].rsplit("-", 1)[1]
        expected = migration if reader == "migration" else app
        assert store["spec"]["conditions"] == [{"namespaces": [expected]}]
        sa = store["spec"]["provider"]["aws"]["auth"]["jwt"]["serviceAccountRef"]
        assert sa == {
            "name": "ai-platform-" + reader + "-secrets",
            "namespace": "external-secrets",
            "audiences": ["sts.amazonaws.com"],
        }
    for doc in docs:
        kind, metadata = doc["kind"], doc["metadata"]
        if kind == "ExternalSecret":
            owner = metadata["name"] == "ai-platform-migration-secrets"
            assert metadata["namespace"] == (migration if owner else app)
            assert doc["spec"]["secretStoreRef"]["name"] == app + (
                "-migration" if owner else "-runtime"
            )
        if kind == "Role" and metadata["name"] in {"app-deployer", "migration-runner"}:
            for rule in doc["rules"]:
                assert "*" not in rule["resources"] + rule["verbs"] + rule["apiGroups"]
                assert not set(rule["resources"]) & {
                    "namespaces",
                    "roles",
                    "rolebindings",
                    "clusterroles",
                    "clusterrolebindings",
                    "externalsecrets",
                    "clustersecretstores",
                }
            if metadata["name"] == "migration-runner":
                assert metadata["namespace"] == migration
                assert not any("secrets" in r["resources"] for r in doc["rules"])
            else:
                assert metadata["namespace"] == app
                assert not any("jobs" in r["resources"] for r in doc["rules"])
                for rule in doc["rules"]:
                    if set(rule["resources"]) & {
                        "services",
                        "ingresses",
                        "networkpolicies",
                        "endpoints",
                        "endpointslices",
                    }:
                        assert set(rule["verbs"]) <= {"get", "list", "watch"}
    assert not any(doc["kind"] == "Secret" for doc in docs)


def migration_boundaries(docs, environment):
    assert len(docs) == 1 and docs[0]["kind"] == "Job"
    job = docs[0]
    assert job["metadata"]["namespace"] == "ai-platform-" + environment + "-migration"
    assert job["spec"]["backoffLimit"] == 0 and job["spec"]["activeDeadlineSeconds"] <= 180
    pod = job["spec"]["template"]["spec"]
    assert not pod["automountServiceAccountToken"] and pod["restartPolicy"] == "Never"
    container = pod["containers"][0]
    assert (
        container["securityContext"]["runAsNonRoot"]
        if "runAsNonRoot" in container["securityContext"]
        else pod["securityContext"]["runAsNonRoot"]
    )
    assert container["securityContext"]["readOnlyRootFilesystem"]
    assert container["args"] == ["java", "-jar", "/app/migration.jar", "migrate"]
    refs = [e["valueFrom"]["secretKeyRef"] for e in container["env"] if "valueFrom" in e]
    assert {ref["name"] for ref in refs} == {"ai-platform-migration-secrets"}
    assert {ref["key"] for ref in refs} == {
        "jdbc-database-url",
        "database-username",
        "database-password",
    }


def validator_regressions():
    # Regression: a CRD property literally named nullable/properties/type is not a schema keyword.
    fixture = {
        "type": "object",
        "properties": {
            "nullable": {"type": "boolean"},
            "properties": {"type": "object", "additionalProperties": {"type": "string"}},
            "type": {"type": "string"},
        },
        "required": ["nullable"],
    }
    converted = convert(fixture)
    assert "anyOf" not in converted and converted["properties"] == fixture["properties"]
    try:
        documents("apiVersion: v1\nkind: Service\nkind: Secret\n")
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate YAML keys accepted")
    for environment in ("dev", "staging", "prod"):
        source = (ROOT / "infra/terraform/environments" / environment / "variables.tf").read_text(
            encoding="utf-8"
        )
        cidr = re.search(r'variable "vpc_cidr" \{[^}]*default\s*=\s*"([^"]+)"', source).group(1)
        values = yaml.safe_load(
            (ROOT / BOOTSTRAP / ("values-" + environment + ".yaml")).read_text(encoding="utf-8")
        )
        assert values["vpcCidr"] == cidr, "Bootstrap/cluster network range drift"


def main():
    validator_regressions()
    CACHE.mkdir(parents=True, exist_ok=True)
    charts = verify_sources()
    controllers = {}
    for name, chart in charts.items():
        namespace = "external-secrets" if name == "external-secrets" else "kube-system"
        values = "infra/bootstrap/controllers/" + name + ".yaml"
        controllers[name] = documents(
            run(
                HELM,
                "template",
                name,
                chart["path"],
                "--namespace",
                namespace,
                "--kube-version",
                "1.36.0",
                "--include-crds",
                "-f",
                values,
            )
        )
    generated = prepare_schemas([doc for docs in controllers.values() for doc in docs])
    for name, docs in controllers.items():
        validate(name, docs, generated)
    for environment in [None, "dev", "staging", "prod"]:
        env = environment or "dev"
        for chart in [
            "infra/helm/ai-platform",
            "infra/helm/ai-platform-network",
            "infra/helm/ai-platform-migration",
            BOOTSTRAP,
        ]:
            values = [] if environment is None else ["-f", chart + "/values-" + env + ".yaml"]
            run(HELM, "lint", chart, "--strict", *values)
            extra = ["--set", "externalSecretsEnabled=true"] if chart == BOOTSTRAP else []
            docs = documents(
                run(
                    HELM,
                    "template",
                    "ai-platform",
                    chart,
                    "--kube-version",
                    "1.36.0",
                    *values,
                    *extra,
                )
            )
            name = Path(chart).name + "-" + (environment or "base")
            validate(name, docs, generated)
            if chart == BOOTSTRAP:
                bootstrap_boundaries(docs, env)
                foundation = documents(run(HELM, "template", "ai-platform", chart, *values))
                assert all(d["apiVersion"] != "external-secrets.io/v1" for d in foundation)
                validate(name + "-foundation", foundation, generated)
            if chart.endswith("ai-platform-migration"):
                migration_boundaries(docs, env)
        path = "infra/k8s/" + ("base" if environment is None else "overlays/" + env)
        validate(
            "kustomize-" + (environment or "base"),
            documents(run("kubectl", "kustomize", path)),
            generated,
        )
        validate(
            "kustomize-network-" + (environment or "base"),
            documents(
                run("kubectl", "kustomize", path.replace("infra/k8s/", "infra/k8s/network/"))
            ),
            generated,
        )
    invalid = copy.deepcopy(next(d for d in docs if d["kind"] == "ExternalSecret"))
    invalid["spec"]["secretStoreRef"]["unexpectedField"] = "must-fail"
    validate("negative-crd-field", [invalid], generated, valid=False)
    validate(
        "negative-missing-schema",
        [
            {
                "apiVersion": "unregistered.invalid/v1",
                "kind": "UnknownResource",
                "metadata": {"name": "must-fail"},
            }
        ],
        generated,
        valid=False,
    )
    invalid = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": "must-fail"},
        "spec": {"ports": [{"port": "wrong-type"}]},
    }
    validate("negative-built-in-type", [invalid], generated, valid=False)
    print(
        "Pinned source checks, migration/store/RBAC boundaries and all negative schema probes passed"
    )


if __name__ == "__main__":
    main()
