# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json
import hashlib


class ProofGraph(gl.Contract):
    """Dependency-aware semantic attestations for GenLayer contracts."""

    nodes: TreeMap[str, str]
    dependents: TreeMap[str, str]
    node_count: u64
    validity_epoch: u64

    def __init__(self):
        self.node_count = u64(0)
        self.validity_epoch = u64(0)

    def _spec_hash(self, node: dict) -> str:
        specification = json.dumps(
            {
                "statement": node["statement"],
                "rule": node["rule"],
                "dependencies": node["dependencies"],
                "evidence": node["evidence"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(specification.encode()).hexdigest()

    def _load_node(self, node_id: str) -> dict:
        raw = self.nodes.get(node_id, "")
        if raw == "":
            raise gl.vm.UserError("NODE_NOT_FOUND")
        return json.loads(raw)

    def _store_node(self, node_id: str, node: dict) -> None:
        self.nodes[node_id] = json.dumps(node, sort_keys=True, separators=(",", ":"))

    def _load_string_array(self, raw: str) -> list[str]:
        if raw == "":
            return []
        value = json.loads(raw)
        if not isinstance(value, list):
            raise gl.vm.UserError("INVALID_ARRAY_STATE")
        return value

    def _store_string_array(self, values: list[str]) -> str:
        return json.dumps(values, separators=(",", ":"))

    def _validate_text(self, value: str, name: str, minimum: int, maximum: int) -> None:
        size = len(value.strip())
        if size < minimum or size > maximum:
            raise gl.vm.UserError(name + "_LENGTH")

    def _parse_dependencies(self, dependencies_json: str) -> list[str]:
        if len(dependencies_json) > 2048:
            raise gl.vm.UserError("DEPENDENCIES_TOO_LARGE")
        try:
            dependencies = json.loads(dependencies_json)
        except Exception:
            raise gl.vm.UserError("DEPENDENCIES_NOT_JSON")
        if not isinstance(dependencies, list):
            raise gl.vm.UserError("DEPENDENCIES_NOT_ARRAY")
        if len(dependencies) > 8:
            raise gl.vm.UserError("TOO_MANY_DEPENDENCIES")
        result: list[str] = []
        for dependency in dependencies:
            if not isinstance(dependency, str):
                raise gl.vm.UserError("DEPENDENCY_NOT_STRING")
            dependency = dependency.strip()
            if dependency == "" or len(dependency) > 96:
                raise gl.vm.UserError("INVALID_DEPENDENCY_ID")
            if dependency in result:
                raise gl.vm.UserError("DUPLICATE_DEPENDENCY")
            result.append(dependency)
        return result

    def _mark_direct_dependents_stale(self, node_id: str) -> None:
        children = self._load_string_array(self.dependents.get(node_id, "[]"))
        for child_id in children:
            raw = self.nodes.get(child_id, "")
            if raw == "":
                continue
            child = json.loads(raw)
            if child["status"] == "VALID":
                child["status"] = "NEEDS_REVALIDATION"
                child["verdict"] = "UNRESOLVED"
                child["rule_satisfied"] = False
                child["blocker_class"] = "DEPENDENCY"
                child["reason"] = "An upstream dependency is no longer valid; resolve this node again."
                self._store_node(child_id, child)

    @gl.public.write
    def create_node(
        self,
        node_id: str,
        statement: str,
        rule: str,
        dependencies_json: str,
        evidence: str,
    ) -> None:
        node_id = node_id.strip()
        self._validate_text(node_id, "NODE_ID", 1, 96)
        self._validate_text(statement, "STATEMENT", 8, 2000)
        self._validate_text(rule, "RULE", 8, 2000)
        if len(evidence) > 8000:
            raise gl.vm.UserError("EVIDENCE_TOO_LARGE")
        if self.nodes.get(node_id, "") != "":
            raise gl.vm.UserError("NODE_ALREADY_EXISTS")

        dependencies = self._parse_dependencies(dependencies_json)
        if node_id in dependencies:
            raise gl.vm.UserError("SELF_DEPENDENCY")

        # A node may only point to already-existing nodes. Because IDs are immutable,
        # every edge points backward in creation order and the graph is a DAG.
        for dependency in dependencies:
            if self.nodes.get(dependency, "") == "":
                raise gl.vm.UserError("DEPENDENCY_NOT_FOUND")
            children = self._load_string_array(self.dependents.get(dependency, "[]"))
            if len(children) >= 32:
                raise gl.vm.UserError("DEPENDENT_LIMIT_REACHED")
            children.append(node_id)
            self.dependents[dependency] = self._store_string_array(children)

        node = {
            "id": node_id,
            "statement": statement.strip(),
            "rule": rule.strip(),
            "dependencies": dependencies,
            "evidence": evidence.strip(),
            "status": "PENDING",
            "verdict": "UNRESOLVED",
            "rule_satisfied": False,
            "blocker_class": "NONE",
            "reason": "Awaiting GenLayer consensus.",
            "revision": 0,
            "resolved_epoch": 0,
            "resolved_parent_revisions": {},
            "spec_hash": "",
            "adjudication_input_hash": "",
            "last_context": "",
        }
        node["spec_hash"] = self._spec_hash(node)
        self._store_node(node_id, node)
        self.dependents[node_id] = "[]"
        self.node_count = u64(self.node_count + 1)

    @gl.public.write
    def resolve_node(self, node_id: str, context: str) -> None:
        if len(context) > 4000:
            raise gl.vm.UserError("CONTEXT_TOO_LARGE")

        node = self._load_node(node_id)
        previous_status = node["status"]
        previous_effective_valid = self._is_effectively_valid(node)
        if previous_effective_valid:
            self.validity_epoch = u64(self.validity_epoch + 1)
        current_epoch = int(self.validity_epoch)
        dependencies = node["dependencies"]
        parent_summaries: list[dict] = []
        parent_revisions: dict[str, int] = {}
        invalid_parent = ""

        for dependency in dependencies:
            parent = self._load_node(dependency)
            parent_summaries.append(
                {
                    "id": parent["id"],
                    "statement": parent["statement"],
                    "status": parent["status"],
                    "verdict": parent["verdict"],
                    "revision": parent["revision"],
                }
            )
            parent_revisions[dependency] = int(parent["revision"])
            if not self._is_effectively_valid(parent) and invalid_parent == "":
                invalid_parent = dependency

        node["revision"] = int(node["revision"]) + 1
        node["last_context"] = context.strip()
        node["resolved_epoch"] = 0
        node["resolved_parent_revisions"] = parent_revisions

        # A derived conclusion cannot be valid while one of its declared premises is not.
        # This is deterministic and does not need an LLM vote.
        if invalid_parent != "":
            node["status"] = "NEEDS_REVALIDATION"
            node["verdict"] = "NOT_SUPPORTED"
            node["rule_satisfied"] = False
            node["blocker_class"] = "DEPENDENCY"
            node["reason"] = "Dependency " + invalid_parent + " is not currently VALID."
            self._store_node(node_id, node)
            if previous_status == "VALID":
                self._mark_direct_dependents_stale(node_id)
            return

        # Context is deliberately audit metadata, not part of the semantic
        # basis. A permissionless caller cannot change what this node means.
        adjudication_input = json.dumps(
            {
                "statement": node["statement"],
                "rule": node["rule"],
                "parents": parent_summaries,
                "evidence": node["evidence"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        def evaluate() -> dict:
            prompt = """
You are adjudicating one node in a dependency-aware proof graph.

Decide whether the proposed STATEMENT is supported by the supplied accepted parent conclusions, declared RULE, EVIDENCE, and optional CONTEXT.

Important:
- Treat parent conclusions as premises only when supplied here; do not invent missing premises.
- The RULE defines how the premises/evidence must entail or justify the statement.
- Do not reward plausible wording. Judge whether the derivation is materially supported.
- If evidence is insufficient, contradictory, or the rule cannot be applied reliably, choose INDETERMINATE rather than guessing.
- For a root node with no parents, determine whether its evidence/context supports the statement under the rule.

Return JSON with exactly these semantic fields plus a short reason:
{
  "verdict": "SUPPORTED" | "NOT_SUPPORTED" | "INDETERMINATE",
  "rule_satisfied": true | false,
  "blocker_class": "NONE" | "DEPENDENCY" | "EVIDENCE" | "RULE" | "AMBIGUITY",
  "reason": "brief audit explanation"
}

Consistency requirements:
- SUPPORTED requires rule_satisfied=true and blocker_class=NONE.
- NOT_SUPPORTED requires rule_satisfied=false and a non-NONE blocker_class.
- INDETERMINATE requires rule_satisfied=false and a non-NONE blocker_class.

INPUT:
""" + adjudication_input
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(result, dict):
                raise gl.vm.UserError("LLM_NON_OBJECT")
            verdict = result.get("verdict")
            satisfied = result.get("rule_satisfied")
            blocker = result.get("blocker_class")
            reason = result.get("reason")
            if verdict not in ("SUPPORTED", "NOT_SUPPORTED", "INDETERMINATE"):
                raise gl.vm.UserError("LLM_BAD_VERDICT")
            if not isinstance(satisfied, bool):
                raise gl.vm.UserError("LLM_BAD_RULE_FLAG")
            if blocker not in ("NONE", "DEPENDENCY", "EVIDENCE", "RULE", "AMBIGUITY"):
                raise gl.vm.UserError("LLM_BAD_BLOCKER")
            if not isinstance(reason, str) or len(reason.strip()) == 0 or len(reason) > 1200:
                raise gl.vm.UserError("LLM_BAD_REASON")
            if verdict == "SUPPORTED" and (not satisfied or blocker != "NONE"):
                raise gl.vm.UserError("LLM_INCONSISTENT_SUPPORTED")
            if verdict != "SUPPORTED" and (satisfied or blocker == "NONE"):
                raise gl.vm.UserError("LLM_INCONSISTENT_REJECTION")
            return {
                "verdict": verdict,
                "rule_satisfied": satisfied,
                "blocker_class": blocker,
                "reason": reason.strip(),
            }

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_result = evaluate()
                leader = leader_result.calldata
                if not isinstance(leader, dict):
                    return False
                # Consensus is deliberately over stable semantic decision fields.
                # Free-form reasoning is audit context, not an equivalence key.
                return (
                    leader.get("verdict") == validator_result["verdict"]
                    and leader.get("rule_satisfied") == validator_result["rule_satisfied"]
                    and leader.get("blocker_class") == validator_result["blocker_class"]
                )
            except Exception:
                # Malformed or failed validator executions disagree, causing leader rotation.
                return False

        result = gl.vm.run_nondet_unsafe(evaluate, validator_fn)

        node["adjudication_input_hash"] = hashlib.sha256(
            adjudication_input.encode()
        ).hexdigest()
        node["spec_hash"] = self._spec_hash(node)
        node["resolved_epoch"] = current_epoch

        node["verdict"] = result["verdict"]
        node["rule_satisfied"] = result["rule_satisfied"]
        node["blocker_class"] = result["blocker_class"]
        node["reason"] = result["reason"]
        if result["verdict"] == "SUPPORTED":
            node["status"] = "VALID"
        elif result["verdict"] == "NOT_SUPPORTED":
            node["status"] = "INVALID"
        else:
            node["status"] = "PENDING"

        self._store_node(node_id, node)

        if previous_status == "VALID" and node["status"] != "VALID":
            self._mark_direct_dependents_stale(node_id)

    @gl.public.view
    def get_node(self, node_id: str) -> str:
        raw = self.nodes.get(node_id, "")
        if raw == "":
            raise gl.vm.UserError("NODE_NOT_FOUND")
        return raw

    def _is_effectively_valid(self, node: dict) -> bool:
        if node["status"] != "VALID":
            return False
        if int(node.get("resolved_epoch", 0)) != int(self.validity_epoch):
            return False
        for dependency in node["dependencies"]:
            parent_raw = self.nodes.get(dependency, "")
            if parent_raw == "":
                return False
            parent = json.loads(parent_raw)
            if not self._is_directly_bound(parent, int(node["resolved_parent_revisions"].get(dependency, -1))):
                return False
        return True

    def _is_directly_bound(self, parent: dict, expected_revision: int) -> bool:
        return (
            parent["status"] == "VALID"
            and int(parent["revision"]) == expected_revision
            and int(parent.get("resolved_epoch", 0)) == int(self.validity_epoch)
        )

    @gl.public.view
    def get_dependents(self, node_id: str) -> str:
        if self.nodes.get(node_id, "") == "":
            raise gl.vm.UserError("NODE_NOT_FOUND")
        return self.dependents.get(node_id, "[]")

    @gl.public.view
    def is_valid(self, node_id: str) -> bool:
        raw = self.nodes.get(node_id, "")
        if raw == "":
            return False
        return self._is_effectively_valid(json.loads(raw))

    @gl.public.view
    def can_consume(self, node_id: str, minimum_revision: u64) -> bool:
        raw = self.nodes.get(node_id, "")
        if raw == "":
            return False
        node = json.loads(raw)
        return self._is_effectively_valid(node) and int(node["revision"]) >= int(minimum_revision)

    @gl.public.view
    def get_status(self, node_id: str) -> str:
        raw = self.nodes.get(node_id, "")
        if raw == "":
            return "MISSING"
        return json.loads(raw)["status"]

    @gl.public.view
    def get_graph_stats(self) -> str:
        return json.dumps(
            {"node_count": int(self.node_count), "validity_epoch": int(self.validity_epoch)},
            separators=(",", ":"),
        )
