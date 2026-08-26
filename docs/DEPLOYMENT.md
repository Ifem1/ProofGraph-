# Deployment evidence

## Canonical Studionet deployment

- Address: `0xa06e0035BbC8b0f2Eb4A0F7Ca0F4b3d266209DfB`
- Deployment transaction: `0xd8127bd278ab5a151c6e3660f4b1e3d7ef39966e6addef10c7b3491ca74961e3`
- Source commit: `92513bbb9607e47c59ceb6474fba090c4a3a25f5`
- Result/lifecycle: `MAJORITY_AGREE` / `FINALIZED`

## Steward-requested no-op protection

`context` is audit metadata, not semantic input. When canonical adjudication input and decision are unchanged, `resolve_node` preserves the node revision and parent bindings. An arbitrary caller therefore cannot invalidate descendants by repeating a no-op resolution. A materially different semantic result still changes revision and invalidates affected dependents.

## Source parity

`gen_getContractCode` returned 16,346 bytes. After normalizing local CRLF to LF, the deployed source is identical:

- Local normalized SHA-256: `4b9e93cd46d7dea60b1d47e0fb47a95cabb1d96124815dbaf9fe7c2f19218369`
- Deployed SHA-256: `4b9e93cd46d7dea60b1d47e0fb47a95cabb1d96124815dbaf9fe7c2f19218369`
- Comparison: `True`
- Git blob: `111f93c7ab23a670350c4be65ee5936e35c8cb27`

## Finalized lifecycle receipts

The live integration test passed (`1 passed`). All listed transactions were accepted with `MAJORITY_AGREE` and confirmed `FINALIZED` using `gen_getTransactionStatus`.

| Flow | Transaction | Observed result |
|---|---|---|
| Deploy | `0xd8127bd278ab5a151c6e3660f4b1e3d7ef39966e6addef10c7b3491ca74961e3` | finalized |
| Create A | `0x1353bd7b8141e1bc79fca777ca54d0e46c5b8032f97ccad06e70d598ee3c5257` | finalized |
| Resolve A | `0xbda0a647e3351091b9c7cef5026f8990f923dcfa7a61c639d5cf0e2949cfe98f` | A `VALID`, finalized |
| Create B -> A | `0x6f0f06390700789a51a6c354d51ba4ff46faefed57a190a18d3ad34a9a78a29b` | finalized |
| Resolve B | `0x29db144c8fb90f64f62bbd92ec7a1fddbf6e6c7a090c679989765ca486af86f7` | B `VALID`, finalized |
| Create C -> B | `0x9611b44506780a637acfaedbd289e70c820970088e92b3a7ee6b795bf5c636d4` | finalized |
| Resolve C | `0x2f6fdf7cf2cfe910948dc3772790f63932fb833b5859e474ca6516075354ae91` | C `VALID`, finalized |
| No-op re-resolve A | `0xa5ad5e62664c3683dd0275c1fd4e5fd2808604791ab55c78d21c1ee1fb136c0f` | B/C remained valid and consumable, finalized |
| Create negative N | `0x28398993863d57888e85d526bb9c443b53d45c08666c1bade78079d29eabb186` | finalized |
| Resolve negative N | `0x7c9e4b135454ba56dc46d94649ef654678ad7d326eeefab9b6f5cb058f8c8a09` | majority agree; one disagree; finalized |

## Deprecated deployments

The prior addresses `0xf41e4b81E7486E3f879A8e793d57e3301283839b` and `0xAF78D769aE603b54f57413751c9111F312347A2A` are audit history only. The former predates idempotent re-resolution; the latter used the superseded contract-wide epoch design. Neither is canonical.
