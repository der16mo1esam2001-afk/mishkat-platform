from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from .base import (
    AIProviderStatus,
    Citation,
    GroundedResponse,
    detect_prompt_injection,
    tool_registry,
)

# Licensed curated knowledge corpus for grounded NEXORA learning assistant
LICENSED_KNOWLEDGE_BASE = [
    {
        "keywords": ["python", "variable", "function", "programming"],
        "fact": "Python is a high-level interpreted programming language supporting structured, object-oriented, and functional programming paradigms.",
        "source_id": "ref_python_docs",
        "title": "Python 3.12 Official Documentation",
        "publisher": "Python Software Foundation",
        "license_name": "PSF License Version 2",
        "source_url": "https://docs.python.org/3/",
        "section": "General Python Tutorial, Section 4",
    },
    {
        "keywords": ["water", "stress", "scarcity", "aqueduct"],
        "fact": "Baseline water stress measures total annual water withdrawals relative to available renewable surface and groundwater supplies.",
        "source_id": "ref_wri_aqueduct",
        "title": "WRI Aqueduct 4.0 Methodology",
        "publisher": "World Resources Institute",
        "license_name": "CC BY 4.0",
        "source_url": "https://www.wri.org/aqueduct",
        "section": "Technical Note, Page 8",
    },
    {
        "keywords": ["solar", "radiation", "irradiance", "insolation", "energy"],
        "fact": "Global horizontal irradiance (ALLSKY_SFC_SW_DWN) measures the total solar irradiance received by a surface horizontal to the ground.",
        "source_id": "ref_nasa_power",
        "title": "NASA POWER Methodology and User Guide",
        "publisher": "NASA Langley Research Center",
        "license_name": "Open NASA Data Policy",
        "source_url": "https://power.larc.nasa.gov/docs/",
        "section": "Solar Resource Parameter Guide",
    },
]


class AIGateway:
    def __init__(self) -> None:
        self.provider_status = AIProviderStatus.NOT_CONFIGURED
        self.active_provider: str | None = None

    def get_status(self) -> dict[str, Any]:
        return {
            "status": self.provider_status.value,
            "inference_enabled": False,
            "active_provider": self.active_provider,
            "message": "Production AI model providers are disabled by default. The local grounded NEXORA assistant operates in strictly auditable, citation-grounded evaluation mode.",
            "safety_guardrails": [
                "Prompt injection defense filter active",
                "Clinical diagnosis and prescription requests strictly refused",
                "Water and electrical operational actuation commands strictly refused",
                "Explicit citations required for every factual assertion",
                "Tool execution requires action preview and human approval token for writes",
            ],
            "allowed_models": ["nexora-grounded-eval-v1"],
        }

    def answer_grounded_query(self, query: str, user_id: UUID) -> GroundedResponse:
        start_time = time.perf_counter()

        # 1. Prompt injection defense
        is_injection, reason = detect_prompt_injection(query)
        if is_injection:
            return GroundedResponse(
                query=query,
                grounded_answer="Request rejected by safety filter.",
                citations=[],
                retrieved_facts=[],
                inference_and_advice=[],
                is_refusal=True,
                refusal_reason=reason,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 2. Strict domain boundary refusals (no autonomous medical/actuation advice)
        lower_query = query.lower()
        if any(term in lower_query for term in ["prescribe", "diagnose", "treatment", "cure my", "blood test result"]):
            return GroundedResponse(
                query=query,
                grounded_answer="رفض الطلب: لا تقدم المنظومة تشخيصاً طبياً أو وصفات علاجية مستقلة. يرجى استشارة ممارس صحي مرخص.",
                citations=[],
                retrieved_facts=[],
                inference_and_advice=[],
                is_refusal=True,
                refusal_reason="Autonomous clinical diagnosis and prescription is strictly prohibited by MISHKAT Medical Safety Policy.",
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        if any(term in lower_query for term in ["open valve", "turn off pump", "trip breaker", "shut down grid"]):
            return GroundedResponse(
                query=query,
                grounded_answer="رفض الطلب: تكاملات الشبكات والمحطات تعمل بوضع القراءة فقط ولا تقبل أوامر تحكم مادية أو تشغيلية.",
                citations=[],
                retrieved_facts=[],
                inference_and_advice=[],
                is_refusal=True,
                refusal_reason="Autonomous operational actuation is prohibited. All operational integrations remain strictly read-only.",
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 3. Grounded knowledge retrieval (RAG with citations)
        matched_items = []
        for item in LICENSED_KNOWLEDGE_BASE:
            if any(kw in lower_query for kw in item["keywords"]):
                matched_items.append(item)

        if not matched_items:
            return GroundedResponse(
                query=query,
                grounded_answer="لا تتوفر أدلة كافية في قاعدة المصادر المرخصة المعتمدة للإجابة عن هذا الاستفسار دون تخمين.",
                citations=[],
                retrieved_facts=[],
                inference_and_advice=[],
                is_refusal=True,
                refusal_reason="Insufficient grounded evidence in verified licensed knowledge repository.",
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        citations = []
        retrieved_facts = []
        for item in matched_items:
            retrieved_facts.append(item["fact"])
            citations.append(
                Citation(
                    source_id=item["source_id"],
                    title=item["title"],
                    publisher=item["publisher"],
                    license_name=item["license_name"],
                    source_url=item["source_url"],
                    retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    section_or_page=item["section"],
                )
            )

        # Build answer explicitly separating facts from guidance
        grounded_text = "استناداً إلى المصادر المرخصة الموثقة:\n" + "\n".join(f"- {f}" for f in retrieved_facts)
        advice = ["يُرجى مراجعة الرابط المرجعي الأصلي للمزيد من التفاصيل والتحقق."]

        return GroundedResponse(
            query=query,
            grounded_answer=grounded_text,
            citations=citations,
            retrieved_facts=retrieved_facts,
            inference_and_advice=advice,
            is_refusal=False,
            latency_ms=(time.perf_counter() - start_time) * 1000,
        )


ai_gateway = AIGateway()
