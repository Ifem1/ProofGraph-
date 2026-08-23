# Integration

A consuming Intelligent Contract can gate a deterministic action on a ProofGraph conclusion:

```python
proofs = gl.get_contract_at(proof_graph_address)
if not proofs.view().can_consume("release-ready-v1", 2):
    raise gl.vm.UserError("PROOF_NOT_CURRENTLY_CONSUMABLE")
```

Consumers should choose a minimum revision appropriate to their workflow, re-check the view in the same action that consumes the result, and treat every non-`VALID` state as a failure. The stable machine-readable surface is `get_node` (canonical JSON), `get_status`, `is_valid`, and `can_consume`.
