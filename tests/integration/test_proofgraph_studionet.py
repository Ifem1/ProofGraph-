"""Live Studionet lifecycle test.

Run explicitly with:
    $env:GENLAYER_RUN_STUDIONET="1"
    gltest tests/integration/test_proofgraph_studionet.py -v -s --network studionet

The test is skipped during ordinary local/Direct Mode runs so it cannot create
external deployments accidentally.
"""

import json
import os
from pathlib import Path

import pytest
from gltest import get_contract_factory, get_default_account
from gltest.types import TransactionStatus
from gltest.utils import extract_contract_address


pytestmark = pytest.mark.skipif(
    os.getenv("GENLAYER_RUN_STUDIONET") != "1",
    reason="set GENLAYER_RUN_STUDIONET=1 to run live Studionet evidence",
)


ROOT = Path(__file__).parents[2] / "contracts" / "ProofGraph.py"


def _receipt(label, receipt):
    data = dict(receipt)
    summary = {
        "hash": data.get("hash") or data.get("tx_id"),
        "status": data.get("status_name") or data.get("status"),
        "result": data.get("result_name") or data.get("result"),
        "consensus": data.get("consensus_data", {}).get("votes", {}),
    }
    print(label + "_RECEIPT=" + json.dumps(summary, default=str, sort_keys=True))
    return receipt


def test_live_proofgraph_lifecycle():
    factory = get_contract_factory(contract_file_path=ROOT)
    account = get_default_account()
    deployment_receipt = factory.deploy_contract_tx(
        account=account,
        wait_transaction_status=TransactionStatus.ACCEPTED,
    )
    _receipt("DEPLOY", deployment_receipt)
    contract = factory.build_contract(
        extract_contract_address(deployment_receipt), account=account
    )
    print("DEPLOYED_ADDRESS=" + str(contract.address))

    _receipt(
        "CREATE_A",
        contract.create_node(args=[
            "A",
            "The HTTPS endpoint https://example.com returns HTTP status 200.",
            "The evidence must explicitly record a successful HTTP 200 response for the same endpoint.",
            "[]",
            "Observed response: GET https://example.com -> HTTP 200 OK.",
        ]).transact(),
    )
    _receipt("RESOLVE_A", contract.resolve_node(args=["A", ""]).transact())
    assert json.loads(contract.get_node(args=["A"]).call())["status"] == "VALID"

    _receipt(
        "CREATE_B",
        contract.create_node(args=[
            "B",
            "The release is ready for publication.",
            "A valid endpoint check plus the supplied release checklist must support publication readiness.",
            '["A"]',
            "Release checklist: tests passed; approval recorded; deployment endpoint returned HTTP 200.",
        ]).transact(),
    )
    _receipt("RESOLVE_B", contract.resolve_node(args=["B", ""]).transact())
    assert contract.is_valid(args=["B"]).call() is True

    _receipt(
        "CREATE_C",
        contract.create_node(args=[
            "C",
            "The release may be consumed by downstream systems.",
            "A valid publication-readiness conclusion and downstream acceptance record must support consumption.",
            '["B"]',
            "Downstream acceptance record: release gate approved for consumption.",
        ]).transact(),
    )
    _receipt("RESOLVE_C", contract.resolve_node(args=["C", ""]).transact())
    assert contract.is_valid(args=["C"]).call() is True

    # Re-adjudicating A with context only is a semantic no-op. Its revision
    # binding is preserved, so arbitrary callers cannot invalidate B or C.
    _receipt("REVISE_A", contract.resolve_node(args=["A", "revalidation"]).transact())
    assert contract.is_valid(args=["B"]).call() is True
    assert contract.is_valid(args=["C"]).call() is True
    assert contract.can_consume(args=["B", 1]).call() is True
    assert contract.can_consume(args=["C", 1]).call() is True
    assert contract.is_valid(args=["C"]).call() is True

    _receipt(
        "CREATE_NEGATIVE",
        contract.create_node(args=[
            "N",
            "The service passes a deliberately unsupported requirement.",
            "Evidence must directly establish the unsupported requirement.",
            "[]",
            "No evidence is supplied for this requirement.",
        ]).transact(),
    )
    _receipt("RESOLVE_NEGATIVE", contract.resolve_node(args=["N", ""]).transact())
    assert contract.get_status(args=["N"]).call() in ("INVALID", "PENDING")
