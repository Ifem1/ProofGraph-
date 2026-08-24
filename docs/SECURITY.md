# Security notes

ProofGraph protects the integrity of dependency-gated conclusions, not external assets or the truth of arbitrary internet claims.

Caller-supplied statements, rules, evidence, and context are bounded but untrusted. The immutable statement/rule/dependency/evidence specification is bound by `spec_hash`; context is stored for audit but is not part of the semantic adjudication input. The adjudication prompt labels them as input data and requires the model to treat embedded instructions as evidence, not authority. Structured output is strictly type-, range-, and consistency-checked; malformed or ambiguous output never becomes `VALID`.

Leader results are not trusted: validators independently adjudicate the same canonical input. A malicious validator majority remains outside this contract's protection. Downstream consumers must use `is_valid`/`can_consume`; effective validity checks bounded ancestor traversal and direct-parent revision bindings, so stale descendants fail closed without recursive writes and unrelated branches remain valid. `PENDING`, `INVALID`, and `NEEDS_REVALIDATION` are unsafe. No privileged bypass exists. Network authenticity, source provenance, and domain-specific evidence quality remain application responsibilities.
