#!/usr/bin/env python3
"""Structural and digest consistency checks. Not authentication or provenance."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

EXPECTED = ["1_ingress", "2_pre_inference", "3_execution_participation", "4_egress"]

def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

def digest(data):
    return hashlib.sha256(data).hexdigest()

def verify(folder):
    issues = []
    files = ["run_A.json", "run_B.json", "comparison.json", "run_manifest.json"]
    try:
        a, b, comparison, manifest = [json.loads((folder / name).read_text(encoding="utf-8")) for name in files]
    except (OSError, ValueError) as error:
        return ["Results missing or unreadable: " + type(error).__name__]
    for label, run in (("A", a), ("B", b)):
        snaps = run.get("snapshots", [])
        if [s.get("boundary") for s in snaps] != EXPECTED:
            issues.append(label + ": incorrect snapshot sequence")
            continue
        if len({s.get("trace_id") for s in snaps}) != 1 or snaps[0].get("trace_id") != run.get("trace_id"):
            issues.append(label + ": inconsistent trace IDs")
        for snap in snaps:
            for key in ("declared_configuration", "observed_execution", "inferred_participation", "unknowns"):
                if key not in snap:
                    issues.append(label + ": missing evidence category " + key)
        try:
            ingress = snaps[0]["observed_execution"]
            raw = base64.b64decode(ingress["raw_body_base64"], validate=True)
            if digest(raw) != ingress["raw_body_sha256"] or len(raw) != ingress["raw_body_length"]:
                issues.append(label + ": ingress digest/length mismatch")
            if json.loads(raw) != ingress["parsed_request"]:
                issues.append(label + ": parsed ingress mismatch")
            assembly = snaps[1]["observed_execution"]
            if digest(canonical(assembly["actual_assembled_messages"])) != assembly["assembled_context_sha256"]:
                issues.append(label + ": assembled context digest mismatch")
            pre = snaps[1]["declared_configuration"]
            config = {k: v for k, v in pre.items() if k != "config_sha256"}
            if digest(canonical(config)) != pre["config_sha256"]:
                issues.append(label + ": declared configuration digest mismatch")
            egress = snaps[3]["observed_execution"]
            if digest(canonical(egress["output_body"])) != egress["output_body_sha256"]:
                issues.append(label + ": egress digest mismatch")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            issues.append(label + ": malformed evidence fields")
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
        if comparison.get(key) != value:
            issues.append("comparison mismatch: " + key)
    if not checks["request_sha256_same"] or not checks["configured_route_same"] or not checks["tokenizer_declaration_same"]:
        issues.append("controlled-variable invariant failed")
    if checks["assembled_context_sha256_same"]:
        issues.append("prompt assembly did not change recorded context")
    if x[1]["declared_configuration"]["prompt_assembly_version"] == y[1]["declared_configuration"]["prompt_assembly_version"]:
        issues.append("prompt assembly version unchanged")
    if manifest.get("control_request_sha256") != x[0]["observed_execution"]["raw_body_sha256"]:
        issues.append("manifest request digest mismatch")
    if manifest.get("experiment_variable") != "prompt_assembly_version":
        issues.append("manifest changed-variable mismatch")
    if manifest.get("run_type") != "offline_synthetic_fixture" or manifest.get("network_used") is not False:
        issues.append("fixture mode not as expected")
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
