# EXP-001 Reviewer Guide

This is a bounded methodological experiment, not a provider benchmark. The offline executor is synthetic and intentionally designed to show output differences following a prompt-assembly change.

## Review criteria

1. **Controls:** Is the exact request byte hash the same in A and B? Were declared route and tokenizer held constant? Does prompt assembly differ?
2. **Provenance:** Are evidence files tied to a protocol version and Git commit? Do not treat local checksums as trusted third-party provenance.
3. **Boundaries:** Are ingress, pre-inference, execution participation, and egress distinguishable in the report?
4. **Claim classification:** Are configuration declarations, observed records, participation inferences, and unknowns kept separate?
5. **Access restriction:** Does withholding a snapshot from the observer reduce supportable claims without implying any component was absent?
6. **Privacy:** Are submissions synthetic and inspected for secrets, endpoints, private prompts, and inadvertent identifiers?
7. **Limitations:** Does the report avoid claiming provider-internal completeness, correct answers, actual tokenizer use, model weights, or full causal explanation?

A **reproduced local PASS** means only that the same protocol fixture and structural checks ran successfully under stated conditions. A contradictory report should not be discarded simply because it differs from the reference expectations; preserve the discrepancy and investigate the protocol, implementation and environmental differences.

## Submission

Submit the reviewed participant report as a pull request or issue after the first public protocol release. Do not submit unredacted live run bundles. Note redactions, protocol version, environment, and any deviation from standard steps.
