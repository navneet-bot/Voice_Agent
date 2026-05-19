"""Central feature flags for the phased platform migration.

All roadmap flags default to disabled. Runtime code can opt in later without
changing flag names or environment wiring.
"""

from __future__ import annotations

import os
from types import MappingProxyType
from typing import Mapping


_DEFAULTS = MappingProxyType(
    {
        "auth.enforce_backend": False,
        "tenant.scoped_reads": False,
        "tenant.enforcement_readiness": False,
        "tenant.scoped_read_canary": False,
        "tenant.scoped_read_guard_shadow": False,
        "tenant.scoped_read_policy_shadow": False,
        "tenant.scoped_read_endpoint_shadow": False,
        "tenant.leak_regression_matrix": False,
        "tenant.result_asset_readiness": False,
        "tenant.final_rollout_report": False,
        "tenant.rollout_approval_packet": False,
        "tenant.rollout_canary_plan": False,
        "tenant.rollback_drill_readiness": False,
        "tenant.rollout_evidence_bundle": False,
        "tenant.canary_observation_checklist": False,
        "tenant.production_go_no_go_gate": False,
        "tenant.production_activation_contract_stub": False,
        "tenant.production_activation_permission_shadow": False,
        "tenant.production_activation_payload_dry_run": False,
        "tenant.production_activation_readiness": False,
        "tenant.production_activation_rollback_confirmation": False,
        "tenant.controlled_handoff_readiness": False,
        "ws.scoped_events": False,
        "ws.scoped_events_shadow": False,
        "recordings.access_shadow": False,
        "recordings.owner_lookup_shadow": False,
        "recordings.access_enforcement_shadow": False,
        "recordings.access_gate_dry_run": False,
        "transcripts.access_shadow": False,
        "transcripts.access_canary": False,
        "transcripts.access_enforcement_shadow": False,
        "transcripts.access_gate_dry_run": False,
        "transcripts.protected_route_stub": False,
        "transcripts.protected_route_permission_shadow": False,
        "transcripts.protected_response_shape_canary": False,
        "transcripts.protected_payload_dry_run": False,
        "transcripts.protected_enforcement_readiness": False,
        "transcripts.protected_live_activation_plan": False,
        "transcripts.protected_rollback_readiness": False,
        "transcripts.frontend_migration_readiness": False,
        "campaign.worker_v2": False,
        "campaign.lifecycle_management": False,
        "flow.v2_shadow": False,
        "flow.v2_live": False,
        "flow.visualization": False,
        "demo.runtime_qa_readiness": False,
        "scrape.generate_script": False,
        "scrape.worker_v1": False,
        "scrape.job_cancel": False,
        "scrape.stale_recovery": False,
        "scrape.job_events": False,
        "scrape.review_gate_shadow": False,
        "scrape.live_qa_readiness": False,
        "scrape.generated_draft_qa_readiness": False,
        "telephony.tenant_numbers": False,
        "memory.rag_enabled": False,
        "crm.sync_enabled": False,
        "crm.sync_preflight": False,
        "crm.sync_outbox": False,
        "crm.sync_worker_shadow": False,
        "crm.sync_worker_retries": False,
        "crm.sync_observability": False,
        "crm.provider_contracts": False,
        "crm.delivery_plan_shadow": False,
        "crm.delivery_approval_shadow": False,
        "crm.delivery_approval_revoke": False,
        "crm.live_readiness_shadow": False,
        "crm.provider_sandbox_shadow": False,
        "crm.dispatch_canary_shadow": False,
    }
)

_TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
_FALSE_VALUES = {"0", "false", "no", "off", "disabled"}


def env_name(flag_name: str) -> str:
    """Return the environment variable name for a dotted feature flag."""
    normalized = "".join(ch if ch.isalnum() else "_" for ch in flag_name.upper())
    return f"FEATURE_{normalized}"


def parse_bool(value: str | None, default: bool = False) -> bool:
    """Parse a feature flag value using conservative defaults."""
    if value is None:
        return bool(default)
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return bool(default)


def is_enabled(
    flag_name: str,
    *,
    default: bool | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Return whether a feature flag is enabled.

    Unknown flags are disabled unless the caller supplies an explicit default.
    """
    source = env if env is not None else os.environ
    fallback = _DEFAULTS.get(flag_name, False) if default is None else bool(default)
    return parse_bool(source.get(env_name(flag_name)), fallback)


def known_flags() -> dict[str, bool]:
    """Return the registered flags and their default states."""
    return dict(_DEFAULTS)


def snapshot(env: Mapping[str, str] | None = None) -> dict[str, bool]:
    """Return current flag states for logging, diagnostics, or health checks."""
    return {flag: is_enabled(flag, env=env) for flag in _DEFAULTS}
