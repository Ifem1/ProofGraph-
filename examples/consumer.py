# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *


@gl.contract_interface
class ProofGraphInterface:
    class View:
        def is_valid(self, node_id: str) -> bool: ...
        def can_consume(self, node_id: str, minimum_revision: u64) -> bool: ...
        def get_status(self, node_id: str) -> str: ...

    class Write:
        pass


class ReleaseGateExample(gl.Contract):
    proof_graph: Address
    required_node: str
    released: bool

    def __init__(self, proof_graph: Address, required_node: str):
        self.proof_graph = proof_graph
        self.required_node = required_node
        self.released = False

    @gl.public.write
    def release(self) -> None:
        proofs = ProofGraphInterface(self.proof_graph)
        if not proofs.view().is_valid(self.required_node):
            raise gl.vm.UserError("REQUIRED_PROOF_NOT_VALID")
        self.released = True

    @gl.public.view
    def is_released(self) -> bool:
        return self.released
