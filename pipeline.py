import re
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Directory holding the source .txt files, resolved relative to this file so
# the pipeline works regardless of the current working directory.
DOCUMENTS_DIR = Path(__file__).parent / "documents"

# Per-source-type chunking parameters (chunk_size, overlap) in characters,
CHUNK_PARAMS = {
    "ratemyprofessors": {"chunk_size": 350, "overlap": 100},
    "reddit": {"chunk_size": 500, "overlap": 100},
}

# Default parameters when a file's source type can't be determined
DEFAULT_SOURCE_TYPE = "ratemyprofessors"


# --------------------------------------------------------------------------- #
# Stage 1 — Document loading
# --------------------------------------------------------------------------- #

def detect_source_type(source):
    """Infer the source type from a file's name.

    The chunking parameters in planning.md are defined per *source type*, so we
    need a rule that maps each file to a type. We use the filename prefix.

    Args:
        source: Filename or relative path (e.g. "rmp_david_kung.txt").

    Returns:
        "ratemyprofessors", "reddit", or DEFAULT_SOURCE_TYPE if unrecognized.
    """
    # Look only at the bare filename, lowercased, so nested paths still work.
    name = Path(source).name.lower()

    if name.startswith("rmp_"):
        return "ratemyprofessors"
    if name.startswith("reddit_"):
        return "reddit"

    # Unknown prefix: warn and fall back so ingestion doesn't silently misbehave.
    print(f"[detect_source_type] Unknown prefix for '{source}', "
          f"defaulting to '{DEFAULT_SOURCE_TYPE}'")
    return DEFAULT_SOURCE_TYPE


def load_documents(documents_dir=DOCUMENTS_DIR):
    """Recursively load every .txt file under `documents_dir`.

    Args:
        documents_dir: Path (or str) to the folder containing the .txt files.

    Returns:
        A list of dicts, one per successfully read file:
            {
                "source":      <relative path of the file>,
                "source_type": "ratemyprofessors" | "reddit",
                "text":        <raw file text>,
            }
    """
    # Accept either a str or a Path and normalize to a Path object.
    documents_dir = Path(documents_dir)

    documents = []

    # Guard against a missing/incorrect directory so the caller gets a clear
    # message instead of an empty result that's hard to debug.
    if not documents_dir.is_dir():
        print(f"[load_documents] Directory not found: {documents_dir}")
        return documents

    # rglob("*.txt") walks the directory tree recursively, matching .txt files
    # in `documents_dir` and any nested subfolders. Sorted for deterministic order.
    for file_path in sorted(documents_dir.rglob("*.txt")):
        # Skip anything that isn't a regular file (e.g. a stray directory match).
        if not file_path.is_file():
            continue

        try:
            # Read the full file as UTF-8 text. The default errors="strict"
            # means malformed bytes raise instead of being silently dropped.
            raw_text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            # Error handling: an unreadable or non-UTF-8 file shouldn't crash
            # the whole ingestion run. Log it and move on to the next file.
            print(f"[load_documents] Skipping unreadable file {file_path}: {error}")
            continue

        # Skip empty files so they don't pollute the corpus downstream.
        if not raw_text.strip():
            print(f"[load_documents] Skipping empty file: {file_path}")
            continue

        # Use the path relative to documents_dir as the source identifier. This
        # keeps names unique even when files live in subfolders, while remaining
        # human-readable (e.g. "rmp_david_kung.txt").
        source = str(file_path.relative_to(documents_dir))

        documents.append({
            "source": source,
            "source_type": detect_source_type(source),
            "text": raw_text,
        })

    # Summary so the user can confirm how many documents were ingested.
    print(f"[load_documents] Loaded {len(documents)} document(s) from {documents_dir}")
    return documents


# --------------------------------------------------------------------------- #
# Stage 1b — Cleaning
# --------------------------------------------------------------------------- #

def clean_text(raw_text):
    """Clean a document's text while preserving its meaningful content.

    The cleaning is deliberately conservative: it tidies up whitespace and
    removes invisible/garbled characters, but keeps all readable content
    (review text, ratings, professor names, and header/URL metadata) so that
    nothing needed for retrieval is lost.

    Steps:
        1. Unicode-normalize (NFKC) so look-alike characters become canonical.
        2. Convert non-breaking spaces to regular spaces.
        3. Normalize line endings (\\r\\n and \\r -> \\n).
        4. Remove control/non-printable characters, keeping newlines and tabs.
        5. Strip trailing whitespace on each line and collapse runs of blank
           lines down to a single blank line.
        6. Strip leading/trailing whitespace from the whole document.

    Args:
        raw_text: The raw text of a single document.

    Returns:
        The cleaned text as a string.
    """
    # 1. Canonicalize Unicode (e.g. fancy quotes / fullwidth chars -> standard).
    text = unicodedata.normalize("NFKC", raw_text)

    # 2. Non-breaking spaces and similar look like spaces but aren't; normalize.
    text = text.replace(" ", " ")

    # 3. Normalize Windows/Mac line endings to plain "\n".
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 4. Drop control characters (category "C") except newline and tab, which we
    #    keep so paragraph and column structure survives.
    text = "".join(
        ch for ch in text
        if ch in ("\n", "\t") or not unicodedata.category(ch).startswith("C")
    )

    # 5a. Remove trailing spaces/tabs at the end of every line.
    text = re.sub(r"[ \t]+(\n)", r"\1", text)

    # 5b. Collapse 3+ consecutive newlines into a single blank line (\n\n) so
    #     paragraph breaks are preserved but large gaps are tidied.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 6. Trim leading/trailing whitespace for the document as a whole.
    return text.strip()


# --------------------------------------------------------------------------- #
# Stage 2 — Chunking
# --------------------------------------------------------------------------- #

def chunk_text(text, chunk_size, overlap):
    """Split text into fixed-size, character-based chunks with overlap.

    Uses a sliding window: each chunk is `chunk_size` characters long, and the
    window advances by `step = chunk_size - overlap` characters, so consecutive
    chunks share `overlap` characters of context. The final chunk may be shorter
    than `chunk_size` (the trailing remainder). Whitespace-only chunks are
    dropped, and each kept chunk is stripped of leading/trailing whitespace.

    Args:
        text:       The (already cleaned) text to split.
        chunk_size: Maximum chunk length in characters (must be > 0).
        overlap:    Number of characters shared between consecutive chunks
                    (must satisfy 0 <= overlap < chunk_size).

    Returns:
        A list of chunk strings.
    """
    # Validate parameters up front so misconfiguration fails loudly rather than
    # producing a non-advancing window (an infinite loop) or odd output.
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    if not 0 <= overlap < chunk_size:
        raise ValueError(
            f"overlap must satisfy 0 <= overlap < chunk_size; "
            f"got overlap={overlap}, chunk_size={chunk_size}"
        )

    # How far the window advances each step. Guaranteed positive by the checks.
    step = chunk_size - overlap

    chunks = []
    # Slide the window from the start of the text to the end.
    for start in range(0, len(text), step):
        # Slice out one window; Python clamps the end index for the last chunk.
        chunk = text[start:start + chunk_size].strip()
        if chunk:  # Skip windows that are empty after stripping.
            chunks.append(chunk)

        # Once the window reaches the end of the text, stop; otherwise the loop
        # would emit duplicate trailing slices.
        if start + chunk_size >= len(text):
            break

    return chunks


def build_chunks(documents):
    """Clean and chunk a list of loaded documents.

    Ties the pipeline together: for each document it cleans the text, looks up
    the chunk size/overlap for that document's source type, and produces chunk
    records carrying enough metadata for the later embedding/retrieval stages.

    Args:
        documents: Output of `load_documents()` — a list of dicts with
                   "source", "source_type", and "text".

    Returns:
        A list of chunk dicts:
            {
                "source":      <originating filename>,
                "source_type": "ratemyprofessors" | "reddit",
                "chunk_id":    <0-based index of this chunk within its document>,
                "text":        <chunk text>,
            }
    """
    all_chunks = []

    for doc in documents:
        # Clean before chunking so character offsets are computed on tidy text.
        cleaned = clean_text(doc["text"])

        # Pick chunk size/overlap based on the document's source type.
        params = CHUNK_PARAMS.get(doc["source_type"], CHUNK_PARAMS[DEFAULT_SOURCE_TYPE])

        # Produce the chunks for this single document.
        doc_chunks = chunk_text(cleaned, params["chunk_size"], params["overlap"])

        # Wrap each chunk with metadata, numbering chunks within the document.
        for chunk_id, chunk in enumerate(doc_chunks):
            all_chunks.append({
                "source": doc["source"],
                "source_type": doc["source_type"],
                "chunk_id": chunk_id,
                "text": chunk,
            })

    return all_chunks


# --------------------------------------------------------------------------- #
# Validation / manual inspection
# --------------------------------------------------------------------------- #

def _run_validation():
    """Run the Milestone 3 pipeline and print checks for manual inspection."""
    print("=" * 70)
    print("MILESTONE 3 VALIDATION — Ingestion & Chunking")
    print("=" * 70)

    # --- Load -------------------------------------------------------------- #
    documents = load_documents()
    print(f"\n[1] Number of documents loaded: {len(documents)}")

    if not documents:
        print("No documents found — nothing to validate.")
        return

    # --- Show one cleaned document ----------------------------------------- #
    sample_doc = documents[0]
    cleaned_sample = clean_text(sample_doc["text"])
    print("\n[2] One cleaned document "
          f"(source='{sample_doc['source']}', type='{sample_doc['source_type']}', "
          f"{len(cleaned_sample)} chars):")
    print("-" * 70)
    print(cleaned_sample)
    print("-" * 70)

    # --- Build all chunks -------------------------------------------------- #
    chunks = build_chunks(documents)

    # --- Show 5 representative chunks -------------------------------------- #
    # Pick chunks spread evenly across the full set so the sample represents
    # different documents and both source types, not just the first few.
    print("\n[3] 5 representative chunks:")
    sample_count = min(5, len(chunks))
    if sample_count:
        step = max(1, len(chunks) // sample_count)
        sample_indices = [i * step for i in range(sample_count)]
        for idx in sample_indices:
            chunk = chunks[idx]
            print("-" * 70)
            print(f"global #{idx} | source='{chunk['source']}' "
                  f"| type='{chunk['source_type']}' | chunk_id={chunk['chunk_id']} "
                  f"| len={len(chunk['text'])}")
            print(chunk["text"])
        print("-" * 70)

    # --- Total chunk count ------------------------------------------------- #
    print(f"\n[4] Total number of chunks generated: {len(chunks)}")
    print("=" * 70)


if __name__ == "__main__":
    _run_validation()
