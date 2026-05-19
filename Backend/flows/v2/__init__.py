"""FlowSpec v2 sidecar package.

Flow v2 is validation/shadow-only in Phase 4. Live calls continue to use the
existing StateManager and v1 conversationFlow schema.
"""

from .spec import FlowSpecValidationError, build_flow_spec_from_agent, validate_flow_spec
from .shadow_runner import FlowShadowRunner, ShadowTurnResult
from .preview import build_flow_preview

__all__ = [
    "FlowShadowRunner",
    "FlowSpecValidationError",
    "ShadowTurnResult",
    "build_flow_preview",
    "build_flow_spec_from_agent",
    "validate_flow_spec",
]
