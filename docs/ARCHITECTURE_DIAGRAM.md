# DBMA Architecture Diagrams

## System Overview (Mermaid)

```mermaid
graph TB
    subgraph "Presentation Layer"
        UI[dbma_ui.py<br/>Streamlit Entry Point]
        Tabs[ui/tabs.py<br/>Tab Router]
        Processing[Processing Tab]
        Search[Search Tab]
        Chat[Chat Tab]
        Library[Library Tab]
        Research[Research Tab]
    end

    subgraph "Component Layer"
        SourceLink[ui/components/source_link.py<br/>Clickable Source Navigation]
        Tables[ui/components/tables.py<br/>Search Results Table]
        Sidebar[ui/components/sidebar.py<br/>Sidebar Navigation]
        Styles[ui/components/styles.py<br/>UI Styling]
    end

    subgraph "Core Layer"
        QueryEnh[core/query_enhancements.py<br/>Query Enhancement]
        ResearchWS[core/research_workspace.py<br/>Research Workspace]
        Retrieval[core/retrieval.py<br/>Retrieval Engine]
        ChunkOpt[core/chunking_optimizer.py<br/>optimize_chunks — PRODUCTION]
        HierChunk[core/hierarchical_chunk_builder.py<br/>Hierarchical Chunking — DORMANT, HQ 승인 대기]
        Boundary[core/semantic_boundary_detector.py<br/>Boundary Score]
        Identity[core/identity_registry.py<br/>Identity Registry]
        Constants[core/canonical_constants.py<br/>Canonical Constants]
    end

    subgraph "Pipeline Layer"
        Extraction[core/extractors.py<br/>Document Extraction]
        Normalization[core/text_normalizer.py<br/>Text Normalization]
        TSU[TSU Dataset<br/>In-Memory]
        Metadata[Metadata Layer]
        GoldStandard[Gold Standard<br/>tests/gold_queries.json]
        Ranking[core/ranking<br/>Score-Based Ranking]
        Benchmark[scripts/rag_benchmark.py<br/>Benchmark Suite]
    end

    subgraph "Data Layer"
        SourceDocs[data/<br/>Source Documents]
        Output[output/<br/>Generated Outputs]
        Docs[docs/<br/>Documentation]
        SermonCorpus[sermon_corpus/<br/>Sermon Collector + Analyzer]
        Chroma[ChromaDB<br/>Legacy Only ADR-003]
    end

    UI --> Tabs
    Tabs --> Processing
    Tabs --> Search
    Tabs --> Chat
    Tabs --> Library
    Tabs --> Research

    Search --> SourceLink
    Search --> Tables
    Chat --> SourceLink

    Processing --> Extraction
    Extraction --> Normalization
    Normalization --> ChunkOpt
    ChunkOpt --> TSU
    HierChunk -.dormant, not wired to production.-> Boundary
    TSU --> Metadata
    Metadata --> GoldStandard
    GoldStandard --> Retrieval
    Retrieval --> Ranking
    Ranking --> Benchmark
    Benchmark --> Output

    QueryEnh --> ResearchWS
    ResearchWS --> Retrieval
    Identity --> Constants
```

## Data Flow (Mermaid)

```mermaid
flowchart LR
    User[User Input] --> QE[Query Enhancement<br/>core/query_enhancements.py]
    QE --> RW[Research Workspace<br/>core/research_workspace.py]
    RW --> RET[Retrieval<br/>core/retrieval.py]
    RET --> HC[Hierarchical Chunk<br/>core/hierarchical_chunk_builder.py]
    HC --> BS[Boundary Score<br/>core/semantic_boundary_detector.py]
    BS --> RANK[Ranking<br/>Boundary Score + D5 Metrics]
    RANK --> CIT[Citation Rendering<br/>ui/components/source_link.py]
    CIT --> LLM[LLM Response Generation]
    LLM --> DISP[Result Display<br/>Chat/Search UI]

    Source[Source Documents] --> EXT[Extraction<br/>core/extractors.py]
    EXT --> NORM[Normalization<br/>core/text_normalizer.py]
    NORM --> HC
    HC --> TSU[TSU Dataset<br/>In-Memory]
    TSU --> RET
```

## UI Component Tree (Mermaid)

```mermaid
graph LR
    DBMA[dbma_ui.py] --> T[tabs.py]
    T --> P[Processing Tab]
    T --> S[Search Tab]
    T --> C[Chat Tab]
    T --> L[Library Tab]
    T --> R[Research Tab]

    S --> SL[source_link.py]
    S --> ST[tables.py]
    C --> SL
    C --> SL2[source_link.py]
    L --> SL
    R --> SL

    SL --> NAV[Library Detail<br/>pending source nav]
```

## Core Pipeline Sequence (Mermaid)

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit UI
    participant Q as QueryEnhancements
    participant RW as ResearchWorkspace
    participant R as RetrievalEngine
    participant TSU as TSU Dataset (pre-chunked at ingestion)
    participant RK as Ranker
    participant L as LLM

    Note over TSU: 청킹은 쿼리 시점이 아니라 문서 처리(ingestion) 시점에<br/>1회 수행됨 — 현재 core.chunking_optimizer.optimize_chunks()

    U->>UI: Search/Chat query
    UI->>Q: forward query
    Q->>RW: resolve context
    RW->>R: retrieve candidates
    R->>TSU: query pre-chunked dataset
    TSU-->>R: candidates
    R->>RK: rank results
    RK-->>UI: ranked results
    UI->>U: display with citations
    U->>UI: click source link
    UI->>L: navigate to Library
    L->>U: show document detail
```

## Key Architecture Decisions (ADR Summary)

| ADR | Topic | Status |
|-----|-------|--------|
| ADR-001 | Retrieval-Engine-Authority | accepted
| ADR-006 | Heading-Provider-Registry | accepted
| ADR-007 | Semantic-Boundary-Detector | accepted
| ADR-008 | Semantic-Chunking-Production-Path | accepted, 프로덕션 전환 경로는 미실행
| ADR-009 | SIL-Theology-Engine | 부분 확정 — 구조만, 신학 어휘/임계값은 별도 승인 대기
| ADR-010 | DBMA-REQ-RAG-Evaluation-Quality | 구조 확정, Phase 1 착수 전 미확정 항목 2건 별도 결정 필요
| ADR-011 | Header-Footer-Repetition-Detector | 완료/보류 확정, 2026-07-23

## Research Workspace Layer (Mermaid)

```mermaid
graph TB
    subgraph "Research Workspace Layer"
        RW[core/research_workspace.py<br/>ResearchWorkspace]
        RW:::rw

        subgraph "Workspace State"
            WS[workspace_state<br/>ResearchWorkspaceState]
            DS[document_store<br/>DocumentStore]
            RS[research_state<br/>ResearchState]
        end

        subgraph "Workspace Operations"
            QC[query_context<br/>Query Context Resolution]
            DC[document_collection<br/>Document Collection]
            CS[candidate_selection<br/>Candidate Selection]
            RC[resolve_context<br/>Context Resolution]
        end

        subgraph "Integration Points"
            QE[QueryEnhancement<br/>core/query_enhancements.py]
            RE[RetrievalEngine<br/>core/retrieval.py]
        end
    end

    QC --> WS
    DC --> DS
    CS --> RS
    RC --> WS
    QE --> QC
    RC --> RE

    classDef rw fill:#e1f5fe,stroke:#01579b
```

## Boundary Score Model (Mermaid)

```mermaid
graph TB
    subgraph "Boundary Score Model — core/semantic_boundary_detector.py"
        BSM[BoundaryScoreModel<br/>Score Registry]

        subgraph "Registered Features"
            HB[HeadingBoundaryFeature<br/>heading_provider]
            EB[EmbeddingSimilarityFeature<br/>embedding delta]
            PD[ParagraphDepthFeature<br/>structural depth]
            SD[SectionDensityFeature<br/>section density]
            PH[PageHeaderArtifactFeature<br/>running-header repeats]
        end

        subgraph "Scoring Pipeline"
            SC[score_boundary<br/>Aggregate Scorer]
            TH[threshold comparison<br/>is_boundary decision]
            EV[BoundaryEvent<br/>is_boundary + score]
        end

        subgraph "Heading Integration"
            HP[heading_provider<br/>ProviderRegistry]
            HA[HeadingAssembler<br/>cursor management]
        end
    end

    HB --> SC
    EB --> SC
    PD --> SC
    SD --> SC
    PH --> SC
    SC --> TH
    TH --> EV
    HP --> HB
    HA --> HP

    classDef feature fill:#fff3e0,stroke:#e65100
    class HB,EB,PD,SD,PH feature
```

## Hierarchical Chunk Builder (Mermaid)

```mermaid
graph TB
    subgraph "Hierarchical Chunk Builder — core/hierarchical_chunk_builder.py"
        HCB[build_chunks<br/>Main Entry Point]

        subgraph "Level 1 — Semantic Boundary"
            L1[semantic signal<br/>Boundary Score check]
            SF[flush buffer BEFORE candidate]
        end

        subgraph "Level 2 — Safety Cap Fallback"
            L2[safety_cap<br/>chunk_size × 1.5]
            FF[force flush on overflow]
        end

        subgraph "Level 3 — Hard Fallback"
            L3[word-safe slice<br/>_slice_preserving_words]
            US[unsplittable outlier handling]
        end

        subgraph "Profile Classification"
            PC[classify_document_profile<br/>Signal Profile A/B]
            TH[MEDIAN_CANDIDATE_LENGTH_THRESHOLD<br/>220 chars]
        end

        subgraph "Heading Cursor"
            HC[heading cursor<br/>_advance_heading_cursor]
            HA[HeadingBoundaryFeature<br/>raw signal only]
        end
    end

    L1 --> SF
    L2 --> FF
    L3 --> US
    PC --> TH
    HC --> HA
    HCB --> L1
    HCB --> L2
    HCB --> L3
    HCB --> PC
    HCB --> HC
```

## TLI (Theology Language Intelligence) Architecture (Mermaid)

```mermaid
graph TB
    subgraph "TLI Package — core/tli/"
        TLI[TLI Package<br/>core/tli/__init__.py]

        subgraph "Spell Engine"
            SE[SpellEngine Protocol<br/>Interface]
            SF[create_spell_engine<br/>Factory]
            HN[HunspellSpellEngine<br/>hunspell_adapter.py]
            NO[NoOpSpellEngine<br/>Fallback]
        end

        subgraph "Hunspell Implementation"
            HD[Korean Dictionary<br/>ko_KR.aff/ko_KR.dic]
            CW[Custom Theology Dict<br/>custom_theology.dic]
            JW[Josa Stripping<br/>_STRIPPABLE_JOSA]
        end

        subgraph "Usage"
            UI[UI Integration<br/>spell check]
            AG[Agent Integration<br/>future engines]
        end
    end

    SE --> SF
    SF --> HN
    SF --> NO
    HN --> HD
    HN --> CW
    HN --> JW
    UI --> SE
    AG --> SE

    classDef engine fill:#e8f5e9,stroke:#2e7d32
    class SE,HN,NO,CW engine
```

## SIL (Sermon Intelligence Layer) Architecture (Mermaid)

```mermaid
graph TB
    subgraph "SIL — Generation Service — core/generation.py"
        GS[GenerationService<br/>Main Service]

        subgraph "Generation Modes"
            GM[generate<br/>Blocking]
            GMS[generate_stream<br/>Streaming]
        end

        subgraph "Output"
            GR[GenerationResult<br/>answer + citations]
            GSR[GenerationStream<br/>Iterable chunks]
        end

        subgraph "Prompt Assembly"
            PA[_build_prompt<br/>Context + Question]
            CH[Conversation History<br/>Sliding Window]
        end

        subgraph "Language Purity"
            LC[Language Contamination Check<br/>_detect_script_contamination]
            LR[Language Retry<br/>_MAX_LANGUAGE_RETRIES=2]
            LS[Language Sanitize<br/>_sanitize_script_contamination]
        end

        subgraph "LLM Integration"
            OLL[Ollama API<br/>ollama.generate]
            MM[Default Model<br/>DEFAULT_GEN_MODEL]
        end
    end

    GS --> GM
    GS --> GMS
    GM --> GR
    GMS --> GSR
    PA --> CH
    LC --> LR
    LR --> LS
    GM --> OLL
    GMS --> OLL
    OLL --> MM

    classDef sil fill:#fce4ec,stroke:#880e4f
    class GS,GM,GMS,LC,LR,LS sil
```

## Complete DBMA Data Flow (Mermaid)

```mermaid
flowchart TB
    subgraph "User Input"
        Q[Query]
        S[Search]
        C[Chat]
    end

    subgraph "Query Processing"
        QE[Query Enhancement<br/>core/query_enhancements.py]
        RW[Research Workspace<br/>core/research_workspace.py]
    end

    subgraph "Retrieval Pipeline"
        RE[RetrievalEngine<br/>core/retrieval.py]
        RK[Ranking<br/>Score Aggregation]
    end

    subgraph "Ingestion-time Chunking (DORMANT candidate — not called by retrieval)"
        HC[Hierarchical Chunk<br/>core/hierarchical_chunk_builder.py<br/>HQ 승인 대기]
        BS[Boundary Score<br/>core/semantic_boundary_detector.py<br/>HC 내부에서만 사용]
    end

    subgraph "Generation"
        GS[GenerationService<br/>core/generation.py]
        LLM[Ollama LLM]
    end

    subgraph "TLI Services"
        TLI[Theology Language Intelligence<br/>core/tli/]
        SP[SpellEngine<br/>Hunspell]
    end

    subgraph "Output"
        R[Results]
        CIT[Citations<br/>source_link.py]
    end

    Q --> QE
    S --> QE
    C --> QE
    QE --> RW
    RW --> RE
    RE --> RK
    HC -.dormant, HQ 승인 대기.-> BS
    RK --> GS
    GS --> LLM
    LLM --> R
    TLI --> SP
    R --> CIT
    CIT --> R

    classDef query fill:#e3f2fd,stroke:#1565c0
    class Q,S,C query
    classDef retrieval fill:#fff3e0,stroke:#e65100
    class RE,HC,BS,RK retrieval
    classDef gen fill:#e8f5e9,stroke:#2e7d32
    class GS,LLM gen
```

## Project Structure

This diagram represents the current repository structure and file
containment hierarchy. It does not represent runtime dependencies
or execution flow.

```mermaid
graph TD
    ROOT["DBMA Repository<br/>~/DBMA"]

    subgraph CONFIG["Project Configuration"]
        CFG["config.yaml"]
        PYPROJ["pyproject.toml"]
        REQ["requirements*.txt"]
        ENV["environment.yml"]
        DOCKER["docker-compose.yml"]
        README["README.md"]
    end

    subgraph CORE["core/ — Core Engine"]
        CORE_FILES["35+ modules"]
        TLI["tli/<br/>Spell Engine"]
        EVAL["evaluation/<br/>RAG Judge"]
        SERMON_PKG["sermon/<br/>Bible Books"]
    end

    subgraph UI_PKG["ui/ — Streamlit UI"]
        UI_FILES["app.py, tabs.py<br/>sidebar.py, styles.py"]
        PAGES["pages/<br/>8 page modules"]
        COMPS["components/<br/>7 component modules"]
        STATE_PKG["state/<br/>query processor"]
        THEME_PKG["theme/<br/>colors, spacing"]
    end

    subgraph DOCS_PKG["docs/ — Documentation"]
        ARCH_DOCS["architecture/<br/>ADR files"]
        AGENTS_PKG["agents/<br/>C1 task orders"]
        REL_PKG["releases/<br/>v1.1.0+"]
        STATE_DOC["STATE.md"]
        TODO_DOC["TODO.md"]
    end

    subgraph SCRIPTS_PKG["scripts/ — Engineering"]
        SHADOW["shadow_*<br/>analysis scripts"]
        BENCH["benchmark<br/>scripts"]
        VALID_PKG["validation/<br/>test utilities"]
        UTIL_SCRIPTS["utility<br/>scripts (30+)"]
    end

    subgraph TESTS_PKG["tests/ — Validation"]
        TEST_FILES["test_*.py<br/>130+ test files"]
        FIXTURES_PKG["fixtures/<br/>sample HTML/JSON"]
        ASSETS_PKG["assets/<br/>test PDF"]
    end

    subgraph DATA_PKG["Data & Runtime"]
        SRC_DATA["data/<br/>source documents"]
        CACHE_DIR["cache/<br/>[embedding cache]"]
        OUT_DIR["output/<br/>[generated outputs]"]
    end

    SERMON_CORPUS["sermon_corpus/<br/>collector + analyzer<br/>(top-level, data/의 하위 아님)"]

    ROOT --> CONFIG
    ROOT --> CORE
    ROOT --> UI_PKG
    ROOT --> DOCS_PKG
    ROOT --> SCRIPTS_PKG
    ROOT --> TESTS_PKG
    ROOT --> DATA_PKG
    ROOT --> SERMON_CORPUS

    CORE --> TLI
    CORE --> EVAL
    CORE --> SERMON_PKG

    UI_PKG --> PAGES
    UI_PKG --> COMPS
    UI_PKG --> STATE_PKG
    UI_PKG --> THEME_PKG

    DOCS_PKG --> ARCH_DOCS
    DOCS_PKG --> AGENTS_PKG
    DOCS_PKG --> REL_PKG
```

## Current Sprint Reference

For current sprint status, see `docs/STATE.md`

---

*Generated: 2026-07-27*
*Mermaid rendering: VS Code Markdown Preview or GitHub*
