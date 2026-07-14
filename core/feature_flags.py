"""
Feature Flag Management System
Prepares for capability-based feature control
"""

# ─── SPRINT 2 FEATURE FLAG ───────────────────────────────
# Sprint 1 = False → PURE DATA LAYER ONLY (parse → clean → chunk → store .md)
# Sprint 2+ = True  → Re-enable embedding, vector DB, LLM, RAG
SPRINT2_FEATURES = True  # Set True to enable all features


def feature_enabled(name: str) -> bool:
    """
    Check if a specific feature is enabled.
    
    Args:
        name (str): Feature name to check
        
    Returns:
        bool: True if feature is enabled, False otherwise
        
    Note: 
        For Sprint 1, all features return False except those explicitly enabled
        This provides a clean architecture for future expansion
    """
    # For now, reference the global SPRINT2_FEATURES flag
    # In future sprints, this can be expanded to individual feature flags
    if name in ["embedding", "vector_db", "rag", "llm", "benchmark"]:
        return SPRINT2_FEATURES
    return False


# Feature capability mappings (for future expansion)
FEATURE_CAPABILITIES = {
    "embedding": {"enabled": SPRINT2_FEATURES, "description": "Text embedding functionality"},
    "vector_db": {"enabled": SPRINT2_FEATURES, "description": "Vector database integration"},
    "rag": {"enabled": SPRINT2_FEATURES, "description": "Retrieval Augmented Generation"},
    "llm": {"enabled": SPRINT2_FEATURES, "description": "Large Language Model interactions"},
    "benchmark": {"enabled": SPRINT2_FEATURES, "description": "Performance benchmarking"},
}