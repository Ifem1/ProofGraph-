# ProofGraph Design

## 1. Purpose

ProofGraph is a reusable semantic dependency primitive. It records conclusions as nodes, records explicit dependency edges, uses GenLayer consensus to adjudicate semantic derivations, and prevents downstream consumers from silently relying on conclusions whose premises stopped being valid.

The contract is intentionally domain-neutral. A node may represent a software-release condition, governance prerequisite, certification claim, research conclusion, grant milestone, compliance conclusion, or any other bounded proposition.

## 2. What GenLayer does

The non-deterministic question is narrow:

> Given the accepted parent conclusions, the declared derivation rule, bounded evidence, and optional revalidation context, is this node's statement materially supported?

The leader produces four fields:

- `verdict`: `SUPPORTED`, `NOT_SUPPORTED`, or `INDETERMINATE`
- `rule_satisfied`: boolean
- `blocker_class`: `NONE`, `DEPENDENCY`, `EVIDENCE`, `RULE`, or `AMBIGUITY`
- `reason`: short human-readable explanation

Validators independently rerun the semantic task. Consensus requires exact equality on the first three decision fields. `reason` is deliberately excluded from equivalence because wording can vary without changing the adjudication.

This means the validator is not a schema checker and does not merely inspect the leader's answer. It produces its own answer from the same adjudication input.

## 3. Deterministic responsibilities

The contract handles the following without LLM judgment:

- node identity and uniqueness
- input bounds
- dependency existence
- cycle prevention
- maximum fan-in and fan-out
- revision numbers
- parent validity gating
- node state transitions after consensus
- direct dependent invalidation
- parent revision bindings and bounded dependency-local ancestor validation
- consumption checks

No persistent state is written from inside a non-deterministic block.

## 4. DAG invariant

ProofGraph does not need graph traversal to detect cycles.

A new node may depend only on nodes that already exist, and node IDs are immutable. Therefore every edge points from a later-created node to an earlier-created node. A path can never return to a later-created node, so a cycle cannot be formed.

This also removes an otherwise unbounded cycle-detection traversal from write execution.

## 5. Bounded graph operations

Each node accepts at most eight dependencies. Each node accepts at most 32 direct dependents.

When an upstream node loses `VALID` status, only its direct valid children are marked `NEEDS_REVALIDATION`. The contract deliberately does not recursively traverse every descendant in one transaction.

Why: an attacker could otherwise build a very large descendant tree and make one revalidation trigger unbounded work. Propagation is instead incremental: when a stale child is resolved, its own direct children are affected if necessary.

## 6. Node lifecycle

`PENDING` means no final positive or negative semantic conclusion is currently safe to consume.

`VALID` means consensus returned `SUPPORTED` and all dependencies were valid at resolution time.

`INVALID` means consensus returned `NOT_SUPPORTED`.

`NEEDS_REVALIDATION` means a deterministic prerequisite failed or an upstream dependency changed after the node had been valid.

`INDETERMINATE` maps to `PENDING`, not `VALID` or `INVALID`, because ambiguity should not be silently converted into a categorical decision.

### Effective validity and stale descendants

Stored `VALID` is not sufficient for consumption. Each resolved node records its direct parent revisions and a creation-time depth bounded by `MAX_DEPTH=16`. `is_valid` and `can_consume` walk only that node's recorded ancestor bindings and fail closed on any missing, non-VALID, or revision-mismatched ancestor. Re-resolving one branch cannot invalidate unrelated branches; recovery requires explicit re-resolution from the changed parent downward.

## 7. Revision semantics

Every call to `resolve_node` increments the node revision, including deterministic dependency-blocked resolutions. Consumers may call:

```python
can_consume(node_id, minimum_revision)
```

This allows a downstream contract to require a conclusion to be valid and to have been adjudicated at or after a revision threshold selected by that consumer.

The immutable semantic specification is exposed as `spec_hash`, and each resolution records `adjudication_input_hash`. Caller-supplied `context` remains audit metadata only and is deliberately excluded from semantic adjudication.

## 8. Evidence model

Evidence is intentionally bounded text supplied at node creation. Optional `context` is bounded text supplied for a particular resolution/revalidation and stored as `last_context`.

ProofGraph does not claim that caller-supplied evidence is authentic merely because it exists. The semantic rule should state what the evidence must establish, and validators decide whether the supplied material actually establishes the node statement.

For applications requiring externally fetched evidence, a consuming system can place normalized source extracts or attestations into the evidence/context field, or extend the primitive with domain-specific source fetching while retaining the same graph/state design.

## 9. Threat model

### Fabricated or irrelevant evidence

Mitigation: semantic adjudication explicitly requires the evidence and premises to satisfy the declared rule. Plausible prose is not sufficient.

### Leader hallucination

Mitigation: validators independently rerun the task and compare material decision fields.

### Validator wording differences

Mitigation: free-form `reason` is not part of equivalence.

### Cyclic dependencies

Mitigation: dependencies must pre-exist the node, creating a construction-time DAG invariant.

### Duplicate dependencies

Mitigation: rejected deterministically.

### Graph amplification / gas-style denial of service

Mitigation: fan-in and direct fan-out are bounded, and invalidation is one-hop per transaction.

### Silent use of stale conclusions

Mitigation: a formerly valid direct child becomes `NEEDS_REVALIDATION` when an upstream valid node loses validity. `is_valid` and `can_consume` then return false.

### Ambiguous semantic questions

Mitigation: validators have an explicit `INDETERMINATE` outcome rather than being forced into yes/no.

## 10. Non-goals

ProofGraph is not:

- a generic knowledge graph database
- a truth oracle for arbitrary unbounded internet claims
- a recursive theorem prover
- a frontend application
- a reputation system
- a replacement for deterministic conditions that can already be expressed in normal code

Its purpose is specifically to compose bounded semantic judgments into reusable dependency-aware contract state.
