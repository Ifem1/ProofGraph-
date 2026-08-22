# ProofGraph Test Plan

## Direct-mode coverage

The direct suite covers both deterministic graph mechanics and GenLayer consensus behavior.

| Area | Scenario | Expected result |
|---|---|---|
| Creation | root node | stored as `PENDING` |
| Creation | missing dependency | revert |
| Creation | duplicate node ID | revert |
| Creation | duplicate dependency | revert |
| Consensus | supported root | `VALID` |
| Consensus | unsupported root | `INVALID` |
| Consensus | ambiguous root | `PENDING` / `INDETERMINATE` |
| Dependency gating | unresolved parent | child becomes `NEEDS_REVALIDATION` without semantic execution |
| Derived proof | valid parent + supported derivation | child becomes `VALID` |
| Indexing | parent with child | child appears in direct-dependents index |
| Revalidation | valid parent later fails | direct valid child becomes `NEEDS_REVALIDATION` |
| Consumption | minimum revision met | `can_consume == true` |
| Consumption | minimum revision not met | `can_consume == false` |
| Validator equivalence | same semantic fields, different reason | agree |
| Validator equivalence | different verdict/blocker | disagree |

## Additional adversarial cases for Studio/Testnet

Before treating a deployment as production-ready, exercise these with heterogeneous validators:

1. **Near-boundary entailment** — evidence partially supports the rule; confirm `INDETERMINATE` is used rather than optimistic acceptance.
2. **Contradictory evidence** — strong evidence both for and against the statement.
3. **Prompt injection inside evidence** — evidence contains instructions telling the model to ignore the contract task. The validator should continue applying the contract rule.
4. **Long-but-bounded evidence** — near the 8,000-character limit.
5. **Eight-parent derivation** — maximum fan-in.
6. **32 direct children** — maximum fan-out, followed by an attempted 33rd child.
7. **Multi-level invalidation** — A -> B -> C. When A fails, B becomes stale; after resolving B while A is invalid, C should be marked stale if B had previously been valid.
8. **Leader/validator semantic disagreement** — verify leader rotation rather than acceptance.
9. **Malformed LLM JSON** — should fail/rotate, never write a semantic result.
10. **Inconsistent LLM object** — e.g. `SUPPORTED` with `rule_satisfied=false`; should be rejected before state mutation.

## Invariants

Reviewers/builders should be able to rely on these invariants:

- a node ID is immutable and unique;
- every dependency existed before its child was created;
- therefore the stored dependency graph is acyclic;
- `VALID` can only be written after all parents are `VALID` and semantic consensus returns `SUPPORTED`;
- `INDETERMINATE` is never consumable as valid;
- a direct child of a formerly valid node is not left `VALID` when that parent loses validity;
- nondeterministic functions never write persistent state;
- free-form explanation text cannot cause validators to disagree when all material decision fields agree.
