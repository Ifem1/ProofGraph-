# Consensus design

`resolve_node` uses `run_nondet_unsafe` because semantic entailment is the load-bearing operation: validators must independently judge whether the bounded evidence, accepted parent conclusions, rule, and statement support one another.

The leader and each validator produce `verdict`, `rule_satisfied`, `blocker_class`, and `reason`. Consensus requires exact agreement on the first three fields; explanations are audit text and are intentionally excluded from equivalence. The custom validator reruns the adjudication from the canonical input and does not trust the leader's fields, so a well-formed but substantively different leader result is rejected.

Malformed, inconsistent, out-of-vocabulary, or oversized outputs fail closed. Disagreement causes the GenLayer execution to reject/rotate rather than mutate node state. Deterministic dependency checks, state transitions, revision increments, and storage writes happen outside the nondeterministic function. This makes consensus necessary: replacing it with one model would remove the independent validation of semantic derivations.

The canonical Studionet lifecycle observed `MAJORITY_AGREE` for deployment and all exercised writes. Validator receipts exposed `AGREE` and `IDLE` votes, and the negative semantic flow also exposed a `DISAGREE` vote while still reaching majority agreement. The live evidence is recorded in `docs/DEPLOYMENT.md`; no leader-only result was used.
