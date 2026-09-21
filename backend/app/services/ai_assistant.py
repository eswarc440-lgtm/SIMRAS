from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.entities import Asset
from app.models.operational import AIAssistantAudit
from app.services.report_decision_support import enrich_report_decision_support


class AIAssistantService:
    """AI Assistant service for grounded evidence-based responses."""

    async def generate_response(
        self,
        asset_code: str,
        question: str,
        session: AsyncSession,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Generate AI response grounded in asset evidence."""
        # Get asset
        result = await session.execute(
            select(Asset).where(Asset.asset_code == asset_code)
        )
        asset = result.scalar_one_or_none()

        if asset is None:
            return {
                "answer": f"Asset {asset_code} not found in the system.",
                "evidence_used": [],
                "assessment_basis": "ASSET_NOT_FOUND",
                "limitations": ["Asset does not exist in SIMRAS database"],
                "sources": [],
            }

        # Get assessment data
        try:
            from app.services.twin_service import build_twin

            twin = await build_twin(session, asset_code)
        except Exception:
            twin = None

        # Generate context-aware response
        response = self._generate_contextual_response(question, asset, twin)

        # Audit the AI request
        if user_id:
            audit = AIAssistantAudit(
                user_id=user_id,
                asset_code=asset_code,
                question=question,
                assessment_id=twin.get("ai", {}).get("assessment_id") if twin else None,
                model="simras-evidence-v1",
                response=response["answer"],
            )
            session.add(audit)
            await session.commit()

        return response

    def _generate_contextual_response(
        self,
        question: str,
        asset: Asset,
        twin: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Generate context-aware response based on available evidence."""
        question_lower = question.lower()

        evidence_used = []
        limitations = []
        sources = []

        # Extract evidence from twin data
        if twin:
            ai_data = twin.get("ai", {})
            asset_data = twin.get("asset", {})
            government_evidence = twin.get("government_evidence", [])

            evidence_used.append("Twin state")
            sources.append("SIMRAS Digital Twin")

            if government_evidence:
                evidence_used.append("Government evidence")
                sources.append("Official government records")

        # Build answer based on question type
        if "health" in question_lower:
            health_score = twin.get("ai", {}).get("prediction", {}).get("structural", {}).get("health_score") if twin else None
            health_basis = twin.get("ai", {}).get("prediction", {}).get("structural", {}).get("health_basis") if twin else None

            if health_score is not None:
                answer = f"The health score for {asset.name} ({asset.asset_code}) is {health_score} / 100."
                if health_basis:
                    answer += f" This is based on: {health_basis}"
                evidence_used.append("Health assessment")
            else:
                answer = f"No verified health assessment is currently available for {asset.name}."
                limitations.append("No structural health assessment available")

        elif "risk" in question_lower:
            risk_score = twin.get("ai", {}).get("prediction", {}).get("structural", {}).get("risk_score") if twin else None
            risk_level = twin.get("ai", {}).get("prediction", {}).get("structural", {}).get("risk_level") if twin else None
            risk_basis = twin.get("ai", {}).get("prediction", {}).get("structural", {}).get("risk_basis") if twin else None

            if risk_score is not None:
                answer = f"The risk score for {asset.name} is {risk_score} / 100 with risk level {risk_level}."
                if risk_basis:
                    answer += f" This is based on: {risk_basis}"
                evidence_used.append("Risk assessment")
            else:
                answer = f"No verified risk assessment is currently available for {asset.name}."
                limitations.append("No structural risk assessment available")

        elif "rul" in question_lower or "remaining useful life" in question_lower:
            rul = twin.get("ai", {}).get("prediction", {}).get("remaining_useful_life", {}) if twin else None
            rul_years = rul.get("estimate_years") if rul else None
            rul_basis = rul.get("reason") if rul else None

            if rul_years is not None:
                answer = f"The estimated remaining useful life for {asset.name} is {rul_years} years."
                if rul_basis:
                    answer += f" This is based on: {rul_basis}"
                evidence_used.append("RUL assessment")
            else:
                answer = f"No verified RUL assessment is currently available for {asset.name}."
                limitations.append("No RUL assessment available")

        elif "inspection" in question_lower:
            answer = f"Inspection history for {asset.name} would require accessing the official inspection records. Currently, no detailed inspection timeline is available in the system."
            limitations.append("Inspection history not yet integrated")

        elif "maintenance" in question_lower:
            answer = f"Maintenance records for {asset.name} would require accessing the maintenance database. Currently, no detailed maintenance history is available in the system."
            limitations.append("Maintenance history not yet integrated")

        elif "recommendation" in question_lower or "what should" in question_lower:
            if twin and twin.get("ai", {}).get("prediction", {}).get("structural", {}).get("health_score"):
                health = twin["ai"]["prediction"]["structural"]["health_score"]
                if health < 60:
                    answer = f"Based on the current health score of {health}, priority should be given to structural inspection and any necessary maintenance to prevent further deterioration."
                else:
                    answer = f"Based on the current health score of {health}, the asset appears to be in acceptable condition. Continue regular monitoring and scheduled inspections."
                evidence_used.append("Health-based recommendation")
            else:
                answer = "No verified assessment is available to generate specific recommendations for this asset."
                limitations.append("No assessment available for recommendations")

        else:
            answer = f"I can provide information about {asset.name} ({asset.asset_code}) including health, risk, RUL, and operational context. What specific aspect would you like to know about?"
            limitations.append("Question requires more specific information")

        return {
            "answer": answer,
            "evidence_used": evidence_used,
            "assessment_basis": twin.get("ai", {}).get("prediction", {}).get("structural", {}).get("assessment_method") if twin else "EVIDENCE_NOT_AVAILABLE",
            "limitations": limitations,
            "sources": sources,
        }


# Singleton instance
ai_assistant_service = AIAssistantService()
