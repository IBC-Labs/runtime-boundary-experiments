#!/usr/bin/env python3
"""Check the offline evidence contract and digests, not authenticity or provenance."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

EXPECTED = ["1_ingress", "2_pre_inference", "3_execution_participation", "4_egress"]
FILES = ["run_A.json", "run_B.json", "comparison.json", "run_manifest.json"]
CONTROLLED_CHANGE = "prompt_assembly_version_only_at_client_configuration"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_run(run, label):
    """Validate shapes before reading nested fields; stop at a bounded error."""
    require(run["variant"] == label, "variant does not match filename")
    require(run["fixture"] == "synthetic_request" and run["live"] is False,
            "run is not the offline synthetic fixture")
    trace = run["trace_id"]
    require(isinstance(trace, str) and bool(trace), "missing or invalid trace ID")
    snaps = run["snapshots"]
    require(isinstance(snaps, list) and len(snaps) == 4, "incorrect snapshot sequence")
    require(all(isinstance(s, dict) for s in snaps), "snapshots must be objects")
    require([s["boundary"] for s in snaps] == EXPECTED, "incorrect snapshot sequence")
    for snap in snaps:
        require(snap["trace_id"] == trace, "inconsistent trace IDs")
        for key in ("declared_configuration", "observed_execution"):
            require(isinstance(snap[key], dict), key + " must be an object")
        for key in ("inferred_participation", "unknowns"):
            require(isinstance(snap[key], list)
                    and all(isinstance(item, str) for item in snap[key]),
                    key + " must be a list of strings")

    ingress, assembly, execution, egress = [s["observed_execution"] for s in snaps]
    require(isinstance(ingress["raw_body_base64"], str), "invalid ingress bytes")
    raw = base64.b64decode(ingress["raw_body_base64"], validate=True)
    require(digest(raw) == ingress["raw_body_sha256"], "ingress digest mismatch")
    require(type(ingress["raw_body_length"]) is int
            and len(raw) == ingress["raw_body_length"], "ingress length mismatch")
    require(isinstance(ingress["parsed_request"], dict)
            and json.loads(raw) == ingress["parsed_request"], "parsed ingress mismatch")
    require(isinstance(ingress["metadata_allowlist"], dict), "invalid ingress metadata")
    require(ingress["auth_result"] == "not_tested_fixture", "unexpected authentication result")

    pre = snaps[1]["declared_configuration"]
    for key in ("config_version", "prompt_assembly_version", "model_route_configured"):
        require(isinstance(pre[key], str) and bool(pre[key]), "invalid " + key)
    require(isinstance(pre["tokenizer"], dict), "invalid tokenizer declaration")
    require("name" in pre["tokenizer"] and "version" in pre["tokenizer"],
            "incomplete tokenizer declaration")
    require("temperature" in pre, "missing temperature declaration")
    config = {k: v for k, v in pre.items() if k != "config_sha256"}
    require(digest(canonical(config)) == pre["config_sha256"], "declared configuration digest mismatch")
    messages = assembly["actual_assembled_messages"]
    require(isinstance(messages, list) and len(messages) == 2
            and all(isinstance(m, dict) for m in messages), "invalid assembled messages")
    require([m["role"] for m in messages] == ["system", "user"]
            and all(isinstance(m["content"], str) for m in messages),
            "invalid assembled message roles or content")
    require(messages[1]["content"] == ingress["parsed_request"]["question"],
            "assembled user message differs from parsed request")
    require(digest(canonical(messages)) == assembly["assembled_context_sha256"],
            "assembled context digest mismatch")
    require(type(assembly["message_count"]) is int
            and assembly["message_count"] == len(messages), "message count mismatch")
    require(assembly["selected_route_at_client_boundary"] == pre["model_route_configured"],
            "selected route differs from declared route")

    intended = snaps[2]["declared_configuration"]
    require(intended["intended_executor"] == "local_synthetic_function"
            and intended["requested_model_route"] == pre["model_route_configured"],
            "executor declaration mismatch")
    require(execution["client_adapter_invoked"] is True
            and execution["client_adapter_returned"] is True,
            "missing successful adapter invocation/return evidence")
    require(execution["execution_kind"] == "local_synthetic_function"
            and execution["tools_called"] == [] and execution["remote_inference"] is False,
            "execution evidence contradicts offline fixture mode")

    body = egress["output_body"]
    require(isinstance(body, dict) and isinstance(body["answer"], str), "invalid output body")
    require(body["trace_id"] == trace, "egress body trace ID mismatch")
    output = canonical(body)
    require(digest(output) == egress["output_body_sha256"], "egress digest mismatch")
    require(type(egress["output_bytes_length"]) is int
            and len(output) == egress["output_bytes_length"], "egress length mismatch")
    require(isinstance(egress["response_metadata"], dict), "invalid response metadata")


def verify(folder):
    try:
        documents = [json.loads((folder / name).read_text(encoding="utf-8")) for name in FILES]
    except (OSError, ValueError) as error:
        return ["Results missing or unreadable: " + type(error).__name__]
    issues = [name + ": top-level JSON must be an object"
              for name, doc in zip(FILES, documents) if not isinstance(doc, dict)]
    if issues:
        return issues
    a, b, comparison, manifest = documents
    for label, run in (("A", a), ("B", b)):
        try:
            validate_run(run, label)
        except KeyError as error:
            issues.append(label + ": missing field " + str(error))
        except (TypeError, ValueError) as error:
            issues.append(label + ": malformed evidence (" + str(error) + ")")
    if issues:
        return issues
    x, y = a["snapshots"], b["snapshots"]
    checks = {
        "request_sha256_same": x[0]["observed_execution"]["raw_body_sha256"] == y[0]["observed_execution"]["raw_body_sha256"],
        "configured_route_same": x[1]["declared_configuration"]["model_route_configured"] == y[1]["declared_configuration"]["model_route_configured"],
        "tokenizer_declaration_same": x[1]["declared_configuration"]["tokenizer"] == y[1]["declared_configuration"]["tokenizer"],
        "assembled_context_sha256_same": x[1]["observed_execution"]["assembled_context_sha256"] == y[1]["observed_execution"]["assembled_context_sha256"],
        "answers_same": x[3]["observed_execution"]["output_body"]["answer"] == y[3]["observed_execution"]["output_body"]["answer"],
    }
    for key, value in checks.items():
        if comparison.get(key) is not value:
            issues.append("comparison mismatch: " + key)
    if comparison.get("controlled_change") != CONTROLLED_CHANGE:
        issues.append("comparison changed-variable mismatch")
    kinds = [s[2]["observed_execution"]["execution_kind"] for s in (x, y)]
    if comparison.get("client_adapter_kinds") != kinds:
        issues.append("comparison mismatch: client_adapter_kinds")
    invariant_configs = [{k: v for k, v in s[1]["declared_configuration"].items()
                          if k not in ("prompt_assembly_version", "config_sha256")}
                         for s in (x, y)]
    if invariant_configs[0] != invariant_configs[1] or not checks["request_sha256_same"]:
        issues.append("controlled-variable invariant failed")
    if checks["assembled_context_sha256_same"]:
        issues.append("prompt assembly did not change recorded context")
    if x[1]["declared_configuration"]["prompt_assembly_version"] == y[1]["declared_configuration"]["prompt_assembly_version"]:
        issues.append("prompt assembly version unchanged")
    if a["trace_id"] == b["trace_id"]:
        issues.append("A and B must have distinct trace IDs")
    if manifest.get("control_request_sha256") != x[0]["observed_execution"]["raw_body_sha256"]:
        issues.append("manifest request digest mismatch")
    if manifest.get("experiment_variable") != "prompt_assembly_version":
        issues.append("manifest changed-variable mismatch")
    if manifest.get("run_type") != "offline_synthetic_fixture" or manifest.get("network_used") is not False:
        issues.append("fixture mode not as expected")
    for key, config_key in (("config_version", "config_version"),
                            ("model_route_declared", "model_route_configured")):
        if manifest.get(key) != x[1]["declared_configuration"][config_key]:
            issues.append("manifest declaration mismatch: " + key)
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", default="boundary_results")
    args = parser.parse_args()
    errors = verify(Path(args.folder))
    print(json.dumps({"status": "FAIL" if errors else "PASS", "issues": errors,
                      "caution": "Local structural consistency only; no provenance, real inference, completeness or causality."}, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
