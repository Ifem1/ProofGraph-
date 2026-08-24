# Deployment evidence

## Canonical deployment

- Network: hosted Studionet (`https://studio.genlayer.com/api`)
- Deployment source commit: `0cb1e396b60a0dfc9080278d091cd0c0e69a8c6a`
- Contract: `contracts/ProofGraph.py`
- Canonical address: [`0xAF78D769aE603b54f57413751c9111F312347A2A`](https://explorer-studio.genlayer.com/address/0xAF78D769aE603b54f57413751c9111F312347A2A)
- Deployment transaction: [`0xe3b613830db88703b779810067d4cc2690096d1c0fc95c553a4b08a481d42474`](https://explorer-studio.genlayer.com/tx/0xe3b613830db88703b779810067d4cc2690096d1c0fc95c553a4b08a481d42474)
- Deployment result: `MAJORITY_AGREE`
- Deployment lifecycle: `FINALIZED` (verified with `gen_getTransactionStatus`)
- Tooling: `genlayer-test 0.29.2`, Python 3.12.10

## Source parity

Studionet `gen_getContractCode` returned the deployed source as base64. The local working-tree file uses CRLF line endings while the returned source uses LF. Raw byte digests therefore differ, but normalized UTF-8 content is identical:

- Local raw SHA-256: `634611976529b0a10166c9063f70fd3fb55114900e7879c390d254f87a740650`
- Deployed raw SHA-256: `05c3a38637d5f0f4bcaaead4dd2584462123ff54b9c5fb9eb8f79a14f8f1aa79`
- Local normalized LF SHA-256: `05c3a38637d5f0f4bcaaead4dd2584462123ff54b9c5fb9eb8f79a14f8f1aa79`
- Deployed normalized LF SHA-256: `05c3a38637d5f0f4bcaaead4dd2584462123ff54b9c5fb9eb8f79a14f8f1aa79`
- Normalized content comparison: `True`
- Final repository contract blob: `c813b2a9d012d789aa5ad39d86e267bec48dc046`

The contract source did not change after commit `0cb1e39`; later commits contain tests and documentation only.

## Finalized live lifecycle evidence

All receipts below were returned by the canonical live integration run and subsequently queried as `FINALIZED`.

| Flow | Transaction | Result / observed state |
|---|---|---|
| Deploy | `0xe3b613830db88703b779810067d4cc2690096d1c0fc95c553a4b08a481d42474` | `MAJORITY_AGREE`, `FINALIZED` |
| Create root A | `0x3a0220dfe261ca947c2e9bed11aa029c86fee89321f3e85b45aef799bb7a15d3` | `MAJORITY_AGREE`, `FINALIZED` |
| Resolve A | `0x57c715d0692a305dc209e413fd80f075ab1f6365d3a7b15159f5992a94cdbbb9` | `A.status = VALID`, `MAJORITY_AGREE`, `FINALIZED` |
| Create B -> A | `0xff965b7506858e4b09a9155ac619cd05848920cf0cfa9d671ed2445e13015f42` | `MAJORITY_AGREE`, `FINALIZED` |
| Resolve B | `0x5e28d70318e189d092aaf49d22d607d356e75a57555c32eead29225b9fc163d8` | `B.status = VALID`, `MAJORITY_AGREE`, `FINALIZED` |
| Create C -> B | `0x3675f7e548df114a315bf9199b63c43b5ba158d87492df22e5c3ec61b2f4d3a3` | `MAJORITY_AGREE`, `FINALIZED` |
| Resolve C | `0x9a078fbb391a34e39994f5f41ec474e7c92376484ef4748dcfcd11d2781a61a5` | `C.status = VALID`, `MAJORITY_AGREE`, `FINALIZED` |
| Re-resolve A | `0x3b9313f2e2d999deaaf98a1603bb3c1a50c1fe78a61df1bf2a7664038a6dfd64` | epoch advanced; `is_valid(B/C)=false`, `can_consume(B/C)=false` |
| Recover B | `0xd32f95b1ab326b8c852cfd5524e7924b0c73bcfa91b92abaef08a1cf24866ce7` | `B` recovered, `MAJORITY_AGREE`, `FINALIZED` |
| Recover C | `0x986cd478d74bc5f53f2915a310aff26661ad7bbdb1db2814c5d3c25da9849931` | `C.status = VALID`, `MAJORITY_AGREE`, `FINALIZED` |
| Create negative N | `0x94a86c34f260781ab94326a825c538ddd22142938c4b94ce4d34aa16f5729016` | `MAJORITY_AGREE`, `FINALIZED` |
| Resolve negative N | `0x9784660d17c98a00ed76bde046878eff841977c14f27e1ed6f5ec38774445c36` | `N.status` was `INVALID` or `PENDING` under semantic consensus; `FINALIZED` |

Consensus observations included `MAJORITY_AGREE` receipts with validator votes such as `AGREE` and `IDLE`. The negative resolution also exposed one `DISAGREE` vote while still reaching `MAJORITY_AGREE`; no leader-only result was accepted.

The committed live test is `tests/integration/test_proofgraph_studionet.py`. It uses disposable state within the canonical deployment and asserts positive root/derivation, three-level stale reads, recovery, and negative semantic handling.
