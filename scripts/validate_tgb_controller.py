"""Exercise unmodified LBC v3.5.0 against disposable Kubernetes and local AWS fixtures.

Never uses the current kubeconfig, AWS credentials, or a remote cluster. Requires
Linux Docker, kind, Helm, kubectl, and PyYAML. This is a compatibility experiment;
mock AWS authorization does not prove the real AWS IAM service or ALB data plane.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".maven-cache/tgb-compatibility"
NS = "ai-platform-dev"
SA = "system:serviceaccount:kube-system:aws-load-balancer-controller"
ARN = "arn:aws:elasticloadbalancing:us-east-1:000000000000:targetgroup/ai-platform-api/0123456789abcdef"
OTHER_ARN = ARN.replace("ai-platform-api", "unapproved")
VPC = "vpc-00000000000000000"
NODE = (
    "kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed"
)
CLUSTER = "platform-tgb-compatibility"


def run(*args, data=None, ok=True, timeout=120):
    result = subprocess.run(
        args, cwd=ROOT, input=data, text=True, capture_output=True, timeout=timeout
    )
    if ok and result.returncode:
        raise RuntimeError(" ".join(args) + "\n" + result.stdout + result.stderr)
    return result


def kube(*args, **kwargs):
    return run("kubectl", "--kubeconfig", str(CACHE / "kubeconfig"), *args, **kwargs)


def apply(docs, *args, ok=True):
    return kube("apply", "-f", "-", *args, data=yaml.safe_dump_all(docs), ok=ok)


def wait_for(label, predicate, seconds=120):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            print("PASS: " + label, flush=True)
            return
        time.sleep(2)
    raise AssertionError("Timed out: " + label)


def obj(api, kind, name, spec=None, namespace=NS):
    result = {"apiVersion": api, "kind": kind, "metadata": {"name": name}}
    if namespace:
        result["metadata"]["namespace"] = namespace
    if spec is not None:
        result["spec"] = spec
    return result


def bootstrap_docs(enabled=False):
    values = {
        "targetBindingsEnabled": enabled,
        "targetBindings": {
            "ai-platform-api": {
                "arn": ARN,
                "service": "ai-platform-api",
                "port": 8000,
                "vpcID": VPC,
            }
        },
    }
    return [
        d
        for d in yaml.safe_load_all(
            run(
                "helm",
                "template",
                "bootstrap",
                "infra/bootstrap/ai-platform-bootstrap",
                "-f",
                "-",
                data=yaml.safe_dump(values),
            ).stdout
        )
        if d
    ]


def binding():
    return next(d for d in bootstrap_docs(True) if d["kind"] == "TargetGroupBinding")


def candidate_rbac():
    names = {
        "ai-platform-load-balancer-discovery",
        "load-balancer-reconciler",
        "load-balancer-leader-election",
        "app-deployer",
    }
    return [
        d
        for d in bootstrap_docs()
        if d["kind"] in {"Role", "RoleBinding", "ClusterRole", "ClusterRoleBinding"}
        and d["metadata"]["name"] in names
    ]


def admission():
    return [
        d
        for d in bootstrap_docs()
        if d["kind"] in {"ValidatingAdmissionPolicy", "ValidatingAdmissionPolicyBinding"}
    ]


class AWSFixture:
    def __init__(self):
        self.targets = set()
        self.calls = []
        self.denied = []
        self.fail_registration = False
        self.lock = threading.Lock()
        template = (
            ROOT / "infra/terraform/modules/load-balancing/registration-policy.json.tftpl"
        ).read_text()
        self.policy = json.loads(template.replace("${targetgroup_arns}", json.dumps([ARN])))

    def authorized(self, action, resource):
        # Intentionally supports only this repository's simple Allow policy subset.
        # Unsupported IAM semantics fail the test, rather than being approximated.
        for statement in self.policy["Statement"]:
            assert set(statement) <= {"Sid", "Effect", "Action", "Resource"}
            assert statement["Effect"] == "Allow" and isinstance(statement["Action"], list)
            assert all("*" not in action for action in statement["Action"])
            resources = statement["Resource"]
            if isinstance(resources, str):
                resources = [resources]
            if action in statement["Action"] and any(r == "*" or r == resource for r in resources):
                return True
        return False

    def respond(self, params):
        action = params.get("Action", [""])[0]
        arn = params.get("TargetGroupArn", [""])[0]
        with self.lock:
            self.calls.append(action)
            prefix = (
                "ec2"
                if action
                in {
                    "DescribeVpcs",
                    "DescribeSecurityGroups",
                    "AuthorizeSecurityGroupIngress",
                    "RevokeSecurityGroupIngress",
                    "CreateSecurityGroup",
                    "DeleteSecurityGroup",
                }
                else "sts"
                if action == "AssumeRole"
                else "elasticloadbalancing"
            )
            if not self.authorized(prefix + ":" + action, arn or "*"):
                self.denied.append(action)
                return 403, "AccessDenied", "Unapproved target group"
            if action == "RegisterTargets" and self.fail_registration:
                return 503, "ServiceUnavailable", "Synthetic temporary failure"
            if action in {"RegisterTargets", "DeregisterTargets"}:
                targets = {
                    (values[0], int(params[key.replace(".Id", ".Port")][0]))
                    for key, values in params.items()
                    if key.startswith("Targets.member.") and key.endswith(".Id")
                }
                if action == "RegisterTargets":
                    self.targets.update(targets)
                else:
                    self.targets.difference_update(targets)
                return 200, action, ""
            if action == "DescribeTargetHealth":
                members = "".join(
                    "<member><Target><Id>"
                    + escape(ip)
                    + "</Id><Port>"
                    + str(port)
                    + "</Port></Target><TargetHealth><State>healthy</State></TargetHealth></member>"
                    for ip, port in sorted(self.targets)
                )
                return (
                    200,
                    action,
                    "<TargetHealthDescriptions>" + members + "</TargetHealthDescriptions>",
                )
            if action == "DescribeTargetGroups":
                return (
                    200,
                    action,
                    (
                        "<TargetGroups><member><TargetGroupArn>" + ARN + "</TargetGroupArn>"
                        "<TargetGroupName>ai-platform-api</TargetGroupName><TargetType>ip</TargetType>"
                        "<Protocol>HTTP</Protocol><Port>8000</Port><VpcId>" + VPC + "</VpcId>"
                        "<IpAddressType>ipv4</IpAddressType></member></TargetGroups>"
                    ),
                )
            if action == "DescribeVpcs":
                return (
                    200,
                    action,
                    (
                        "<vpcSet><item><vpcId>"
                        + VPC
                        + "</vpcId><cidrBlock>10.244.0.0/16</cidrBlock>"
                        "<cidrBlockAssociationSet><item><cidrBlock>10.244.0.0/16</cidrBlock>"
                        "<cidrBlockState><state>associated</state></cidrBlockState>"
                        "</item></cidrBlockAssociationSet></item></vpcSet>"
                    ),
                )
            if action == "DescribeSecurityGroups":
                # A real-looking SG with an unrelated rule: controller may discover
                # and inspect it, but must neither authorize nor revoke its rules.
                return (
                    200,
                    action,
                    (
                        "<securityGroupInfo><item><groupId>sg-0123456789abcdef0</groupId>"
                        "<groupName>terraform-owned</groupName><vpcId>" + VPC + "</vpcId>"
                        "<ipPermissions><item><ipProtocol>tcp</ipProtocol><fromPort>8000</fromPort>"
                        "<toPort>8000</toPort><ipRanges><item><cidrIp>10.0.0.0/16</cidrIp>"
                        "<description>Terraform owns this rule</description></item></ipRanges>"
                        "</item></ipPermissions></item></securityGroupInfo>"
                    ),
                )
            self.denied.append(action)
            return 403, "AccessDenied", "Action is outside target registration permissions"


def serve_aws(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            params = urllib.parse.parse_qs(
                self.rfile.read(int(self.headers["Content-Length"])).decode()
            )
            status, action, body = state.respond(params)
            if status == 200:
                # EC2 and ELB use different XML namespaces / response conventions.
                ec2 = action in {"DescribeVpcs", "DescribeSecurityGroups"}
                namespace = (
                    "http://ec2.amazonaws.com/doc/2016-11-15/"
                    if ec2
                    else "http://elasticloadbalancing.amazonaws.com/doc/2015-12-01/"
                )
                result = (
                    body if ec2 else "<" + action + "Result>" + body + "</" + action + "Result>"
                )
                text = (
                    "<"
                    + action
                    + 'Response xmlns="'
                    + namespace
                    + '">'
                    + result
                    + "<ResponseMetadata><RequestId>fixture</RequestId></ResponseMetadata></"
                    + action
                    + "Response>"
                )
            else:
                text = (
                    "<ErrorResponse><Error><Type>Sender</Type><Code>"
                    + action
                    + "</Code><Message>"
                    + body
                    + "</Message></Error><RequestId>fixture</RequestId></ErrorResponse>"
                )
            self.send_response(status)
            self.send_header("Content-Type", "text/xml")
            self.end_headers()
            self.wfile.write(text.encode())

    server = ThreadingHTTPServer(("0.0.0.0", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def rejected(label, result):
    assert result.returncode != 0 and (
        "Error from server (Forbidden):" in result.stderr
        or "denied the request:" in result.stderr
        or "denied request:" in result.stderr
    ), result.stderr
    print("PASS: rejected " + label, flush=True)


def main():
    if os.name == "nt":
        raise RuntimeError("Run in isolated Linux CI; no existing local Kubernetes context is used")
    CACHE.mkdir(parents=True, exist_ok=True)
    assert not (CACHE / "kubeconfig").exists(), "Refuse to reuse an existing test cluster"
    charts = json.loads((ROOT / "infra/validation/charts.json").read_text())
    chart = charts["aws-load-balancer-controller"]
    path = ROOT / chart["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(urllib.request.urlopen(chart["url"], timeout=60).read())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == chart["sha256"]
    state = AWSFixture()
    server = serve_aws(state)
    created = False
    try:
        run(
            "kind",
            "create",
            "cluster",
            "--name",
            CLUSTER,
            "--image",
            NODE,
            "--kubeconfig",
            str(CACHE / "kubeconfig"),
            "--wait",
            "120s",
            timeout=240,
        )
        created = True
        route = run(
            "docker", "exec", CLUSTER + "-control-plane", "ip", "-4", "route", "show", "default"
        ).stdout.split()
        gateway = str(ipaddress.IPv4Address(route[route.index("via") + 1]))
        url = "http://" + gateway + ":" + str(server.server_port)
        apply(
            [
                next(
                    d
                    for d in bootstrap_docs()
                    if d["kind"] == "Namespace" and d["metadata"]["name"] == NS
                ),
                obj(
                    "v1", "ServiceAccount", "aws-load-balancer-controller", namespace="kube-system"
                ),
            ]
        )
        apply(candidate_rbac())
        values = yaml.safe_load(
            (ROOT / "infra/bootstrap/controllers/aws-load-balancer-controller.yaml").read_text()
        )
        values.update(
            {
                "replicaCount": 1,
                "clusterName": "compatibility",
                "awsApiEndpoints": ",".join(
                    service + "=" + url
                    for service in [
                        "EC2",
                        "Elastic Load Balancing v2",
                        "STS",
                        "ACM",
                        "WAF",
                        "WAFV2",
                        "Shield",
                        "Resource Groups Tagging API",
                    ]
                ),
                "env": {
                    "AWS_ACCESS_KEY_ID": "testing",
                    "AWS_SECRET_ACCESS_KEY": "synthetic-not-a-credential",
                    "AWS_EC2_METADATA_DISABLED": "true",
                },
            }
        )
        file = CACHE / "controller-values.yaml"
        file.write_text(yaml.safe_dump(values))
        run(
            "helm",
            "upgrade",
            "--install",
            "aws-load-balancer-controller",
            str(path),
            "--kubeconfig",
            str(CACHE / "kubeconfig"),
            "--namespace",
            "kube-system",
            "-f",
            str(file),
            "--wait",
            "--timeout",
            "180s",
            timeout=210,
        )
        seed_ingress = obj(
            "networking.k8s.io/v1",
            "Ingress",
            "fixture-ingress",
            {"defaultBackend": {"service": {"name": "ai-platform-api", "port": {"number": 8000}}}},
        )
        seed_ingress["metadata"]["annotations"] = {"kubernetes.io/ingress.class": "ignored-fixture"}
        apply([seed_ingress])
        apply(admission())
        for name in (
            NS + "-no-ingress",
            NS + "-approved-targets",
            "ai-platform-load-balancer-leader",
        ):
            policy = json.loads(kube("get", "validatingadmissionpolicy", name, "-o", "json").stdout)
            assert not policy.get("status", {}).get("typeChecking", {}).get("expressionWarnings"), (
                policy
            )
        service = obj(
            "v1",
            "Service",
            "ai-platform-api",
            {
                "ports": [{"name": "http", "port": 8000, "targetPort": 8000}],
                "type": "ClusterIP",
                "selector": {"app": "synthetic"},
            },
        )
        apply([service, binding()])
        # Give the real webhook's informer cache time to observe the approved TGB.
        wait_for(
            "binding observed before pod admission",
            lambda: (
                json.loads(
                    kube(
                        "get", "targetgroupbinding", "ai-platform-api", "-n", NS, "-o", "json"
                    ).stdout
                )
                .get("status", {})
                .get("observedGeneration")
                == 1
            ),
        )
        pod = obj(
            "v1",
            "Pod",
            "synthetic-pod",
            {
                "containers": [
                    {
                        "name": "pause",
                        "image": "registry.k8s.io/pause:3.10.1",
                        "securityContext": {
                            "allowPrivilegeEscalation": False,
                            "capabilities": {"drop": ["ALL"]},
                        },
                    }
                ],
                "securityContext": {
                    "runAsNonRoot": True,
                    "runAsUser": 65534,
                    "seccompProfile": {"type": "RuntimeDefault"},
                },
                "nodeName": CLUSTER + "-control-plane",
            },
        )
        pod["metadata"]["labels"] = {"app": "synthetic"}
        apply([pod])
        kube(
            "wait",
            "pod/synthetic-pod",
            "-n",
            NS,
            "--for=jsonpath={.status.phase}=Running",
            "--timeout=90s",
        )
        pod_data = json.loads(kube("get", "pod", "synthetic-pod", "-n", NS, "-o", "json").stdout)
        assert {"conditionType": "target-health.elbv2.k8s.aws/ai-platform-api"} in pod_data[
            "spec"
        ].get("readinessGates", [])
        pod_ip = pod_data["status"]["podIP"]
        wait_for(
            "register approved pod through real EndpointSlice and injected readiness gate",
            lambda: state.targets == {(pod_ip, 8000)},
        )
        wait_for(
            "controller status and checkpoint writes",
            lambda: (
                json.loads(
                    kube(
                        "get", "targetgroupbinding", "ai-platform-api", "-n", NS, "-o", "json"
                    ).stdout
                )
                .get("status", {})
                .get("observedGeneration")
                == 1
            ),
        )
        wait_for(
            "pod target health readiness gate",
            lambda: any(
                c["type"] == "target-health.elbv2.k8s.aws/ai-platform-api" and c["status"] == "True"
                for c in json.loads(
                    kube("get", "pod", "synthetic-pod", "-n", NS, "-o", "json").stdout
                )
                .get("status", {})
                .get("conditions", [])
            ),
        )
        # Real Kubernetes authorizer denials, not just can-i or YAML assertions.
        slices = json.loads(
            kube(
                "get",
                "endpointslices",
                "-n",
                NS,
                "-l",
                "kubernetes.io/service-name=ai-platform-api",
                "-o",
                "json",
            ).stdout
        )["items"]
        assert slices
        for resource, name in [
            ("ingresses", "fixture-ingress"),
            ("services", "ai-platform-api"),
            ("endpointslices.discovery.k8s.io", slices[0]["metadata"]["name"]),
        ]:
            rejected(
                "controller patch " + resource,
                kube(
                    "patch",
                    resource,
                    name,
                    "-n",
                    NS,
                    "--type=merge",
                    "-p",
                    '{"metadata":{"labels":{"forbidden":"true"}}}',
                    "--as",
                    SA,
                    ok=False,
                ),
            )
        rejected(
            "controller create TGB",
            kube("create", "-f", "-", "--as", SA, data=yaml.safe_dump(binding()), ok=False),
        )
        rejected(
            "controller delete TGB",
            kube(
                "delete", "targetgroupbindings", "ai-platform-api", "-n", NS, "--as", SA, ok=False
            ),
        )
        rejected(
            "app deployer mutate TGB",
            kube(
                "patch",
                "targetgroupbindings",
                "ai-platform-api",
                "-n",
                NS,
                "--type=merge",
                "-p",
                '{"spec":{"serviceRef":{"name":"unapproved"}}}',
                "--as",
                "app-test",
                "--as-group",
                "ai-platform-app-deployers",
                ok=False,
            ),
        )
        rejected(
            "controller retarget binding",
            kube(
                "patch",
                "targetgroupbindings",
                "ai-platform-api",
                "-n",
                NS,
                "--type=merge",
                "-p",
                '{"spec":{"serviceRef":{"name":"unapproved"}}}',
                "--as",
                SA,
                ok=False,
            ),
        )
        for key, value in [
            ("networking", {"ingress": []}),
            ("iamRoleArnToAssume", "arn:aws:iam::000000000000:role/unapproved"),
            ("multiClusterTargetGroup", True),
            ("targetGroupARN", OTHER_ARN),
            ("serviceRef", {"name": "ai-platform-api", "port": 9000}),
        ]:
            rejected(
                "bootstrap unauthorized " + key,
                kube(
                    "patch",
                    "targetgroupbindings",
                    "ai-platform-api",
                    "-n",
                    NS,
                    "--type=merge",
                    "-p",
                    json.dumps({"spec": {key: value}}),
                    ok=False,
                ),
            )
        ingress = obj(
            "networking.k8s.io/v1",
            "Ingress",
            "forbidden",
            {
                "ingressClassName": "alb",
                "defaultBackend": {
                    "service": {"name": "ai-platform-api", "port": {"number": 8000}}
                },
            },
        )
        rejected("bootstrap create Ingress", apply([ingress], ok=False))
        rejected(
            "controller create unrelated leader lease",
            kube(
                "create",
                "-f",
                "-",
                "--as",
                SA,
                data=yaml.safe_dump(
                    obj("coordination.k8s.io/v1", "Lease", "unapproved", {}, "kube-system")
                ),
                ok=False,
            ),
        )
        rejected(
            "controller access other namespace",
            kube("get", "targetgroupbindings", "-n", "default", "--as", SA, ok=False),
        )
        # Actual Kubernetes EndpointSlice controller handles Service selection changes.
        kube("label", "pod", "synthetic-pod", "-n", NS, "app=removed", "--overwrite")
        wait_for("deregister removed endpoint", lambda: not state.targets)
        state.fail_registration = True
        baseline = state.calls.count("RegisterTargets")
        kube("label", "pod", "synthetic-pod", "-n", NS, "app=synthetic", "--overwrite")
        wait_for(
            "temporary AWS failure exercised",
            lambda: state.calls.count("RegisterTargets") > baseline,
        )
        assert not state.targets
        state.fail_registration = False
        wait_for(
            "recover registration after AWS failure",
            lambda: state.targets == {(pod_ip, 8000)},
        )
        kube("rollout", "restart", "deployment/aws-load-balancer-controller", "-n", "kube-system")
        kube(
            "rollout",
            "status",
            "deployment/aws-load-balancer-controller",
            "-n",
            "kube-system",
            "--timeout=90s",
        )
        kube("delete", "targetgroupbinding", "ai-platform-api", "-n", NS, "--wait=false")
        wait_for(
            "delete cleans targets and removes finalizer after restart",
            lambda: (
                not state.targets
                and not json.loads(
                    kube("get", "targetgroupbindings", "-n", NS, "-o", "json").stdout
                )["items"]
            ),
        )
        assert not state.denied, (
            "Legitimate controller operation requested unauthorized AWS actions: "
            + str(state.denied)
        )
        for action in ("RegisterTargets", "DeregisterTargets"):
            assert state.respond({"Action": [action], "TargetGroupArn": [OTHER_ARN]})[0] == 403
        for action in (
            "CreateLoadBalancer",
            "CreateTargetGroup",
            "ModifyListener",
            "CreateRule",
            "AuthorizeSecurityGroupIngress",
            "RevokeSecurityGroupIngress",
            "AssumeRole",
        ):
            assert state.respond({"Action": [action]})[0] == 403
        print(
            "PASS: deny-by-default AWS fixture rejects other groups and AWS management actions",
            flush=True,
        )
        (CACHE / "evidence.json").write_text(
            json.dumps(
                {
                    "controller": chart["appVersion"],
                    "node": NODE,
                    "aws": "local protocol fixture, not AWS IAM or ALB traffic",
                    "calls": state.calls,
                    "result": "passed",
                },
                indent=2,
            )
        )
    finally:
        server.shutdown()
        if created:
            logs = kube(
                "logs", "deployment/aws-load-balancer-controller", "-n", "kube-system", ok=False
            )
            (CACHE / "controller.log").write_text(logs.stdout + logs.stderr)
            (CACHE / "aws-calls.json").write_text(json.dumps(state.calls))
            # Only the fixed, explicitly created disposable cluster; never namespaces
            # or objects from a user's current cluster/context.
            run("kind", "delete", "cluster", "--name", CLUSTER, timeout=120)


def policy_checks():
    # An object name or a diagnostic mentioning forbidden must never count as authorization evidence.
    try:
        rejected(
            "nonexistent fixture",
            subprocess.CompletedProcess(
                [], 1, "", 'Error from server (NotFound): ingresses "forbidden" not found'
            ),
        )
    except AssertionError:
        pass
    else:
        raise AssertionError("A missing resource was mistaken for an authorization denial")
    fixture = AWSFixture()
    for action in ("RegisterTargets", "DeregisterTargets"):
        assert fixture.authorized("elasticloadbalancing:" + action, ARN)
        for resource in (OTHER_ARN, ARN.replace("000000000000", "111111111111"), "*"):
            assert not fixture.authorized("elasticloadbalancing:" + action, resource)
    for action in (
        "CreateLoadBalancer",
        "DeleteLoadBalancer",
        "CreateTargetGroup",
        "ModifyTargetGroup",
        "ModifyListener",
        "CreateRule",
        "SetSecurityGroups",
        "AddTags",
    ):
        assert not fixture.authorized("elasticloadbalancing:" + action, ARN)
    for action in (
        "AuthorizeSecurityGroupIngress",
        "RevokeSecurityGroupIngress",
        "CreateSecurityGroup",
        "DeleteSecurityGroup",
    ):
        assert not fixture.authorized("ec2:" + action, "*")
    assert not fixture.authorized("sts:AssumeRole", "*")
    for prefix, action in (
        ("ec2", "DescribeVpcs"),
        ("ec2", "DescribeSecurityGroups"),
        ("elasticloadbalancing", "DescribeTargetGroups"),
        ("elasticloadbalancing", "DescribeTargetHealth"),
    ):
        assert fixture.authorized(prefix + ":" + action, "*")
    print(
        "PASS: deployed IAM template allows required reads and exact-group membership; rejects other groups and management actions"
    )


if __name__ == "__main__":
    policy_checks()
    if "--policy-only" not in sys.argv:
        main()
