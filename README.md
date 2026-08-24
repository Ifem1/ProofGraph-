# ProofGraph

**A reusable GenLayer Intelligent Contract primitive for dependency-aware semantic attestations.**

ProofGraph lets builders represent conclusions as nodes in a directed acyclic proof graph. Each node may depend on previously created nodes. GenLayer validators independently judge whether the accepted parent conclusions, the node's rule, and its bounded evidence materially support the proposed child conclusion. Deterministic dependency-local revision bindings and bounded ancestor validation make stale descendants non-consumable immediately, without recursively rewriting the whole graph.

ProofGraph is intentionally a **standalone Intelligent Contract**. It has no frontend and does not need one: other contracts, scripts, or GenLayer Studio can consume it directly.

## Why this primitive exists

Most adjudication contracts answer isolated questions. Real systems are compositional:

```text
[A: API is deployed] ----\
                         \
[B: tests pass] ----------> [D: release is ready]
                         /
[C: audit passes] -------/
```

If `B` later becomes invalid, `D` should no longer be silently treated as safe. ProofGraph makes those semantic dependencies explicit and gives downstream contracts a reusable `is_valid(node_id)` gate.

## GenLayer-native design

ProofGraph separates responsibilities deliberately:

- **Deterministic layer:** node IDs, DAG construction, dependency existence, bounded fan-in/fan-out, state transitions, revision counters, parent revision bindings, bounded depth, stale propagation, and read interfaces.
- **Non-deterministic layer:** semantic entailment. A leader LLM evaluates whether the parent conclusions + rule + evidence support the proposed node.
- **Validator layer:** validators independently rerun the same semantic task and compare only stable decision fields. Free-form reasoning is never used as an equivalence key.

The custom validator requires exact agreement on:

1. `verdict` — `SUPPORTED`, `NOT_SUPPORTED`, or `INDETERMINATE`
2. `rule_satisfied` — whether the declared derivation rule is met
3. `blocker_class` — `NONE`, `DEPENDENCY`, `EVIDENCE`, `RULE`, or `AMBIGUITY`

The `reason` may differ between models and is stored only as human-readable audit context.

This follows GenLayer's recommended leader/validator pattern: validators independently reproduce the decision and compare stable fields rather than raw prose.

## State model

Each node stores a canonical JSON record containing:

```text
id
statement
rule
dependencies[]
evidence
status                 PENDING | VALID | INVALID | NEEDS_REVALIDATION
verdict                UNRESOLVED | SUPPORTED | NOT_SUPPORTED | INDETERMINATE
rule_satisfied
blocker_class
reason
revision
```

### Status transitions

```text
create
  |
  v
PENDING --SUPPORTED----------> VALID
   |                              |
   |                              | upstream invalidation
   |                              v
   +--NOT_SUPPORTED----------> INVALID
   |
   +--INDETERMINATE----------> PENDING

VALID/INVALID/NEEDS_REVALIDATION --resolve_node()--> new adjudicated state
```

When a node changes from `VALID` to a non-valid state, every direct dependent is deterministically marked `NEEDS_REVALIDATION`. Repeating this process as affected nodes are resolved propagates invalidation through the graph without an unbounded recursive write.

## DAG invariant

A node can depend only on nodes that already exist. Node IDs are immutable and cannot be recreated. Therefore an edge can only point backward in creation order, making cycles impossible by construction.

## Contract interface

### Writes

```python
create_node(node_id, statement, rule, dependencies_json, evidence)
resolve_node(node_id, context)
```

`dependencies_json` must be a JSON array of unique node IDs. `context` is optional bounded audit metadata for that resolution; it is not part of the semantic adjudication input.

### Views

```python
get_node(node_id) -> str
get_dependents(node_id) -> str
is_valid(node_id) -> bool
can_consume(node_id, minimum_revision) -> bool
get_status(node_id) -> str
get_graph_stats() -> str
```

`can_consume` is designed for contract composition: consumers can require both a valid semantic conclusion and a minimum adjudication revision.

Each node record also exposes `spec_hash`, `resolved_parent_revisions`, `depth`, and `adjudication_input_hash`. The immutable statement/rule/dependency/evidence specification is hashed. A node is consumable only when its direct parent revisions and bounded ancestor chain still match.

## Example composition

A downstream release contract can gate an action on a ProofGraph node:

```python
proofs = gl.get_contract_at(proof_graph_address)
if not proofs.view().is_valid("release-ready-v1"):
    raise gl.vm.UserError("Required proof node is not valid")
```

The same primitive can support grants, software releases, governance, certification, compliance workflows, research provenance, supply-chain decisions, and autonomous-agent workflows.

## Repository layout

```text
contracts/ProofGraph.py      Intelligent Contract
tests/direct/                direct-mode contract and validator tests
examples/consumer.py         composition example
docs/DESIGN.md               invariants, threat model, consensus design
docs/TEST_PLAN.md            lifecycle and consensus test matrix
docs/CONSENSUS.md            reviewer-facing consensus specification
docs/SECURITY.md             threat model and fail-closed rules
docs/INTEGRATION.md          stable downstream-consumer interface
docs/DEPLOYMENT.md           verified deployment evidence (when available)
requirements.txt             development dependencies
gltest.config.yaml           GenLayer test configuration
```

## Local verification

Requires Python 3.12+.

```bash
python -m pip install -r requirements.txt
genvm-lint check contracts/ProofGraph.py
pytest tests/direct -v
```

Direct-mode tests use GenLayer's `genlayer-test` fixtures and mock LLM outputs so the leader and validator paths can be tested independently.

On Windows, the committed `tests/conftest.py` contains a narrow host-only compatibility shim for a `genlayer-test==0.29.2` temporary-stdin unlink error (`PermissionError: [WinError 32]`). It affects only the pytest process and does not change contract execution. With that shim, the local Direct Mode suite passes 18/18 on Python 3.12.10. The live Studionet lifecycle test is run explicitly with `GENLAYER_RUN_STUDIONET=1`.

## Submission fit

ProofGraph is not a thin LLM wrapper and not a one-off application. The reusable object is the graph itself: builders register semantic conclusions, express dependencies, adjudicate derivations under GenLayer consensus, and consume finalized nodes from other contracts. The deterministic DAG/state layer and the non-deterministic semantic consensus layer are both necessary for the primitive to work.

## License

MIT
