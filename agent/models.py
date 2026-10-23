from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class MAPObject(BaseModel):
    """
    Measurable Action Point (MAP) schema.
    Converts unstructured regulatory directives into strictly validated,
    auditable compliance mandates.
    """
    action_id: str = Field(..., description="Unique deterministic identifier for the action point")
    action: str = Field(..., min_length=10, description="The concrete task or operational requirement")
    department: List[str] = Field(..., min_length=1, description="Target departments accountable for execution")
    deadline: str = Field(default="None", description="Normalized ISO date (YYYY-MM-DD) or 'None'")
    deadline_type: Literal["explicit", "derived", "implicit"] = Field(
        default="implicit",
        description="Whether deadline was explicitly stated, calculated, or implicit"
    )
    priority: Literal["Critical", "High", "Medium", "Low"] = Field(
        default="Medium",
        description="Assigned enforcement priority"
    )
    obligation_type: Literal["REQUIRED", "PROHIBITED", "ADVISORY"] = Field(
        default="REQUIRED",
        description="Nature of the legal obligation"
    )
    source_sentence: str = Field(..., min_length=10, description="Exact source quote from circular text")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="AI confidence score between 0.0 and 1.0")
    circular_id: str = Field(..., description="Reference ID or hash of the circular")
    conditions: Optional[str] = Field(default=None, description="Scope or applicability condition")
    is_superseded: bool = Field(default=False, description="Whether this obligation was superseded by a newer circular")
    superseded_by: Optional[str] = Field(default=None, description="Circular ID that superseded this obligation")

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 2)


class HallucinationValidator:
    """
    Guards against LLM hallucinations by ensuring every generated MAP's
    source_sentence is anchored to the genuine document text.
    """

    @staticmethod
    def verify_source_quote(source_sentence: str, document_text: str) -> dict:
        """
        Verifies if the claimed source sentence exists in the source text.
        Returns match status and confidence penalty.
        """
        if not source_sentence or not document_text:
            return {"verified": False, "score": 0.0, "reason": "Empty quote or document text"}

        clean_quote = " ".join(source_sentence.lower().split())
        clean_doc = " ".join(document_text.lower().split())

        # 1. Exact substring match
        if clean_quote in clean_doc:
            return {"verified": True, "score": 1.0, "reason": "Exact substring match verified"}

        # 2. Token overlap similarity match (handles minor OCR or punctuation discrepancies)
        quote_tokens = set(re_tokenize(clean_quote))
        if not quote_tokens:
            return {"verified": False, "score": 0.0, "reason": "No valid tokens in quote"}

        doc_tokens = set(re_tokenize(clean_doc))
        common = quote_tokens.intersection(doc_tokens)
        overlap = len(common) / len(quote_tokens)

        if overlap >= 0.85:
            return {
                "verified": True,
                "score": round(overlap, 2),
                "reason": f"High lexical overlap match ({overlap:.0%})"
            }

        return {
            "verified": False,
            "score": round(overlap, 2),
            "reason": f"Hallucination Warning: Quote not found in source document ({overlap:.0%} overlap)"
        }


def re_tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer for overlap comparison."""
    import re
    return re.findall(r'[a-zA-Z0-9]+', text.lower())
