                    Human HQ
                       |
                       |
                 Governance Layer
                       |
          +------------+------------+
          |                         |
         C1                        CUE
   Planning Brain            Execution Agent
          |                         |
          +------------+------------+
                       |
                 DBMA Core


DBMA Core

        Document
           |
           v
      Extraction
           |
           v
      Normalization
           |
           v
       Chunking
           |
           v
      Embedding
           |
           v
   TSU dataset (in-memory)
   [Qdrant/Chroma: legacy-only,
    ADR-003, 검색 경로 미사용]
           |
           v
    RetrievalEngine
           |
           v
       Research UI