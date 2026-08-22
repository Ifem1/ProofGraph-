import json


def supported(reason="supported"):
    return json.dumps(
        {
            "verdict": "SUPPORTED",
            "rule_satisfied": True,
            "blocker_class": "NONE",
            "reason": reason,
        }
    )


def not_supported(blocker="EVIDENCE", reason="not supported"):
    return json.dumps(
        {
            "verdict": "NOT_SUPPORTED",
            "rule_satisfied": False,
            "blocker_class": blocker,
            "reason": reason,
        }
    )


def indeterminate(blocker="AMBIGUITY", reason="unclear"):
    return json.dumps(
        {
            "verdict": "INDETERMINATE",
            "rule_satisfied": False,
            "blocker_class": blocker,
            "reason": reason,
        }
    )


def create_root(contract, node_id="A"):
    contract.create_node(
        node_id,
        "The API is deployed and reachable.",
        "The evidence must directly demonstrate a live deployment.",
        "[]",
        "Deployment record and endpoint evidence.",
    )


def test_create_root_and_views(direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)

    node = json.loads(contract.get_node("A"))
    assert node["id"] == "A"
    assert node["status"] == "PENDING"
    assert node["dependencies"] == []
    assert contract.get_status("A") == "PENDING"
    assert contract.is_valid("A") is False
    assert json.loads(contract.get_graph_stats())["node_count"] == 1


def test_missing_dependency_reverts(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    with direct_vm.expect_revert("DEPENDENCY_NOT_FOUND"):
        contract.create_node(
            "B",
            "Release is ready.",
            "All declared dependencies must be valid.",
            '["A"]',
            "Release evidence.",
        )


def test_duplicate_node_reverts(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    with direct_vm.expect_revert("NODE_ALREADY_EXISTS"):
        create_root(contract)


def test_duplicate_dependency_reverts(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    with direct_vm.expect_revert("DUPLICATE_DEPENDENCY"):
        contract.create_node(
            "B",
            "Release is ready.",
            "The API deployment premise must hold.",
            '["A","A"]',
            "Release evidence.",
        )


def test_supported_root_becomes_valid(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported())

    contract.resolve_node("A", "")

    node = json.loads(contract.get_node("A"))
    assert node["status"] == "VALID"
    assert node["verdict"] == "SUPPORTED"
    assert node["revision"] == 1
    assert contract.is_valid("A") is True
    assert contract.can_consume("A", 1) is True
    assert contract.can_consume("A", 2) is False


def test_not_supported_root_becomes_invalid(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", not_supported())

    contract.resolve_node("A", "")

    node = json.loads(contract.get_node("A"))
    assert node["status"] == "INVALID"
    assert node["blocker_class"] == "EVIDENCE"


def test_indeterminate_root_stays_pending(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", indeterminate())

    contract.resolve_node("A", "conflicting source material")

    node = json.loads(contract.get_node("A"))
    assert node["status"] == "PENDING"
    assert node["verdict"] == "INDETERMINATE"
    assert node["last_context"] == "conflicting source material"


def test_child_requires_valid_parent(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    contract.create_node(
        "B",
        "The release is ready.",
        "The deployment premise must be valid and release evidence must support readiness.",
        '["A"]',
        "Release checklist.",
    )

    # Parent is still PENDING, so the child is blocked deterministically; no LLM call.
    contract.resolve_node("B", "")
    child = json.loads(contract.get_node("B"))
    assert child["status"] == "NEEDS_REVALIDATION"
    assert child["blocker_class"] == "DEPENDENCY"


def test_derived_node_and_dependents_index(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported())
    contract.resolve_node("A", "")

    contract.create_node(
        "B",
        "The release is ready.",
        "A valid deployment plus the supplied checklist must materially establish release readiness.",
        '["A"]',
        "Release checklist completed.",
    )
    contract.resolve_node("B", "")

    assert contract.is_valid("B") is True
    assert json.loads(contract.get_dependents("A")) == ["B"]


def test_upstream_failure_marks_direct_child_stale(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported())
    contract.resolve_node("A", "")

    contract.create_node(
        "B",
        "The release is ready.",
        "A valid deployment plus evidence must establish readiness.",
        '["A"]',
        "Release checklist completed.",
    )
    contract.resolve_node("B", "")
    assert contract.is_valid("B") is True

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", not_supported("EVIDENCE"))
    contract.resolve_node("A", "new evidence contradicts the prior deployment record")

    assert contract.get_status("A") == "INVALID"
    assert contract.get_status("B") == "NEEDS_REVALIDATION"
    assert contract.is_valid("B") is False


def test_validator_compares_semantic_decision_fields(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported("leader wording"))

    contract.resolve_node("A", "")

    # The captured validator may use different free-form reasoning and still agree.
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported("validator uses different words"))
    assert direct_vm.run_validator() is True


def test_validator_rejects_material_decision_disagreement(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported())

    contract.resolve_node("A", "")

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", not_supported("RULE"))
    assert direct_vm.run_validator() is False
