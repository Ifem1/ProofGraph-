# Deployment evidence

## Canonical Studionet deployment

- Address: `0xf41e4b81E7486E3f879A8e793d57e3301283839b`
- Deployment transaction: `0x16c3f281a565d35d70038b884eaacae12dda6d348fb60dfef4fbceef71e5cb3`
- Source commit: `4f232bd` (`fix: use dependency-local validity bindings`)
- Result/lifecycle: `MAJORITY_AGREE` / `FINALIZED`
- Tooling: Python 3.12.10, genlayer-test 0.29.2, genvm-linter 0.10.0

## Source parity

`gen_getContractCode` returned 15,062 bytes. Normalized local LF source and deployed source are identical:

- Local normalized SHA-256: `01d39ee2bc523bd571bb57c5495c20fb26b7690cbd0f92080b792c6b3a793545`
- Deployed SHA-256: `01d39ee2bc523bd571bb57c5495c20fb26b7690cbd0f92080b792c6b3a793545`
- Comparison: `True`
- Git blob: `a17ee1ebb6a98252971e485d1571bf67b5832ad4`

No contract-source changes followed commit `4f232bd`.

## Finalized live lifecycle

The Studionet integration passed (`1 passed`). Every transaction below was accepted with `MAJORITY_AGREE` and confirmed `FINALIZED` via `gen_getTransactionStatus`.

| Flow | Transaction | Observed result |
|---|---|---|
| Deploy | `0x16c3f281a565d35d70038b884eaacae12dda6d348fb60dfef4fbceef71e5cb3` | finalized |
| Create A | `0x99fe51daa576e887f2e10850ba120fc52355c0a93d5f8606089b0e2886680114` | finalized |
| Resolve A | `0x8ecf26776628b6ccaab30637ec78e867ab3f4df944e478153f0608ff6c3dfb41` | A `VALID`, finalized |
| Create B -> A | `0x37db4a7614e9453b02386201bea6e5c980dc42edd54ffe021e8360feb53dbbfd` | finalized |
| Resolve B | `0x67d477a8f1446fa13d00d5d44b9fb1d0a995caef01eb3948b2e87aebac7fbef4` | B `VALID`, finalized |
| Create C -> B | `0x702bd249f426c79425fdd47ee32a42773beb4ff3da3fb5e451580c8b1797ccb6` | finalized |
| Resolve C | `0xa7d5547fc0f287a01cf815b3ede18964e1e764dc2d8dd30fd39427e0915c5549` | C `VALID`, finalized |
| Re-resolve A | `0x58c9c0f0e369ca4621cd97478e11c90285c60fa456d6174172511897dade3e25` | B/C `is_valid=false`, finalized |
| Recover B | `0xaaf603576f7782b8c358b65589dc3eb4e748da311b5d2a0cd932835a2e248c37` | B recovered, finalized |
| Recover C | `0x736080112923f9f36642540b4dd2ffa2455919ab4452623d73817ced84ff14f` | C `VALID`, finalized |
| Create negative N | `0x8803a3ae27843e1cde4039f0aebfc2467898878d0cd61c847b7e6b3c1591c92b` | finalized |
| Resolve negative N | `0x3b85a785efc9de5f436840bcd1c28cdcf1dcb4da2599f4022afdd8926f6fd404` | majority agree, one disagree, finalized |

## Deprecated deployment

`0xAF78D769aE603b54f57413751c9111F312347A2A` (deployment `0xe3b613830db88703b779810067d4cc2690096d1c0fc95c553a4b08a481d42474`) is audit history only. It used the superseded contract-wide validity-epoch design and is not canonical.
