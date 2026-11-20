# Runtime Boundary Experiments

An IBC Labs repository for reproducible, bounded studies of what instrumented interfaces in text-based LLM and agent applications do—and do not—establish about an interaction.

**Status:** EXP-001 is under preparation. This branch is for review; the repository is not yet a public participant release.

## EXP-001 — Information hiding and runtime visibility

**Research question:** How does an observer's access to evidence at defined application boundaries constrain what can defensibly be claimed about application execution?

The study draws on David Parnas's information-hiding principle, but **does not assume information hiding prevents observability**. Modules can hide implementation decisions while exposing specifically designed operational evidence. We vary an application input to prompt assembly; we do not experimentally manipulate Parnas's design principle.

### Four snapshots

| Snapshot | Capture | Evidence limitation |
| --- | --- | --- |
| 1 — Ingress | Exact synthetic request bytes, byte digest, allowlisted metadata, parsed request | No direct evidence of later assembly or execution |
| 2 — Pre-inference | Client-assembled messages, selected route, tokenizer *declaration*, versioned configuration | No proof of hidden provider configuration or effective tokenizer |
| 3 — Participation | Local adapter invocation/return; optional authorized HTTP receipts | No comprehensive evidence of remote internal participants |
| 4 — Egress | App answer and response metadata | No automatic proof of correctness, completeness, or causality |

Every snapshot explicitly separates `declared_configuration`, `observed_execution`, `inferred_participation`, and `unknowns`.

### Controlled comparison

- **Held constant:** exact synthetic ingress request, parser, adapter mode, configured model route, tokenizer declaration and relevant request parameters.
- **Changed:** prompt assembly version, resulting in a different client-assembled system message.
- **Compared:** captured boundary evidence and answer.
- **Interpretation:** the offline fixture uses a deliberately constructed *synthetic function, not an LLM*. Its differences demonstrate the recording protocol only. Any live HTTP mode is an opt-in, independently authorized extension and cannot verify provider-internal activity.

### Two observer perspectives

After the baseline A/B run, compare an observer with ingress and egress only against an observer with all four snapshots, using **the same recorded execution**. This is an evidence-access comparison, not a second execution. Withholding a snapshot from an observer does not establish that an internal component was absent.

## Running the participant kit

The EXP-001 Python scripts and templates are being reviewed for inclusion. The intended standard workflow uses Python 3.10+ and no third-party dependencies:

```bash
python boundary_probe.py --participant-id tester_01 --out my_results
python verify_results.py my_results
```

**These commands become runnable from a clone only after `boundary_probe.py` and `verify_results.py` are committed.** Do not treat this initial README as a complete runnable release.

## Reporting and privacy

Use only synthetic, non-sensitive inputs for public artifacts. Do not submit bearer tokens, authentication headers, customer records, real system prompts, private retrieved context, or raw production traces. Run locally and manually review every artifact before sharing. HTTP identifiers, endpoints and low-entropy hashes can also disclose information.

A local digest check establishes byte comparison within collected artifacts, **not** independent provenance, tamper-resistant evidence, complete participation or causal attribution. An HTTP response shows what the instrumented client received, not what occurred inside an opaque provider.

We welcome disconfirming examples, alternative interpretations and instrument proposals. Participant reports should state what was observed, what was configured, what is inferred and what remains unknown.

## Release checklist

- [x] Private IBC-Labs repository and existing GPL-3.0 license
- [x] Local synthetic fixture validation (structural consistency only)
- [ ] Review and commit participant kit, verifier and report template
- [ ] Review privacy and submission policy
- [ ] Verify clean-clone reproducibility
- [ ] Tag first protocol release
- [ ] Decide public visibility and cross-link from ibclabs.org

## Reference

D. L. Parnas, “On the Criteria To Be Used in Decomposing Systems into Modules,” *Communications of the ACM* (1972), https://doi.org/10.1145/361598.361623.

Research information: https://ibclabs.org/research/
