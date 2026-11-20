#!/usr/bin/env python3
"""EXP-001. Offline, synthetic, bounded boundary evidence fixture (not an LLM)."""
import argparse
import base64
import datetime
import hashlib
import json
import os
import platform
import re
import sys
import uuid
from pathlib import Path

PROTOCOL_VERSION = "external-participant-1.0"
CONFIG_VERSION = "boundary-fixture-1.1.0"
REQUEST = {"request_id": "synthetic-001", "question": "What is the status of order A-100?"}
REQUEST_BYTES = json.dumps(REQUEST, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
PROMPTS = {
    "A": ("prompt-short-v1", "You are a demo support assistant. Answer in one concise sentence."),
    "B": ("prompt-structured-v2", "You are a demo support assistant. Answer with STATUS and NEXT STEP labels."),
}

def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

def digest(data):
    return hashlib.sha256(data).hexdigest()

def snapshot(boundary, trace, declared, observed, inferred, unknowns):
    return {
        "boundary": boundary, "trace_id": trace,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "captured_by": "instrumented_local_fixture",
        "declared_configuration": declared, "observed_execution": observed,
        "inferred_participation": inferred, "unknowns": unknowns,
    }

def execute_synthetic(messages):
    """Deterministic fixture; no inference, tool call or HTTP request occurs."""
    if "STATUS and NEXT STEP" in messages[0]["content"]:
        return "STATUS: Not checked. NEXT STEP: Look up order A-100 in the order system."
    return "The order status has not been checked; query the order system."

def run(variant):
    trace = str(uuid.uuid4())
    parsed = json.loads(REQUEST_BYTES)
    ingress = snapshot(
        "1_ingress", trace,
        {"request_schema_version": "1.0", "input_classification": "synthetic_non_sensitive",
         "auth_required": False},
        {"raw_body_base64": base64.b64encode(REQUEST_BYTES).decode("ascii"),
         "raw_body_sha256": digest(REQUEST_BYTES), "raw_body_length": len(REQUEST_BYTES),
         "metadata_allowlist": {"content_type": "application/json", "source": "local_test_fixture"},
         "parsed_request": parsed, "auth_result": "not_tested_fixture"},
        [], ["No network ingress, authentication, authorization, or TLS tested."])
    version, instruction = PROMPTS[variant]
    messages = [{"role": "system", "content": instruction},
                {"role": "user", "content": parsed["question"]}]
    declared = {
        "config_version": CONFIG_VERSION, "prompt_assembly_version": version,
        "model_route_configured": "synthetic/function-v1",
        "tokenizer": {"name": None, "version": None, "status": "not_used_by_synthetic_function"},
        "temperature": "not_applicable",
    }
    assembly = snapshot(
        "2_pre_inference", trace,
        {**declared, "config_sha256": digest(canonical(declared))},
        {"actual_assembled_messages": messages,
         "assembled_context_sha256": digest(canonical(messages)),
         "selected_route_at_client_boundary": "synthetic/function-v1",
         "message_count": len(messages)},
        [], ["No LLM inference occurs in this synthetic run."])
    answer = execute_synthetic(messages)
    execution = snapshot(
        "3_execution_participation", trace,
        {"intended_executor": "local_synthetic_function",
         "requested_model_route": "synthetic/function-v1"},
        {"client_adapter_invoked": True, "client_adapter_returned": True,
         "execution_kind": "local_synthetic_function",
         "tools_called": [], "remote_inference": False},
        [], ["No inference, model, or external agent participated."])
    body = {"trace_id": trace, "answer": answer}
    egress = snapshot(
        "4_egress", trace,
        {"output_schema_version": "1.0", "output_content_type": "application/json"},
        {"output_body": body, "output_body_sha256": digest(canonical(body)),
         "output_bytes_length": len(canonical(body)),
         "response_metadata": {"status": 200, "content_type": "application/json",
                               "origin": "local_test_harness"}},
        [], ["Output alone cannot establish correctness or any hidden causal contribution."])
    return {"fixture": "synthetic_request", "variant": variant, "live": False,
            "trace_id": trace, "snapshots": [ingress, assembly, execution, egress]}

def compare(a, b):
    x, y = a["snapshots"], b["snapshots"]
    return {
        "controlled_change": "prompt_assembly_version_only_at_client_configuration",
        "request_sha256_same": x[0]["observed_execution"]["raw_body_sha256"] == y[0]["observed_execution"]["raw_body_sha256"],
        "configured_route_same": x[1]["declared_configuration"]["model_route_configured"] == y[1]["declared_configuration"]["model_route_configured"],
        "tokenizer_declaration_same": x[1]["declared_configuration"]["tokenizer"] == y[1]["declared_configuration"]["tokenizer"],
        "assembled_context_sha256_same": x[1]["observed_execution"]["assembled_context_sha256"] == y[1]["observed_execution"]["assembled_context_sha256"],
        "client_adapter_kinds": [x[2]["observed_execution"]["execution_kind"], y[2]["observed_execution"]["execution_kind"]],
        "answers_same": x[3]["observed_execution"]["output_body"]["answer"] == y[3]["observed_execution"]["output_body"]["answer"],
        "claim_limit": "A/B illustrates fixture recording only; no provider inference, causal attribution, or completeness proved.",
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant-id", default="anonymous")
    parser.add_argument("--out", default="boundary_results")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", args.participant_id):
        parser.error("Use a pseudonym of 1-40 letters/digits/_/-")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        out.chmod(0o700)
    a, b = run("A"), run("B")
    diff = compare(a, b)
    manifest = {
        "protocol_version": PROTOCOL_VERSION, "participant_id": args.participant_id,
        "run_type": "offline_synthetic_fixture",
        "captured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python_version": platform.python_version(), "platform_family": sys.platform,
        "experiment_variable": "prompt_assembly_version",
        "control_request_sha256": digest(REQUEST_BYTES),
        "config_version": CONFIG_VERSION, "model_route_declared": "synthetic/function-v1",
        "tokenizer_declared": {"name": None, "version": None, "verified": False},
        "network_used": False, "local_authentication_tested": False,
        "provider_internals_observed": False,
        "limitations": ["No proof of execution completeness", "No attribution of causal contribution",
                        "No real model was executed"],
        "files": ["run_A.json", "run_B.json", "comparison.json"],
    }
    for name, item in (("run_A.json", a), ("run_B.json", b),
                       ("comparison.json", diff), ("run_manifest.json", manifest)):
        file = out / name
        file.write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if os.name == "posix":
            file.chmod(0o600)
    print(json.dumps({"result_directory": str(out), "summary": diff}, indent=2))

if __name__ == "__main__":
    main()
