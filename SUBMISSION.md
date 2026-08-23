# ProofGraph — Submission Notes

## Category

Standalone GenLayer Intelligent Contract / reusable contract primitive.

## One-line purpose

ProofGraph is a dependency-aware semantic attestation primitive: it lets contracts compose GenLayer-adjudicated conclusions into an acyclic proof graph and automatically prevents downstream consumers from relying on conclusions whose prerequisites have become invalid.

## Why this is not a thin LLM wrapper

The LLM does one bounded job: determine whether a node's statement is materially supported by its declared rule, accepted parent conclusions, and evidence.

The contract itself provides the reusable infrastructure around that judgment:

- immutable node identity;
- DAG construction invariant;
- dependency indexing;
- bounded fan-in/fan-out;
- explicit lifecycle state;
- revision tracking;
- deterministic prerequisite checks;
- one-hop stale propagation;
- downstream consumption gates;
- custom independent validator logic.

Removing the consensus layer makes semantic derivations untrusted. Removing the deterministic graph/state layer makes the result a one-off AI answer instead of a composable contract primitive.

## Consensus logic reviewers should inspect

See `contracts/ProofGraph.py::resolve_node`.

The leader and every validator independently run the same adjudication task. The custom validator compares only the stable semantic decision fields:

- `verdict`
- `rule_satisfied`
- `blocker_class`

The free-form explanation is intentionally excluded from equivalence.

A validator that returns a different material decision disagrees. Malformed or internally inconsistent outputs also disagree rather than being accepted.

## State design reviewers should inspect

Each node has:

- immutable ID;
- statement;
- derivation rule;
- bounded dependency list;
- bounded evidence;
- lifecycle status;
- consensus verdict;
- blocker classification;
- audit explanation;
- revision counter;
- last revalidation context.

A separate direct-dependents index supports bounded invalidation.

## Key invariant

A new node can only depend on existing nodes. Since node IDs cannot be recreated, every dependency edge points backward in creation order. The graph is therefore acyclic without requiring an unbounded traversal.

## Meaningful invalidation behavior

Suppose:

```text
A: API deployed
B: tests pass
C: audit passes
       \\ | /
     D: release ready
```

If `B` is later re-adjudicated and loses `VALID` status, any direct valid node that depends on `B` becomes `NEEDS_REVALIDATION`. A consumer calling `is_valid(D)` can no longer treat that conclusion as safe.

Propagation is deliberately one hop per resolution to avoid an attacker making a single write recursively traverse an unbounded descendant graph.

## Reuse examples

The same contract can underpin:

- software-release gates;
- grant milestone dependencies;
- governance prerequisites;
- compliance/certification workflows;
- research provenance conclusions;
- autonomous-agent workflow gates;
- supply-chain decision graphs.

`examples/consumer.py` demonstrates another Intelligent Contract synchronously consuming a ProofGraph node.

## Verification

Run:

```bash
python -m pip install -r requirements.txt
genvm-lint check contracts/ProofGraph.py
pytest tests/direct -v
```

The direct test suite covers graph creation, dependency failures, positive/negative/indeterminate semantic outcomes, stale propagation, revision-gated consumption, and validator agreement/disagreement behavior.

## Evidence status

The contract passes GenVM linter 0.10.0 and SDK validation. The Direct Mode suite passes 12/12 with the committed Windows-only test-runner shim described in `tests/conftest.py`. No canonical Studionet address or runtime transaction evidence is present yet; see `docs/DEPLOYMENT.md`.
