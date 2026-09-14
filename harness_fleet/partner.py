"""Typed Ideal Partner Profile used by partner-fleet onboarding and qualification."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from .profile import IdealCompanyProfile


class IdealPartnerProfile(BaseModel):
    """The durable Ideal Partner Profile (IPP) contract for partner research.

    The JSON file is the human-editable authoring form (ideal_partner_profile.json).
    It bridges to IdealCompanyProfile so partner campaigns can integrate directly
    with the existing store and run execution engine.
    """

    model_config = ConfigDict(extra="forbid")

    profile_kind: ClassVar[str] = "ideal_partner"

    profile_name: str = Field(default="My Ideal Partner Profile")
    version: str = Field(default="1.0.0")
    target_ecosystem: str = Field(default="", description="Platform or technology to be implemented (e.g. Snowflake, Kafka, Supabase, Datadog)")
    service_models: list[str] = Field(default_factory=list, description="Target partner delivery models (e.g. Systems Integration, Migration, Managed Services)")
    required_adjacent_competencies: list[str] = Field(default_factory=list, description="Pre-requisite or complementary tech stack (e.g. AWS, Terraform, Kubernetes)")
    target_client_segment: list[str] = Field(default_factory=list, description="Target client tier (e.g. Enterprise, Mid-Market, Regulated)")
    target_partner_tier: str = Field(default="", description="Desired partner agency scale (e.g. Boutique 10-50, Regional 50-250, GSI)")
    key_delivery_roles: list[str] = Field(default_factory=list, description="Client-facing roles (e.g. Solutions Architect, Implementation Consultant, Delivery Lead)")
    negative_exclusions: list[str] = Field(default_factory=list, description="Disqualifiers (e.g. Pure SaaS product vendors, staffing agencies, direct rivals)")
    anchor_partners: list[str] = Field(default_factory=list, description="Reference exemplar partner firms or agencies")
    calibrated_scoring_rubric: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_interview_document(cls, value: Any) -> Any:
        """Flatten the nested shape emitted by the IPP interview guide."""
        if not isinstance(value, dict):
            return value
        nested = value.get("ipp_profile") or value.get("partner_profile")
        if isinstance(nested, dict):
            flattened = dict(nested)
            for key in ("profile_name", "version", "calibrated_scoring_rubric"):
                if key in value:
                    flattened[key] = value[key]
            return flattened
        return value

    @classmethod
    def load(cls, path: Path | str) -> IdealPartnerProfile:
        profile_path = Path(path).expanduser()
        if not profile_path.exists():
            raise FileNotFoundError(f"Ideal Partner Profile not found at: {profile_path}")
        return cls.model_validate(json.loads(profile_path.read_text(encoding="utf-8")))

    def save(self, path: Path | str) -> None:
        profile_path = Path(path).expanduser()
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def to_company_profile(self) -> IdealCompanyProfile:
        """Map to IdealCompanyProfile for persistence in the SQLite store."""
        trigger_phrases = [
            f"service model: {sm}" for sm in self.service_models
        ] + [
            f"target client: {tc}" for tc in self.target_client_segment
        ]
        return IdealCompanyProfile(
            profile_name=self.profile_name,
            version=self.version,
            product_category=f"Implementation Partner: {self.target_ecosystem}".strip(),
            architectural_layer=self.target_partner_tier or "Systems Integration & Consulting Partner",
            required_stack=list(dict.fromkeys(([self.target_ecosystem] if self.target_ecosystem else []) + self.required_adjacent_competencies)),
            negative_stack_exclusions=self.negative_exclusions,
            trigger_pain_phrases=trigger_phrases,
            target_roles=self.key_delivery_roles,
            anchor_logos=self.anchor_partners,
            calibrated_scoring_rubric=self.calibrated_scoring_rubric,
        )

    def to_prompt_context(self) -> str:
        """Render explicit partner context for task runs."""
        return (
            f"IDEAL PARTNER PROFILE: {self.profile_name} (v{self.version})\n"
            f"Target ecosystem / technology: {self.target_ecosystem or 'Not specified'}\n"
            f"Service delivery models: {', '.join(self.service_models) or 'Not specified'}\n"
            f"Required adjacent competencies: {', '.join(self.required_adjacent_competencies) or 'None specified'}\n"
            f"Target client segment: {', '.join(self.target_client_segment) or 'Not specified'}\n"
            f"Target partner tier: {self.target_partner_tier or 'Not specified'}\n"
            f"Key delivery roles: {', '.join(self.key_delivery_roles) or 'Not specified'}\n"
            f"Negative exclusions: {', '.join(self.negative_exclusions) or 'None specified'}\n"
            f"Anchor exemplar partners: {', '.join(self.anchor_partners) or 'None specified'}\n"
            f"Scoring rubric: {json.dumps(self.calibrated_scoring_rubric, ensure_ascii=False, sort_keys=True)}"
        )
