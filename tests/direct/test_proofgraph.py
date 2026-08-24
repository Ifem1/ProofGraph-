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


def test_self_dependency_reverts(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    with direct_vm.expect_revert("SELF_DEPENDENCY"):
        contract.create_node(
            "A",
            "A node cannot depend on itself.",
            "The graph must remain acyclic.",
            '["A"]',
            "Structural invariant.",
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


def test_transitive_stale_reads_and_recovery(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract, "A")
    contract.create_node("B", "B is supported.", "A must support B.", '["A"]', "B evidence.")
    contract.create_node("C", "C is supported.", "B must support C.", '["B"]', "C evidence.")

    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported())
    contract.resolve_node("A", "")
    contract.resolve_node("B", "")
    contract.resolve_node("C", "")
    assert contract.is_valid("C") is True

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", not_supported("EVIDENCE"))
    contract.resolve_node("A", "contradictory update")

    # No intermediate repair is needed for reads to fail closed.
    assert contract.is_valid("B") is False
    assert contract.is_valid("C") is False
    assert contract.can_consume("B", 1) is False
    assert contract.can_consume("C", 1) is False

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported())
    contract.resolve_node("A", "recovered evidence")
    contract.resolve_node("B", "")
    contract.resolve_node("C", "")
    assert contract.is_valid("C") is True


def test_revision_binding_and_context_not_semantic_input(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported("first"))
    contract.resolve_node("A", "caller supplied context one")
    first = json.loads(contract.get_node("A"))
    assert first["spec_hash"] != ""
    assert first["adjudication_input_hash"] != ""
    assert "resolved_epoch" not in first
    assert first["depth"] == 0

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported("second"))
    contract.resolve_node("A", "different caller supplied context")
    second = json.loads(contract.get_node("A"))
    assert second["spec_hash"] == first["spec_hash"]
    assert second["adjudication_input_hash"] == first["adjudication_input_hash"]
    assert second["revision"] == 2


def test_dependency_local_isolation_and_middle_reresolution(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    for root in ("A", "X"):
        create_root(contract, root)
    contract.create_node("B", "B is supported.", "A must support B.", '["A"]', "B evidence.")
    contract.create_node("C", "C is supported.", "B must support C.", '["B"]', "C evidence.")
    contract.create_node("Y", "Y is supported.", "X must support Y.", '["X"]', "Y evidence.")
    contract.create_node("Z", "Z is supported.", "Y must support Z.", '["Y"]', "Z evidence.")

    direct_vm.mock_llm(r".*dependency-aware proof graph.*", supported())
    for node_id in ("A", "X", "B", "C", "Y", "Z"):
        contract.resolve_node(node_id, "")
    assert all(contract.is_valid(node_id) for node_id in ("A", "B", "C", "X", "Y", "Z"))

    # Re-resolving A changes only A's revision binding chain.
    contract.resolve_node("A", "new A evidence")
    assert not contract.is_valid("B")
    assert not contract.is_valid("C")
    assert contract.is_valid("X")
    assert contract.is_valid("Y") and contract.can_consume("Y", 1)
    assert contract.is_valid("Z") and contract.can_consume("Z", 1)

    # Re-resolving B with unchanged A preserves A/B and invalidates only C.
    contract.resolve_node("B", "new B evidence")
    assert contract.is_valid("A") and contract.is_valid("B")
    assert not contract.is_valid("C")
    contract.resolve_node("C", "new C evidence")
    assert contract.is_valid("C")


def test_max_depth_is_bounded(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract, "N0")
    for index in range(1, 17):
        parent = "N" + str(index - 1)
        node = "N" + str(index)
        contract.create_node(node, node + " is supported.", parent + " must support it.",
                             '["' + parent + '"]', node + " evidence.")
    with direct_vm.expect_revert("MAX_DEPTH_EXCEEDED"):
        contract.create_node("N17", "N17 is supported.", "N16 must support it.",
                             '["N16"]', "N17 evidence.")


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


def test_malformed_model_output_fails_closed(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(r".*dependency-aware proof graph.*", "not-json")
    with direct_vm.expect_revert("LLM_NON_OBJECT"):
        contract.resolve_node("A", "")
    assert json.loads(contract.get_node("A"))["status"] == "PENDING"


def test_inconsistent_supported_model_output_fails_closed(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    create_root(contract)
    direct_vm.mock_llm(
        r".*dependency-aware proof graph.*",
        json.dumps(
            {
                "verdict": "SUPPORTED",
                "rule_satisfied": False,
                "blocker_class": "NONE",
                "reason": "inconsistent",
            }
        ),
    )
    with direct_vm.expect_revert("LLM_INCONSISTENT_SUPPORTED"):
        contract.resolve_node("A", "")
    assert json.loads(contract.get_node("A"))["status"] == "PENDING"


def test_fan_in_bound_is_enforced(direct_vm, direct_deploy):
    contract = direct_deploy("contracts/ProofGraph.py")
    for index in range(8):
        create_root(contract, "P" + str(index))
    dependencies = json.dumps(["P" + str(index) for index in range(8)])
    contract.create_node("D", "A derived statement.", "All premises support it.", dependencies, "Evidence.")
    with direct_vm.expect_revert("TOO_MANY_DEPENDENCIES"):
        contract.create_node(
            "E",
            "Another derived statement.",
            "All premises support it.",
            json.dumps(["P" + str(index) for index in range(8)] + ["D"]),
            "Evidence.",
        )
