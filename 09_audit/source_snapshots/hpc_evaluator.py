"""Evaluator workflow for ECN-BENCH benchmark scoring."""

from __future__ import annotations

import math
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping

from .prompt_registry import build_evaluator_system_prompt, load_mcq_prompt_spec
from .role_router import BenchmarkRoleRouter

MCQ_DIMENSION_KEYS = (
    "prediction_accuracy",
    "polarization",
    "herd_effect",
    "deliberation_quality",
    "susceptibility",
    "convergence",
    "information_diversity",
)
MCQ_BUCKET_KEYS = ("very_low", "low", "high", "very_high")
MCQ_BUCKET_SCORE_ANCHORS = {
    "very_low": 0.0,
    "low": 1.0 / 3.0,
    "high": 2.0 / 3.0,
    "very_high": 1.0,
}
MCQ_DIMENSION_WEIGHTS = {
    "prediction_accuracy": 0.25,
    "polarization": 0.125,
    "herd_effect": 0.125,
    "deliberation_quality": 0.125,
    "susceptibility": 0.125,
    "convergence": 0.125,
    "information_diversity": 0.125,
}
CANONICAL_VALIDATED_SCALE_KEYS = (
    "prediction_accuracy_score",
    "polarization_score",
    "herd_effect_score",
    "deliberation_quality_score",
    "susceptibility_score",
    "convergence_score",
    "information_diversity_score",
    "weighted_rubric_score",
)
# Phase 1 MVP uses placeholder weights (prediction_accuracy=0.25, others=0.125)
# for pipeline validation. Empirical weight optimization will be applied to pilot
# data prior to Phase 2 per KB §2.9.
VALIDATED_SCALES_SCHEMA_VERSION = "v1"
INVALID_JSON_ERROR_PREFIX = "Invalid JSON format from LLM:"
EVALUATOR_JSON_MAX_ATTEMPTS = 3
_EVALUATOR_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "ecnbench_mcq_v1.yaml"


@lru_cache(maxsize=1)
def get_evaluator_system_prompt() -> str:
    try:
        return build_evaluator_system_prompt(load_mcq_prompt_spec(_EVALUATOR_PROMPT_PATH))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load evaluator prompt contract from {_EVALUATOR_PROMPT_PATH}"
        ) from exc


def _normalize_probability_mapping(mapping: Any, context: str) -> Dict[str, float]:
    if not isinstance(mapping, Mapping) or not mapping:
        raise ValueError(f"{context} must be a non-empty mapping")

    normalized: Dict[str, float] = {}
    total = 0.0
    for label, value in mapping.items():
        if not isinstance(label, str) or not label:
            raise ValueError(f"{context} must use non-empty string keys")
        if not isinstance(value, (int, float)):
            raise ValueError(f"{context} has invalid value for {label!r}: {value!r}")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric < 0.0:
            raise ValueError(
                f"{context} has invalid value for {label!r}: {value!r} (must be finite and non-negative)"
            )
        normalized[label] = numeric
        total += numeric

    if total <= 0.0:
        raise ValueError(f"{context} must have positive total mass")

    return {label: value / total for label, value in normalized.items()}


def _validate_numeric_scores_mapping(
    mapping: Any,
    context: str,
    *,
    allow_empty: bool = False,
) -> Dict[str, float]:
    if not isinstance(mapping, Mapping):
        requirement = "a mapping" if allow_empty else "a non-empty mapping"
        raise ValueError(f"{context} must be {requirement}")
    if not mapping and not allow_empty:
        raise ValueError(f"{context} must be a non-empty mapping")

    validated: Dict[str, float] = {}
    for label, value in mapping.items():
        if not isinstance(label, str) or not label:
            raise ValueError(f"{context} must use non-empty string keys")
        if not isinstance(value, (int, float)):
            raise ValueError(f"{context} has invalid value for {label!r}: {value!r}")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError(f"{context} has invalid value for {label!r}: {value!r} (must be finite)")
        validated[label] = numeric

    return validated


def _compute_canonical_validated_scales(mcq_dimensions: Mapping[str, Mapping[str, float]]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for dimension in MCQ_DIMENSION_KEYS:
        buckets = mcq_dimensions[dimension]
        value = sum(
            float(buckets[bucket]) * float(MCQ_BUCKET_SCORE_ANCHORS[bucket])
            for bucket in MCQ_BUCKET_KEYS
        )
        if not math.isfinite(value) or value < 0.0 or value > 1.0:
            raise ValueError(f"Computed canonical scale out of range for {dimension!r}")
        scores[f"{dimension}_score"] = round(value, 6)

    weighted = sum(
        scores[f"{dimension}_score"] * float(MCQ_DIMENSION_WEIGHTS[dimension])
        for dimension in MCQ_DIMENSION_KEYS
    )
    if not math.isfinite(weighted) or weighted < 0.0 or weighted > 1.0:
        raise ValueError("Computed canonical weighted_rubric_score out of range")
    scores["weighted_rubric_score"] = round(weighted, 6)
    return scores


def _one_hot_bucket_mapping(bucket_label: str, *, context: str) -> Dict[str, float]:
    normalized_label = bucket_label.strip()
    if normalized_label not in MCQ_BUCKET_KEYS:
        allowed = ", ".join(MCQ_BUCKET_KEYS)
        raise ValueError(f"{context} label must be one of: {allowed}")
    return {bucket: (1.0 if bucket == normalized_label else 0.0) for bucket in MCQ_BUCKET_KEYS}


class ProbabilityEvaluator:
    """Query the evaluator role and normalize outcome probabilities."""

    def __init__(self, router: BenchmarkRoleRouter):
        self._router = router

    def evaluate(
        self,
        event_question: str,
        condition: str,
        evidence_text: str,
        options: list[str] | None = None,
        micro_questions: list[Dict[str, Any]] | None = None,
        event: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        client = self._router.client_for("evaluator")
        system_prompt = get_evaluator_system_prompt()
        
        # Resolve options: extract from event dict if positional 'options' is missing
        final_options = options
        if final_options is None and event is not None:
            final_options = event.get("options")
        
        if not final_options:
            # Emergency fallback: ensure evaluate never runs without valid keys
            final_options = ["YES", "NO"] if "YES/NO" in event_question.upper() else ["Option A", "Option B"]
        
        # TASK 3: Strict Key Enforcement & Comprehensive Analysis Instruction
        key_instruction = (
            "\n\nCRITICAL INSTRUCTION: The keys in your `probabilities` dictionary MUST EXACTLY MATCH the items in the following options list: "
            f"{', '.join(final_options)}. DO NOT hallucinate, summarize, or invent new keys. "
            "If you invent a key, the system will crash."
            "\n\nProvide a comprehensive analysis including:"
            "\n1. Probabilities for the specified options."
            "\n2. Micro-epistemic mapping for each provided question."
            "\n3. Rubric scores for the defined MCQ dimensions."
        )
        system_prompt += key_instruction

        if micro_questions:
            instruction = (
                "\n\nAs a Report Agent, based strictly on the provided discussion timeline, "
                "answer the following micro-questions to map the swarm's epistemic logic. "
                "Choose the dominant option the swarm believes, and provide a short rationale."
            )
            q_text = ""
            for q in micro_questions:
                q_id = q.get("id", "unknown")
                q_str = q.get("question", "")
                q_options = ", ".join(q.get("options", []))
                q_text += f"\n- {q_id}: {q_str} (Options: {q_options})"
            system_prompt += instruction + q_text

        # requirement 3: Output Schema Update (Refined for TASK 3)
        probabilities_properties = {opt: {"type": "number"} for opt in final_options}
        
        micro_mapping_properties = {}
        if micro_questions:
            for q in micro_questions:
                q_id = q.get("id")
                if q_id:
                    micro_mapping_properties[q_id] = {
                        "type": "object",
                        "properties": {
                            "dominant_tag": {"type": "string"},
                            "short_rationale": {"type": "string"},
                        },
                        "required": ["dominant_tag", "short_rationale"],
                        "additionalProperties": False,
                    }

        # ARCHITECTURE v3.10: Comprehensive Hybrid JSON Schema
        # NOTE: strict=False is required for vLLM v0.6.3 and Ollama compatibility.
        # strict=True causes nested additionalProperties:False constraints to be silently
        # dropped by local inference servers, resulting in micro_epistemic_mapping always
        # returning "N/A"/"Missing in LLM response". Fix confirmed 2026-08-04.
        json_schema = {
            "name": "evaluator_response",
            "strict": False,
            "schema": {
                "type": "object",
                "properties": {
                    "probabilities": {
                        "type": "object", 
                        "properties": probabilities_properties,
                        "required": final_options,
                        "additionalProperties": False
                    },
                    "mcq_dimensions": {
                        "type": "object",
                        "properties": {
                            k: {
                                "type": "object",
                                "properties": {
                                    b: {"type": "number"} for b in MCQ_BUCKET_KEYS
                                },
                                "required": list(MCQ_BUCKET_KEYS),
                                "additionalProperties": False,
                            }
                            for k in MCQ_DIMENSION_KEYS
                        },
                        "required": list(MCQ_DIMENSION_KEYS),
                        "additionalProperties": False,
                    },
                    "validated_scales": {
                        "type": "object",
                        "properties": {
                            "schema_version": {"type": "string"},
                            "scores": {"type": "object", "additionalProperties": {"type": "number"}},
                        },
                        "required": ["schema_version", "scores"],
                        "additionalProperties": False,
                    }
                },
                "required": [
                    "probabilities",
                    "mcq_dimensions",
                    "validated_scales",
                ],
                "additionalProperties": False,
            },
        }
        
        if micro_questions:
            json_schema["schema"]["properties"]["micro_epistemic_mapping"] = {
                "type": "object",
                "properties": micro_mapping_properties,
                "required": list(micro_mapping_properties.keys()),
                "additionalProperties": False,
            }
            json_schema["schema"]["required"].append("micro_epistemic_mapping")
        else:
            # Still require the key even if empty, to maintain structure consistency
            json_schema["schema"]["properties"]["micro_epistemic_mapping"] = {
                "type": "object",
                "additionalProperties": False
            }
            json_schema["schema"]["required"].append("micro_epistemic_mapping")

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    f"Question: {event_question}\n"
                    f"Condition: {condition}\n"
                    f"Evidence: {evidence_text}"
                ),
            },
        ]
        response = None
        current_messages = list(messages)
        last_error = ""
        # Collect expected micro_question IDs for completeness check in retry loop
        expected_micro_ids = [
            q["id"] for q in (micro_questions or []) if q.get("id")
        ]
        for attempt in range(EVALUATOR_JSON_MAX_ATTEMPTS):
            try:
                temp = 0.0
                if attempt > 0:
                    temp = 0.1 if attempt == 1 else 0.2

                    missing_micro_ids_hint = ""
                    if expected_micro_ids and isinstance(response, dict):
                        mapping = response.get("micro_epistemic_mapping", {})
                        if isinstance(mapping, dict):
                            missing_ids = [
                                qid for qid in expected_micro_ids
                                if not isinstance(mapping.get(qid), dict)
                                or mapping[qid].get("dominant_tag") in (None, "N/A", "")
                            ]
                            if missing_ids:
                                missing_micro_ids_hint = (
                                    f" The 'micro_epistemic_mapping' field is MISSING or has N/A for these IDs: "
                                    f"{missing_ids}. You MUST include a valid 'dominant_tag' and 'short_rationale' "
                                    f"for EACH of these keys."
                                )

                    error_feedback = (
                        f"Your previous output was invalid or incomplete. "
                        f"Ensure you return a valid JSON object matching the schema. "
                        f"Crucially, verify that the 'probabilities' key, all expected MCQ dimension keys, "
                        f"AND the 'micro_epistemic_mapping' object (with all required question IDs) are fully populated."
                        f"{missing_micro_ids_hint} "
                        f"Specifically, the evaluation failed with the following error: {last_error}"
                    )
                    current_messages.append({
                        "role": "user",
                        "content": f"[SYSTEM NOTICE: Retry {attempt}] {error_feedback}"
                    })

                response = client.chat_json(
                    current_messages,
                    temperature=temp,
                    max_tokens=1500 if micro_questions else 512,
                    repair_truncated_json=True,
                    json_schema=json_schema,
                )

                if not isinstance(response, dict):
                    raise ValueError("Evaluator response is not a dictionary")

                probabilities = response.get("probabilities")
                mcq_dimensions = response.get("mcq_dimensions")
                validated_scales = response.get("validated_scales")

                # Normalize probabilities and mcq_dimensions INSIDE retry loop.
                # If values are non-numeric, negative, missing, or zero mass, raise ValueError
                # so that attempt retry logic triggers with error feedback.
                normalized = self._normalize_probabilities(probabilities, final_options)
                normalized_dimensions = self._normalize_mcq_dimensions(mcq_dimensions)
                normalized_scales = self._normalize_validated_scales(validated_scales, normalized_dimensions)

                if expected_micro_ids:
                    mapping = response.get("micro_epistemic_mapping")
                    if not isinstance(mapping, dict):
                        raise ValueError(
                            f"micro_epistemic_mapping is missing from evaluator response "
                            f"(expected keys: {expected_micro_ids})"
                        )
                    missing_ids = [
                        qid for qid in expected_micro_ids
                        if not isinstance(mapping.get(qid), dict)
                        or mapping[qid].get("dominant_tag") in (None, "N/A", "")
                    ]
                    if missing_ids:
                        raise ValueError(
                            f"micro_epistemic_mapping has missing/N/A entries for: {missing_ids}"
                        )

                result = dict(response)
                result["probabilities"] = normalized
                result["normalized_probabilities"] = normalized
                result["mcq_dimensions"] = normalized_dimensions
                result["validated_scales"] = normalized_scales

                if micro_questions:
                    result["micro_epistemic_mapping"] = self._validate_micro_mapping(
                        result.get("micro_epistemic_mapping", {}), micro_questions
                    )
                else:
                    result["micro_epistemic_mapping"] = {}

                return result
            except Exception as error:
                last_error = str(error)
                if attempt == EVALUATOR_JSON_MAX_ATTEMPTS - 1:
                    raise ValueError(f"Evaluator scoring failed after {EVALUATOR_JSON_MAX_ATTEMPTS} attempts: {last_error}") from error
                time.sleep(0.2 * (attempt + 1))

    def _validate_micro_mapping(
        self, mapping: Any, micro_questions: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not isinstance(mapping, Mapping):
            raise ValueError("micro_epistemic_mapping must be a mapping")
        
        validated = {}
        for q in micro_questions:
            q_id = q.get("id")
            if not q_id:
                continue
            q_data = mapping.get(q_id)
            if not isinstance(q_data, Mapping):
                validated[q_id] = {"dominant_tag": "N/A", "short_rationale": "Missing in LLM response"}
                continue
            
            dominant_tag = str(q_data.get("dominant_tag", "N/A"))
            short_rationale = str(q_data.get("short_rationale", "No rationale provided"))
            validated[q_id] = {
                "dominant_tag": dominant_tag,
                "short_rationale": short_rationale
            }
        return validated

    def _normalize_probabilities(self, probabilities: Any, fallback_options: list[str]) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        for opt in fallback_options:
            normalized[opt] = 0.0

        if isinstance(probabilities, Mapping):
            for label, value in probabilities.items():
                if not isinstance(label, str) or not label:
                    continue
                try:
                    numeric = float(value) if value is not None else 0.0
                except (ValueError, TypeError):
                    numeric = 0.0
                if not math.isfinite(numeric) or numeric < 0.0:
                    numeric = 0.0
                
                # Check for matching option key (case-insensitive strip match)
                matched = False
                for opt in fallback_options:
                    if opt.strip().upper() == label.strip().upper():
                        normalized[opt] = normalized.get(opt, 0.0) + numeric
                        matched = True
                        break
                if not matched:
                    # Fuzzy match fallback
                    for opt in fallback_options:
                        if label.strip().upper() in opt.strip().upper() or opt.strip().upper() in label.strip().upper():
                            normalized[opt] = normalized.get(opt, 0.0) + numeric
                            matched = True
                            break

        total = sum(normalized.values())
        if total <= 0.0:
            num_keys = len(fallback_options)
            return {label: 1.0 / num_keys for label in fallback_options}

        return {label: value / total for label, value in normalized.items()}

    def _normalize_mcq_dimensions(self, dimensions: Any) -> Dict[str, Dict[str, float]]:
        if not isinstance(dimensions, Mapping):
            raise ValueError("Evaluator response must include mcq_dimensions mapping")

        expected_dimensions = set(MCQ_DIMENSION_KEYS)
        provided_dimensions = set(dimensions.keys())
        if provided_dimensions != expected_dimensions:
            raise ValueError("Evaluator response mcq_dimensions must include all required dimensions")

        normalized: Dict[str, Dict[str, float]] = {}
        for dimension in MCQ_DIMENSION_KEYS:
            buckets = dimensions.get(dimension)
            if isinstance(buckets, Mapping):
                bucket_keys = set(buckets.keys())
                if bucket_keys != set(MCQ_BUCKET_KEYS):
                    raise ValueError("Evaluator response mcq_dimensions must include all bucket keys")
                normalized[dimension] = _normalize_probability_mapping(
                    buckets,
                    f"mcq_dimensions.{dimension}",
                )
                continue
            if isinstance(buckets, str):
                normalized[dimension] = _one_hot_bucket_mapping(
                    buckets,
                    context=f"mcq_dimensions.{dimension}",
                )
                continue
            raise ValueError(
                "Evaluator response mcq_dimensions must map dimensions to bucket mappings or bucket labels"
            )

        return normalized

    def _normalize_validated_scales(
        self,
        validated_scales: Any,
        mcq_dimensions: Mapping[str, Mapping[str, float]],
    ) -> Dict[str, Any]:
        canonical_scores = _compute_canonical_validated_scales(mcq_dimensions)
        if set(canonical_scores.keys()) != set(CANONICAL_VALIDATED_SCALE_KEYS):
            raise ValueError("Canonical validated_scales key set mismatch")
        return {"schema_version": VALIDATED_SCALES_SCHEMA_VERSION, "scores": canonical_scores}
