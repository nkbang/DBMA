"""
core/research_workspace.py — Research session management layer

[SPRINT27-B-2] Implements the research workspace layer as specified in ADR-004.
This module provides session management for research queries while maintaining
the "One Retrieval Engine" principle - it only calls QueryProcessor.process()
via its public interface, never bypassing or extending the retrieval system.

Storage pattern:
- sessions.json in {DEFAULT_OUTPUT_DIR}/research/ (append-only, atomic write)
- Session records contain only references (tsu_id, document_id, citation_id) 
  to TSU dataset content - no content duplication
"""

from __future__ import annotations

import datetime
import json
import os
from typing import Any, Dict, List, Optional

from core.config import DEFAULT_OUTPUT_DIR
from core.retrieval import QueryProcessor


def _sessions_path() -> str:
    """Get the path to sessions.json file."""
    research_dir = os.path.join(DEFAULT_OUTPUT_DIR, "research")
    return os.path.join(research_dir, "sessions.json")


def create_session() -> str:
    """
    Create a new research session.
    
    Returns
    -------
    str
        Unique session ID (timestamp-based).
    """
    session_id = datetime.datetime.now().isoformat(timespec="seconds")
    return session_id


def add_query_result(
    session_id: str,
    query: str,
    response_package: Dict[str, Any]
) -> bool:
    """
    Add a query result to an existing session.
    
    Parameters
    ----------
    session_id : str
        The session ID to add the result to.
    query : str
        The original query text.
    response_package : dict
        The response package from QueryProcessor.process() containing results.
        
    Returns
    -------
    bool
        True if successful, False on failure.
    """
    try:
        # Load existing sessions
        sessions_data = load_sessions()
        sessions = sessions_data.get("sessions", [])
        
        # Find the session or create new one
        session = None
        for s in sessions:
            if s.get("session_id") == session_id:
                session = s
                break
        
        if session is None:
            # Create new session
            session = {
                "session_id": session_id,
                "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "queries": []
            }
            sessions.append(session)
        
        # Extract references from response package. RankedCandidate.to_dict()
        # nests document_id under "metadata", and citation_id only exists on
        # the separate "citations" list (core/retrieval.py ResponsePackage.to_dict)
        # keyed by tsu_id — both looked up accordingly rather than assumed
        # top-level on each result (SPRINT27-C fix).
        citation_id_by_tsu = {
            c.get("tsu_id"): c.get("citation_id")
            for c in response_package.get("citations", [])
            if c.get("tsu_id")
        }

        result_refs = []
        if "top_k_results" in response_package:
            for result in response_package["top_k_results"]:
                # Store only references, not full content
                ref = {}
                tsu_id = result.get("tsu_id")
                if tsu_id:
                    ref["tsu_id"] = tsu_id
                document_id = result.get("metadata", {}).get("document_id")
                if document_id:
                    ref["document_id"] = document_id
                citation_id = citation_id_by_tsu.get(tsu_id)
                if citation_id:
                    ref["citation_id"] = citation_id
                if ref:  # Only add non-empty references
                    result_refs.append(ref)
        
        # Add query to session
        query_entry = {
            "query": query,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "result_refs": result_refs
        }
        session["queries"].append(query_entry)
        
        # Save back to file with atomic write pattern
        sessions_data["sessions"] = sessions
        path = _sessions_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(sessions_data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
        
        return True
    except Exception:
        return False


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a specific session by ID.
    
    Parameters
    ----------
    session_id : str
        The session ID to load.
        
    Returns
    -------
    dict or None
        Session data if found, None otherwise.
    """
    try:
        sessions_data = load_sessions()
        sessions = sessions_data.get("sessions", [])
        
        for session in sessions:
            if session.get("session_id") == session_id:
                return session
        
        return None
    except Exception:
        return None


def load_sessions() -> Dict[str, Any]:
    """
    Load all sessions.
    
    Returns
    -------
    dict
        All sessions data.
    """
    try:
        path = _sessions_path()
        if not os.path.exists(path):
            return {"sessions": []}
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data.get("sessions"), list):
            return {"sessions": []}
            
        return data
    except (json.JSONDecodeError, OSError):
        return {"sessions": []}


def list_sessions() -> List[Dict[str, Any]]:
    """
    List all sessions.
    
    Returns
    -------
    list
        List of session dictionaries.
    """
    try:
        sessions_data = load_sessions()
        return sessions_data.get("sessions", [])
    except Exception:
        return []