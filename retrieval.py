from pathlib import Path
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import chromadb
from sentence_transformers import SentenceTransformer

# --------------------------------------------------------------------------- #
# Configuration (sourced from planning.md > Retrieval Approach)
# --------------------------------------------------------------------------- #

# Embedding model, loaded exactly as the spec requires.
MODEL_NAME = "all-MiniLM-L6-v2"

# Where ChromaDB persists its data on disk (already gitignored).
PERSIST_DIR = Path(__file__).parent / "chroma_db"

# Name of the collection that holds our chunk vectors.
COLLECTION_NAME = "uta_reviews"

# Default number of chunks to retrieve per query. planning.md: "Top-k: 5".
DEFAULT_TOP_K = 5

# Module-level singletons so we load the model and open the DB only once.
_model = None
_collection = None


# --------------------------------------------------------------------------- #
# Embedding
# --------------------------------------------------------------------------- #

def get_embedding_model():
    """Return a cached SentenceTransformer instance.

    Loading the model is expensive (it reads weights from disk), so we create
    it once and reuse it for every embedding call — both for indexing chunks
    and for embedding queries. Using the SAME model for both is essential:
    query and document vectors must live in the same vector space to compare.
    """
    global _model
    if _model is None:
        # Loaded exactly as specified in the milestone requirements.
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts):
    """Embed a list of strings into vectors using all-MiniLM-L6-v2.

    Each input string is mapped one-to-one to its own embedding vector. We pass
    the whole list to `encode()` so it batches the work efficiently on the
    model — the per-item mapping is preserved (output[i] is the embedding of
    texts[i]); batching is purely a performance optimisation, not a change in
    behaviour.

    Args:
        texts: List of strings to embed.

    Returns:
        A list of vectors (each a list of floats), aligned with `texts`.
    """
    model = get_embedding_model()
    # normalize_embeddings=True gives unit-length vectors, which makes cosine
    # similarity well-conditioned. convert_to_numpy returns an array we turn
    # into plain Python lists for ChromaDB.
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return embeddings.tolist()


# --------------------------------------------------------------------------- #
# Vector store (ChromaDB)
# --------------------------------------------------------------------------- #

def get_collection(persist_dir=PERSIST_DIR, collection_name=COLLECTION_NAME):
    """Open (or create) the persistent ChromaDB collection.

    ChromaDB API notes:
        * chromadb.PersistentClient(path=...) opens an on-disk database at
          `path`, so vectors survive across program runs (unlike the in-memory
          Client()).
        * get_or_create_collection(...) returns the named collection, creating
          it if it doesn't exist yet — safe to call every run.
        * metadata={"hnsw:space": "cosine"} tells Chroma to build its HNSW index
          using cosine distance. This only takes effect when the collection is
          first created; an existing collection keeps its original space.

    Returns:
        A chromadb Collection object.
    """
    global _collection
    if _collection is None:
        # PersistentClient writes the index/data under `persist_dir`.
        client = chromadb.PersistentClient(path=str(persist_dir))
        _collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # semantic (cosine) similarity
        )
    return _collection


def index_chunks(chunks, batch_size=64):
    """Embed chunks and store them in ChromaDB.

    For each chunk we store, in aligned lists, four things that stay matched by
    position: a unique id, the embedding, the chunk text (document), and the
    metadata. Because all four are built in the same loop iteration, the mapping
    between vector <-> text <-> metadata can never drift.

    We use `upsert` with deterministic ids (f"{source}#{chunk_id}") so running
    this more than once updates existing rows instead of creating duplicates.

    Args:
        chunks: List of dicts, each at least {chunk_id, source, text}.
        batch_size: How many chunks to embed/insert per batch.

    Returns:
        The number of chunks indexed.
    """
    collection = get_collection()

    # Process in batches to bound memory use on larger corpora.
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]

        ids = []        # unique key per chunk
        documents = []  # the chunk text
        metadatas = []  # source, chunk_id (+ source_type if present)
        texts = []      # text to embed (same as documents)

        for chunk in batch:
            source = chunk["source"]
            chunk_id = chunk["chunk_id"]

            # Synthesize a globally-unique id; chunk_id alone is only unique
            # within a single document.
            ids.append(f"{source}#{chunk_id}")
            documents.append(chunk["text"])
            texts.append(chunk["text"])

            metadata = {"source": source, "chunk_id": chunk_id}
            # Carry source_type through if Milestone 3 provided it (optional).
            if "source_type" in chunk:
                metadata["source_type"] = chunk["source_type"]
            metadatas.append(metadata)

        # Embed this batch of texts, then upsert vectors+text+metadata together.
        embeddings = embed_texts(texts)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    return len(chunks)


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #

def retrieve(query: str, k: int = 5):
    """Retrieve the top-k most semantically similar chunks for a query.

    Steps:
        1. Embed the query with the SAME model used to embed the chunks.
        2. Ask ChromaDB for the k nearest stored vectors (semantic search).
        3. Return each hit's text, source, chunk_id, and a cosine distance.

    Scoring convention (as requested):
        We report the cosine *distance* directly, where
            distance = 1 - cosine_similarity
        so LOWER means more similar (0.0 ≈ near-identical meaning) and HIGHER
        means less similar. Results are ordered ascending by distance, i.e.
        most-similar first.

    Args:
        query: The natural-language search query.
        k:     Number of chunks to return (default 5, per planning.md).

    Returns:
        A list of up to k dicts, ordered most- to least-similar:
            {
                "text":     <chunk text>,
                "source":   <originating filename>,
                "chunk_id": <per-document chunk index>,
                "distance": <cosine distance; lower = more similar>,
            }
    """
    collection = get_collection()

    # Guard: an empty collection means index_chunks() hasn't run yet.
    if collection.count() == 0:
        print("[retrieve] Collection is empty — run index_chunks() first.")
        return []

    # 1. Embed the query (embed_texts expects a list; take the single vector).
    query_embedding = embed_texts([query])[0]

    # 2. Semantic nearest-neighbour search. include= asks Chroma to return the
    #    stored text + metadata + distances alongside the matches.
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma returns lists-of-lists (one inner list per query); we sent one
    # query, so we read index [0] of each. Empty results give empty lists.
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # 3. Assemble result dicts. We return the cosine distance as-is, so lower
    #    means more similar (Chroma already orders results ascending by it).
    hits = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        hits.append({
            "text": text,
            "source": metadata.get("source"),
            "chunk_id": metadata.get("chunk_id"),
            "distance": distance,  # cosine distance: lower = more similar
        })
    return hits


# --------------------------------------------------------------------------- #
# Validation / manual inspection
# --------------------------------------------------------------------------- #

def _run_validation():
    """Index the Milestone 3 chunks, then run sample queries and print results."""
    # Consume Milestone 3 output (we do NOT re-implement it here).
    from pipeline import build_chunks, load_documents

    print("=" * 78)
    print("MILESTONE 4 VALIDATION — Embedding, Vector Store & Retrieval")
    print("=" * 78)

    # --- Build chunks (Milestone 3) and index them (Milestone 4) ----------- #
    chunks = build_chunks(load_documents())
    print(f"\nIndexing {len(chunks)} chunks into ChromaDB "
          f"(model='{MODEL_NAME}', space=cosine)...")
    index_chunks(chunks)

    # --- Total vectors stored ---------------------------------------------- #
    collection = get_collection()
    print(f"\n[1] Total vectors stored in ChromaDB: {collection.count()}")

    # --- Sample queries from planning.md ---------- #
    sample_queries = [
        "How does Professor Manfred Huber typically conduct his lectures?",
        "Which professor do students commonly recommend for CSE 3318?",
        "What percentage of students would take Abhishek Santra's class again?",
    ]

    print(f"\n[2] Running {len(sample_queries)} sample queries (k={DEFAULT_TOP_K}):")
    for q_num, query in enumerate(sample_queries, start=1):
        print("\n" + "=" * 78)
        print(f"Query {q_num}: {query}")
        print("=" * 78)

        hits = retrieve(query, k=DEFAULT_TOP_K)

        # --- Print retrieved chunks with metadata -------------------------- #
        for rank, hit in enumerate(hits, start=1):
            # Keep the preview short so the console stays readable.
            preview = hit["text"].replace("\n", " ")
            if len(preview) > 220:
                preview = preview[:220] + "..."
            print(f"\n  Rank {rank} | source='{hit['source']}' "
                  f"| chunk_id={hit['chunk_id']} "
                  f"| distance={hit['distance']:.3f} (lower = more similar)")
            print(f"    {preview}")

    print("\n" + "=" * 78)


if __name__ == "__main__":
    _run_validation()
