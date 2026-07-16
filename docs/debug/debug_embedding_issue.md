# Debugging Embedding Dimension Mismatch Issue

## Understanding the Problem

The error `chromadb.errors.InvalidArgumentError: Collection expecting embedding with dimension of 1024, got 384` indicates a mismatch between:
1. The expected embedding dimensions of an existing ChromaDB collection (1024)
2. The actual dimensions of embeddings being inserted (384)

## Debugging Steps

### 1. Check Existing Collection Dimensions
```bash
# Inspect the chroma database directory
ls -la chroma_db/

# Check if there are any existing collections with their metadata
# This requires inspecting the ChromaDB internal structure or using Python API
```

### 2. Verify Current Embedding Model Configuration
```python
# In dbma.py, add debug prints to see which model is being used
print(f"Using embed_model: {embed_model}")
print(f"DEFAULT_EMBED_MODEL: {DEFAULT_EMBED_MODEL}")

# Check what Ollama models are available
import ollama
try:
    models = ollama.list()
    print("Available Ollama models:", models)
except Exception as e:
    print("Ollama not accessible:", e)
```

### 3. Debug Embedding Generation Process
```python
# Add debugging to the _embed_texts function in dbma.py
def _embed_texts(texts: List[str], model: str = DEFAULT_EMBED_MODEL) -> List[List[float]]:
    """Batch embedding — Ollama or sentence_transformers (SPRINT 1 DISABLED)."""
    print(f"DEBUG: _embed_texts called with model: {model}")
    print(f"DEBUG: Number of texts: {len(texts)}")
    
    if not feature_enabled("embedding"):
        return []
        
    try:
        result = ollama.embed(model=model, input=texts)["embeddings"]
        print(f"DEBUG: Ollama embeddings shape: {len(result)} x {len(result[0]) if result else 0}")
        return result
    except Exception as e:
        print(f"DEBUG: Ollama failed with error: {e}")
        pass
        
    # Fallback to transformer
    result = []
    for t in texts:
        if not t.strip():
            continue
        try:
            embedding = embed_via_transformer(t)  # This is from core.embedder import embed as embed_via_transformer
            print(f"DEBUG: Transformer embedding shape: {len(embedding)}")
            result.append(embedding)
        except Exception as e:
            print(f"DEBUG: Transformer failed with error: {e}")
            result.append([0.0] * 384)  # fallback to 384 dims
    return result
```

### 4. Check Collection Creation Logic
```python
# In get_collection() function, add debugging:
def get_collection():
    """Get or create ChromaDB collection (SPRINT 1 DISABLED)."""
    print("DEBUG: get_collection called")
    if not feature_enabled("vector_db"):
        return None
    client = get_vector_client()
    if client is None:
        return None
        
    # Debug what's happening here
    try:
        collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
        print(f"DEBUG: Collection created/loaded - name: {COLLECTION_NAME}")
        print(f"DEBUG: Collection info: {collection}")
        return collection
    except Exception as e:
        print(f"DEBUG: get_or_create_collection failed: {e}")
        raise
```

### 5. Check Model Dimensions Directly
```python
# Test what dimensions different models produce
from sentence_transformers import SentenceTransformer

# Test the fallback model
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
test_text = "Hello world"
embedding = model.encode(test_text)
print(f"all-mpnet-base-v2 produces {len(embedding)} dimensional embeddings")

# Test the config model
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2') 
embedding = model.encode(test_text)
print(f"all-MiniLM-L6-v2 produces {len(embedding)} dimensional embeddings")
```

### 6. Clear Database and Recreate
If you identify that the issue is due to existing collection dimensions:
```bash
# Remove the existing Chroma database
rm -rf chroma_db/

# Then restart the application to create a fresh collection
```

## Quick Diagnostic Commands

1. **Check what embedding models are available in Ollama**:
   ```bash
   ollama list
   ```

2. **Verify the current config settings**:
   ```python
   # In Python console
   from core.config import DEFAULT_EMBED_MODEL, EMBEDDING_DIMENSION
   print(f"Default embed model: {DEFAULT_EMBED_MODEL}")
   print(f"Expected dimension: {EMBEDDING_DIMENSION}")
   ```

3. **Check if Ollama is running and accessible**:
   ```bash
   curl http://localhost:11434/api/tags