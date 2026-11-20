# Runtime Boundary Experiments

An IBC Labs repository for reproducible, bounded studies of what instrumented interfaces in text-based LLM and agent applications do—and do not—establish about an interaction.

**Status:** Initial offline participant protocol. This repository remains private while the first public release is prepared. No external replication or live-model result is claimed.

## EXP-001 — Information hiding and runtime visibility

**Research question:** How does an observer's access to evidence at defined application boundaries constrain what can defensibly be claimed about application execution?

The study draws on David Parnas's information-hiding principle, but **does not assume information hiding prevents observability**. Modules can hide implementation decisions while exposing specifically designed operational evidence. We vary an application input to prompt assembly; we do not experimentally manipulate Parnas's design principle.

### Four snapshots

| Snapshot | Capture | Evidence limitation |
| --- | --- | --- |
| 1 — Ingress | Exact synthetic request bytes, byte digest, allowlisted metadata, parsed request | No direct evidence of later assembly or execution |
| 2 — Pre-inference | Client-assembled messages, synthetic route label, explicit unused tokenizer, versioned configuration | No model or tokenizer is executed by this fixture |
| 3 — Participation | Recorded local synthetic function invocation and return | No provider call or external agent is part of this fixture |
| 4 — Egress | App answer and response metadata | No automatic proof of correctness, completeness, or causality |

Every snapshot explicitly separates `declared_configuration`, `observed_execution`, `inferred_participation`, and `unknowns`.

### Controlled comparison

- **Held constant:** exact synthetic ingress request, parser, adapter mode, configured model route, tokenizer declaration and relevant request parameters.
- **Changed:** prompt assembly version, resulting in a different client-assembled system message.
- **Compared:** captured boundary evidence and answer.
- **Interpretation:** the offline fixture uses a deliberately constructed *synthetic function, not an LLM*. Its differences demonstrate the recording protocol only. Live HTTP/model execution is outside this package and would require a separately documented extension.

### Two observer perspectives

After the baseline A/B run, compare an observer with ingress and egress only against an observer with all four snapshots, using **the same recorded execution**. This is an evidence-access comparison, not a second execution. Withholding a snapshot from an observer does not establish that an internal component was absent.

For the restricted observer, provide copies of snapshots 1 and 4 only; withhold snapshots 2 and 3, the manifest, comparison file, and source code. Those other materials disclose additional information. Record any prior knowledge and distinguish claims supported by the supplied records from claims based on that knowledge. This manual exercise is not a blinded study of human performance.

## Running the participant kit

The package has **no live model or HTTP mode**. It uses Python 3.10+ and no third-party dependencies. Access requires permission to this private repository until a public release is made.

On GitHub, choose **Code → Download ZIP**, extract it, and open a terminal in the extracted folder. Alternatively, clone the repository using your usual authenticated GitHub setup. Run:

```bash
python boundary_probe.py --participant-id tester_01 --out my_results
python verify_results.py my_results
```

If `python` is unavailable, use `python3` on macOS/Linux or `py -3` on Windows. The output directory contains:

- `run_A.json` and `run_B.json`: the four snapshots for each prompt variant.
- `comparison.json`: request/route/tokenizer equality, context difference, and answer comparison.
- `run_manifest.json`: participant pseudonym, protocol/configuration versions, and runtime declarations.

Expected: the request, route and tokenizer declarations match; assembled context and synthetic answer differ; verification returns `PASS`. UUIDs and capture times vary, so whole files are not expected to be byte-identical across sessions. Compare the named fields, not whole-run hashes.

The verifier checks the supported fixture's structure, digests, execution-record fields, and fixed configuration. A `PASS` is an internal consistency result, not independent evidence that an execution occurred. GitHub Actions checks the fixture and targeted malformed-evidence cases; the same tests run locally with `python -m unittest -v test_verify_results.py`.

## First session (about 50 minutes)

1. **0–10 minutes:** Confirm synthetic scope, choose a pseudonym, and identify who can inspect the resulting files.
2. **10–20 minutes:** Run the commands above; inspect each snapshot in run A.
3. **20–30 minutes:** Compare run B, confirm fixed fields, and inspect the changed system message.
4. **30–40 minutes:** Perform the two-observer exercise on copies of the same records.
5. **40–50 minutes:** Complete [PARTICIPANT_REPORT.md](PARTICIPANT_REPORT.md), including the protocol version, source commit, limitations and unresolved claims. Use [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) to review it.

## Reporting and privacy

Use only synthetic, non-sensitive inputs for public artifacts. Do not submit bearer tokens, authentication headers, customer records, real system prompts, private retrieved context, or raw production traces. Run locally and manually review every artifact before sharing. HTTP identifiers, endpoints and low-entropy hashes can also disclose information.

A local digest check establishes byte comparison within collected artifacts, **not** independent provenance, tamper-resistant evidence, complete participation or causal attribution. An HTTP response shows what the instrumented client received, not what occurred inside an opaque provider.

We welcome disconfirming examples, alternative interpretations and instrument proposals. Participant reports should state what was observed, what was configured, what is inferred and what remains unknown.

## Release checklist

- [x] Private IBC-Labs repository and existing GPL-3.0 license
- [x] Offline probe, verifier, and participant/reviewer templates
- [x] Successful original GitHub Actions checkout, fixture execution and verification ([run](https://github.com/IBC-Labs/runtime-boundary-experiments/actions/runs/44831551431))
- [x] Fresh-directory execution of files retrieved at the original PR commit and checked against their Git blob IDs
- [x] Targeted regression tests for malformed and inconsistent evidence
- [x] WordPress copy reviewed by the project owner; page remains a draft
- [ ] Complete WordPress visual review
- [ ] Tag first protocol release
- [ ] Decide public visibility and cross-link from ibclabs.org

Commit-specific automated results and the merge record are available in [pull request #1](https://github.com/IBC-Labs/runtime-boundary-experiments/pull/1).

## Reference

D. L. Parnas, “On the Criteria To Be Used in Decomposing Systems into Modules,” *Communications of the ACM* (1972), https://doi.org/10.1145/361598.361623.

Research information: https://ibclabs.org/research/

License: the existing [GNU GPL v3 license](LICENSE) is preserved.
