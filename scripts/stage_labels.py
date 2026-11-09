"""Workflow stage labels on issues and draft PRs.

One workflow label at a time. Waiting labels are the cron-2 queue.
Approved labels mean that stage is in flight (or about to merge).
"""

from __future__ import annotations

from aac_common import load_workflow

READY = "Ready"
ABORT = "Abort"

WAITING = ("Spec", "Plan", "Acceptance", "Implement", "Gate")
APPROVED = {
    "Spec": "Spec_Approved",
    "Plan": "Plan_Approved",
    "Acceptance": "Acceptance_Approved",
    "Implement": "Implement_Approved",
    "Gate": "Gate_Approved",
}
NEXT_WAITING = {
    "Spec_Approved": "Plan",
    "Plan_Approved": "Acceptance",
    "Acceptance_Approved": "Implement",
    "Implement_Approved": "Gate",
}
# After Gate_Approved we merge; no next waiting label.
WAITING_TO_ACTION = {
    "Spec": "approve_spec",
    "Plan": "start_s3",
    "Acceptance": "start_s4",
    "Implement": "start_s5",
    "Gate": "merge",
}

LABEL_COLORS = {
    READY: "0E8A16",
    "Spec": "FBCA04",
    "Plan": "FBCA04",
    "Acceptance": "FBCA04",
    "Implement": "FBCA04",
    "Gate": "FBCA04",
    "Spec_Approved": "1D76DB",
    "Plan_Approved": "1D76DB",
    "Acceptance_Approved": "1D76DB",
    "Implement_Approved": "1D76DB",
    "Gate_Approved": "1D76DB",
    ABORT: "B60205",
}

LABEL_DESCRIPTIONS = {
    READY: "Issue ready for S1",
    "Spec": "Waiting for /approve on spec",
    "Plan": "Waiting for /approve on plan",
    "Acceptance": "Waiting for /approve on acceptance tests",
    "Implement": "Waiting for /approve on implement",
    "Gate": "Waiting for /approve to merge",
    "Spec_Approved": "Spec approved; plan running",
    "Plan_Approved": "Plan approved; acceptance running",
    "Acceptance_Approved": "Acceptance approved; implement running",
    "Implement_Approved": "Implement approved; gate/final running",
    "Gate_Approved": "Gate approved; merging into dev",
    ABORT: "Aborted",
}


def labels_cfg() -> dict[str, str]:
    raw = ((load_workflow().get("github") or {}).get("labels") or {})
    out = {
        "ready": READY,
        "abort": ABORT,
        "spec": "Spec",
        "plan": "Plan",
        "acceptance": "Acceptance",
        "implement": "Implement",
        "gate": "Gate",
        "spec_approved": "Spec_Approved",
        "plan_approved": "Plan_Approved",
        "acceptance_approved": "Acceptance_Approved",
        "implement_approved": "Implement_Approved",
        "gate_approved": "Gate_Approved",
    }
    for key, value in raw.items():
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()
    return out


def waiting_labels() -> tuple[str, ...]:
    cfg = labels_cfg()
    return tuple(cfg[k] for k in ("spec", "plan", "acceptance", "implement", "gate"))


def all_workflow_labels() -> set[str]:
    cfg = labels_cfg()
    return set(cfg.values())


def approved_label(waiting: str) -> str:
    cfg = labels_cfg()
    inverse = {cfg[k]: k for k in ("spec", "plan", "acceptance", "implement", "gate")}
    key = inverse.get(waiting)
    if not key:
        raise ValueError(f"not a waiting label: {waiting}")
    return cfg[f"{key}_approved"]


def next_waiting(approved: str) -> str | None:
    cfg = labels_cfg()
    mapping = {
        cfg["spec_approved"]: cfg["plan"],
        cfg["plan_approved"]: cfg["acceptance"],
        cfg["acceptance_approved"]: cfg["implement"],
        cfg["implement_approved"]: cfg["gate"],
        cfg["gate_approved"]: None,
    }
    if approved not in mapping:
        raise ValueError(f"not an approved label: {approved}")
    return mapping[approved]


def tech_lead_note(*, stage: str, delivered: str, next_step: str) -> str:
    """Short Tech Lead voice for a PR comment body (caller adds marker)."""
    return "\n".join(
        [
            f"**{stage} done.**",
            delivered.rstrip("."),
            f"Next: {next_step.rstrip('.')}.",
        ]
    )
