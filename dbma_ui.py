"""DBMA v1.1.0 — Production Streamlit Entry Point.

Resolves nested module import path instability when running
`streamlit run ui/app.py` directly from the project root.

The UI application module is imported through the package system,
and execution is delegated to ui.app.main().

Usage:
    streamlit run dbma_ui.py
"""

from ui.app import main

if __name__ == "__main__":
    main()
