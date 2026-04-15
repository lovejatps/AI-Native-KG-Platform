import pytest
from app.ingestion.extractor import extract_kg


def test_extractor_returns_relations():
    """Ensure the fallback extractor returns at least one relation.
    This works without a real LLM key because the fallback heuristic
    generates naive "related_to" edges.
    """
    sample_text = "Alice works at Acme Corp. Bob collaborates with Alice on a project."
    result = extract_kg(sample_text)
    assert isinstance(result, dict)
    # Must contain both keys
    assert "entities" in result and "relations" in result
    # Entities list should be non‑empty
    assert isinstance(result["entities"], list) and len(result["entities"]) > 0
    # Relations list should be non‑empty (fallback generates chain relations)
    assert isinstance(result["relations"], list) and len(result["relations"]) > 0
    # Basic sanity: relation type should be a string
    for rel in result["relations"]:
        assert isinstance(rel.get("type"), str)
