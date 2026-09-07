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
ARN = (
    "arn:aws:elasticloadbalancing:us-east-1:000000000000:targetgroup/approved-api/0123456789abcdef"
)
OTHER_ARN = ARN.replace("approved-api", "unapproved")
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


def binding():
    return obj(
        "elbv2.k8s.aws/v1beta1",
        "TargetGroupBinding",
        "approved-api",
        {
            "targetGroupARN": ARN,
            "targetType": "ip",
            "ipAddressType": "ipv4",
            "vpcID": VPC,
            "targetGroupProtocol": "HTTP",
            "serviceRef": {"name": "approved-api", "port": 8000},
        },
    )


def candidate_rbac():
    docs = list(
        yaml.safe_load_all(
            run("helm", "template", "bootstrap", "infra/bootstrap/ai-platform-bootstrap").stdout
        )
    )
    allowed = []
    for doc in docs:
        if not doc or doc["metadata"]["name"] not in {
            "ai-platform-load-balancer-discovery",
            "load-balancer-reconciler",
            "load-balancer-leader-election",
            "app-deployer",
        }:
            continue
        if doc and doc["kind"] in {"Role", "RoleBinding", "ClusterRole", "ClusterRoleBinding"}:
            if doc["metadata"]["name"] == "load-balancer-reconciler":
                for rule in doc.get("rules", []):
                    if "ingresses" in rule["resources"]:
                        rule["verbs"] = ["get", "list", "watch"]
                if "rules" in doc:
                    doc["rules"] = [
                        r
                        for r in doc["rules"]
                        if not set(r["resources"])
                        & {"ingresses/status", "targetgroupbindings", "targetgroupbindings/status"}
                    ]
                    doc["rules"].extend(
                        [
                            {
                                "apiGroups": ["elbv2.k8s.aws"],
                                "resources": ["targetgroupbindings"],
                                "verbs": ["get", "list", "watch"],
                            },
                            {
                                "apiGroups": ["elbv2.k8s.aws"],
                                "resources": ["targetgroupbindings", "targetgroupbindings/status"],
                                "resourceNames": ["approved-api"],
                                "verbs": ["patch", "update"],
                            },
                        ]
                    )
            allowed.append(doc)
    return allowed


def admission():
    # Native API-server enforcement; all identities including cluster-admin are
    # subject to policy until a trusted bootstrap owner changes the policy itself.
    specs = [
        (
            "platform-no-ingress",
            ["networking.k8s.io"],
            ["ingresses"],
            ["CREATE", "UPDATE"],
            [{"expression": "false", "message": "Terraform owns platform routing"}],
        ),
        (
            "platform-approved-targets",
            ["elbv2.k8s.aws"],
            ["targetgroupbindings"],
            ["CREATE", "UPDATE"],
            [
                {
                    "expression": "object.metadata.name == 'approved-api'",
                    "message": "Unapproved binding name",
                },
                {
                    "expression": "object.spec.targetGroupARN == '" + ARN + "' && "
                    "object.spec.serviceRef.name == 'approved-api' && object.spec.serviceRef.port == 8000 && "
                    "object.spec.targetType == 'ip' && object.spec.ipAddressType == 'ipv4' && "
                    "object.spec.vpcID == '"
                    + VPC
                    + "' && object.spec.targetGroupProtocol == 'HTTP'",
                    "message": "Binding must use the approved target group, service, port and VPC",
                },
                {
                    "expression": "!has(object.spec.networking) && !has(object.spec.targetGroupName) && "
                    "!has(object.spec.iamRoleArnToAssume) && !has(object.spec.assumeRoleExternalId) && "
                    "!has(object.spec.nodeSelector) && (!has(object.spec.multiClusterTargetGroup) || "
                    "!object.spec.multiClusterTargetGroup)",
                    "message": "Unsupported binding capability",
                },
                {
                    "expression": "request.operation != 'UPDATE' || object.spec == oldObject.spec",
                    "message": "Binding spec is immutable; replacement requires bootstrap review",
                },
            ],
        ),
    ]
    docs = []
    for name, groups, resources, operations, validations in specs:
        docs.append(
            obj(
                "admissionregistration.k8s.io/v1",
                "ValidatingAdmissionPolicy",
                name,
                {
                    "failurePolicy": "Fail",
                    "matchConstraints": {
                        "resourceRules": [
                            {
                                "apiGroups": groups,
                                "apiVersions": ["*"],
                                "operations": operations,
                                "resources": resources,
                            }
                        ]
                    },
                    "validations": validations,
                },
                namespace=None,
            )
        )
        docs.append(
            obj(
                "admissionregistration.k8s.io/v1",
                "ValidatingAdmissionPolicyBinding",
                name,
                {
                    "policyName": name,
                    "validationActions": ["Deny"],
                    "matchResources": {
                        "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": NS}}
                    },
                },
                namespace=None,
            )
        )
    return docs


class AWSFixture:
    def __init__(self):
        self.targets = set()
        self.calls = []
        self.denied = []
        self.fail_registration = False
        self.lock = threading.Lock()

    def respond(self, params):
        action = params.get("Action", [""])[0]
        arn = params.get("TargetGroupArn", [""])[0]
        with self.lock:
            self.calls.append(action)
            if (
                action in {"RegisterTargets", "DeregisterTargets", "DescribeTargetHealth"}
                and arn != ARN
            ):
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
                        "<TargetGroupName>approved-api</TargetGroupName><TargetType>ip</TargetType>"
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
        "forbidden" in result.stderr.lower() or "denied" in result.stderr.lower()
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
                obj("v1", "Namespace", NS, namespace=None),
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
                "ingressClass": "tgb-unmanaged",
                "createIngressClassResource": False,
                "ingressClassParams": {"create": False},
                "enableBackendSecurityGroup": False,
                "enableManageBackendSecurityGroupRules": False,
                "enableShield": False,
                "enableWaf": False,
                "enableWafv2": False,
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
        values["controllerConfig"]["featureGates"]["EndpointsFailOpen"] = False
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
        apply(admission())
        for name in ("platform-no-ingress", "platform-approved-targets"):
            policy = json.loads(kube("get", "validatingadmissionpolicy", name, "-o", "json").stdout)
            assert not policy.get("status", {}).get("typeChecking", {}).get("expressionWarnings"), (
                policy
            )
        service = obj(
            "v1",
            "Service",
            "approved-api",
            {"ports": [{"name": "http", "port": 8000, "targetPort": 8000}], "type": "ClusterIP"},
        )
        pod = obj(
            "v1",
            "Pod",
            "synthetic-pod",
            {
                "containers": [{"name": "pause", "image": "registry.k8s.io/pause:3.10.1"}],
                "nodeName": CLUSTER + "-control-plane",
                "readinessGates": [{"conditionType": "target-health.elbv2.k8s.aws/approved-api"}],
            },
        )
        apply([service, pod])
        kube(
            "wait",
            "pod/synthetic-pod",
            "-n",
            NS,
            "--for=jsonpath={.status.phase}=Running",
            "--timeout=90s",
        )
        slice_doc = obj("discovery.k8s.io/v1", "EndpointSlice", "approved-api")
        slice_doc.update(
            {
                "addressType": "IPv4",
                "ports": [{"name": "http", "protocol": "TCP", "port": 8000}],
                "endpoints": [
                    {
                        "addresses": ["10.244.0.10"],
                        "conditions": {"ready": True},
                        "targetRef": {"kind": "Pod", "name": "synthetic-pod", "namespace": NS},
                    }
                ],
            }
        )
        slice_doc["metadata"]["labels"] = {
            "kubernetes.io/service-name": "approved-api",
            "endpointslice.kubernetes.io/managed-by": "compatibility-fixture",
        }
        apply([slice_doc, binding()])
        wait_for("register approved pod target", lambda: state.targets == {("10.244.0.10", 8000)})
        wait_for(
            "controller status and checkpoint writes",
            lambda: (
                json.loads(
                    kube("get", "targetgroupbinding", "approved-api", "-n", NS, "-o", "json").stdout
                )
                .get("status", {})
                .get("observedGeneration")
                == 1
            ),
        )
        wait_for(
            "pod target health readiness gate",
            lambda: any(
                c["type"] == "target-health.elbv2.k8s.aws/approved-api" and c["status"] == "True"
                for c in json.loads(
                    kube("get", "pod", "synthetic-pod", "-n", NS, "-o", "json").stdout
                )
                .get("status", {})
                .get("conditions", [])
            ),
        )
        # Real Kubernetes authorizer denials, not just can-i or YAML assertions.
        for resource, name in [
            ("ingresses", "forbidden"),
            ("services", "approved-api"),
            ("endpointslices.discovery.k8s.io", "approved-api"),
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
            kube("delete", "targetgroupbindings", "approved-api", "-n", NS, "--as", SA, ok=False),
        )
        rejected(
            "app deployer mutate TGB",
            kube(
                "patch",
                "targetgroupbindings",
                "approved-api",
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
                "approved-api",
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
            ("serviceRef", {"name": "approved-api", "port": 9000}),
        ]:
            rejected(
                "bootstrap unauthorized " + key,
                kube(
                    "patch",
                    "targetgroupbindings",
                    "approved-api",
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
                "defaultBackend": {"service": {"name": "approved-api", "port": {"number": 8000}}},
            },
        )
        rejected("bootstrap create Ingress", apply([ingress], ok=False))
        # Readiness loss and endpoint churn must deregister as well as register.
        slice_doc["endpoints"] = []
        apply([slice_doc])
        wait_for("deregister removed endpoint", lambda: not state.targets)
        state.fail_registration = True
        slice_doc["endpoints"] = [
            {
                "addresses": ["10.244.0.11"],
                "conditions": {"ready": True},
                "targetRef": {"kind": "Pod", "name": "synthetic-pod", "namespace": NS},
            }
        ]
        baseline = state.calls.count("RegisterTargets")
        apply([slice_doc])
        wait_for(
            "temporary AWS failure exercised",
            lambda: state.calls.count("RegisterTargets") > baseline,
        )
        assert not state.targets
        state.fail_registration = False
        wait_for(
            "recover registration after AWS failure",
            lambda: state.targets == {("10.244.0.11", 8000)},
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
        kube("delete", "targetgroupbinding", "approved-api", "-n", NS, "--wait=false")
        wait_for(
            "delete cleans targets and removes finalizer after restart",
            lambda: (
                not state.targets
                and not json.loads(kube("get", "targetgroupbindings", "-n", NS, "-o", "json").stdout)["items"]
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


if __name__ == "__main__":
    main()
