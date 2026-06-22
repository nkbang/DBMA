# DBMA

## Project Identity
DBMA is a document-based RAG system. The main entry point is `dbma.py`, which orchestrates the Streamlit UI and the full processing pipeline. `core/` contains document extraction, file handling, processing, chunking optimization, and shared utilities. `dbma_rag.py` handles ChromaDB-based embedding and retrieval. The project is developed on a MacBook Pro Max M5 with 128 GB RAM.

## Working Rules
Use `bge-m3:latest` as the default embedding model. Use `1200` as the default chunk size and `200` as the default overlap. Prefer a simple, modular, tab-based UI. Keep logs easy to read, and when appropriate, save processing status, optimization results, and debugging traces to markdown files. Any chunking or denoising change must be verified in the running code, not assumed from static inspection. Prefer changes that are small, traceable, and reversible.

## Development Loop
Follow loop engineering: define the goal, run the code, inspect the feedback, and correct the pipeline until the result is stable. The current priority is to stabilize parsing, chunking, and `.md` file generation. Track progress with checkpoints and percentages when useful, and keep the implementation state visible as a pipeline or TODO list. Use Cline for debugging and iterative refinement when needed. When debugging RAG or chunking issues, verify import paths, execution flow, and output files step by step.