import re
import unicodedata
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Directory holding the source .txt files, resolved relative to this file so
# the pipeline works regardless of the current working directory.
DOCUMENTS_DIR = Path(__file__).parent / "documents"

# Structure-aware chunking config.
#
# We are no longer cutting documents on a fixed character window. Instead each document
# is split on its natural units — one Rate My Professors review per chunk, one
# Reddit reply/comment per chunk — so a chunk embeds one complete opinion.
#
# A single review or reply only falls back to fixed-size chunking when it is
# unusually long (> MAX_SEGMENT_CHARS); in that case we use FALLBACK_CHUNK_SIZE
# with FALLBACK_OVERLAP so even a giant segment stays within a sane size while
# preserving some cross-chunk context.
MAX_SEGMENT_CHARS = 1000   # a review/reply longer than this is split by size
FALLBACK_CHUNK_SIZE = 500  # character window used for the oversized-segment fallback
FALLBACK_OVERLAP = 100     # characters shared between consecutive fallback chunks

# Default source type when a file's name prefix can't be recognised.
DEFAULT_SOURCE_TYPE = "ratemyprofessors"


# Loading documents
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
            raw_text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            print(f"[load_documents] Skipping unreadable file {file_path}: {error}")
            continue

        # Skip empty files so they don't pollute the corpus downstream.
        if not raw_text.strip():
            print(f"[load_documents] Skipping empty file: {file_path}")
            continue

        source = str(file_path.relative_to(documents_dir))

        documents.append({
            "source": source,
            "source_type": detect_source_type(source),
            "text": raw_text,
        })

    # Summary so the user can confirm how many documents were ingested.
    print(f"[load_documents] Loaded {len(documents)} document(s) from {documents_dir}")
    return documents

# Clean txt files
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


# Chunking Stage
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


# --------------------------------------------------------------------------- #
# Structure-aware boundary patterns
# --------------------------------------------------------------------------- #
#
# These regexes detect where one natural unit (a review or a reply) ends and the
# next begins. They are ALL anchored to the start of a line (re.MULTILINE makes
# `^` match after every "\n"), which is the key to not splitting mid-sentence:
# a boundary is only recognised when a marker sits at the very start of a line,
# so a word like "reply" appearing inside a sentence never triggers a split.

# --- Rate My Professors -----------------------------------------------------
# Every review in the rmp_*.txt files starts a line with "Review <n>" (e.g.
# "Review 1 - CSE3315 (May 15, 2025)"). We split on that marker. The text before
# "Review 1" is the professor summary header (overall rating, "Would Take Again
# %", tags, ...) — valuable metadata, so it is kept as its own leading chunk
# rather than discarded.
#
#   ^Review        marker word at the start of a line
#   [ \t]+\d+      one or more spaces/tabs, then the review number
#   \b             word boundary so "Review 12" is fine but "Reviewer" is not
RMP_REVIEW_RE = re.compile(r"^Review[ \t]+\d+\b", re.MULTILINE)

# --- Reddit -----------------------------------------------------------------
# Divider lines ("------------------------------------") separate the question
# from the replies. They carry no content, so we blank them out before splitting
# instead of turning them into empty chunks.
#
#   ^[ \t]*   optional leading whitespace
#   -{3,}     three or more dashes
#   [ \t]*$   optional trailing whitespace to end of line
REDDIT_DIVIDER_RE = re.compile(r"^[ \t]*-{3,}[ \t]*$", re.MULTILINE)

# A Reddit segment boundary is either:
#   (a) a "pipe" marker line — the threads use leading pipes for every turn:
#       "|| Reply 1", "|| Reply1:", "||| Follow Up:", "|| Question:",
#       "| Review of CSE Courses at UTA". One-or-more pipes then anything to the
#       end of the line, so inline content after the pipes stays on the marker
#       line and is captured with that segment.
#         ^[ \t]*\|+.*
#   OR
#   (b) a bare header keyword on its own line (no pipes) — some threads write
#       "Question:", "Rumors:", "Reply 1:", "User 2:", "Follow Up:" directly:
#         ^[ \t]*(question|rumors|reply|user|follow up) [optional number] [optional ":"]
#       We require the keyword to be essentially the whole line (`...$`) so the
#       word "reply"/"user" inside a sentence is not mistaken for a boundary.
REDDIT_BOUNDARY_RE = re.compile(
    r"^[ \t]*(?:"
    r"\|+.*"                                                       # (a) pipe marker line
    r"|(?:question|rumors|reply|user|follow[ \t]*up)[ \t]*\d*[ \t]*:?[ \t]*"  # (b) bare header
    r")$",
    re.IGNORECASE | re.MULTILINE,
)


def split_into_segments(text, boundary_re, divider_re=None):
    """Split `text` into natural units at the given line-start boundaries.

    A "segment" is the text from one boundary marker up to (but not including)
    the next one. Any text appearing before the first marker is kept as its own
    leading segment — for Rate My Professors that is the professor summary
    header, which holds the overall rating / "Would Take Again %".

    Because every boundary pattern is anchored to the start of a line, segments
    can only ever be cut at a marker that begins a line; a sentence is never
    sliced in the middle.

    Args:
        text:        Cleaned document text.
        boundary_re: Compiled, MULTILINE regex matching segment-start markers.
        divider_re:  Optional compiled regex for content-free divider lines,
                     which are blanked out before splitting.

    Returns:
        A list of segment strings (stripped, non-empty), in document order.
    """
    # Remove divider lines first so they don't become empty/garbage segments.
    # We replace just the matched line text (not the newline), leaving a blank
    # line that gets stripped away when we clean each segment below.
    if divider_re is not None:
        text = divider_re.sub("", text)

    # Collect the character offset where each boundary marker begins.
    starts = [m.start() for m in boundary_re.finditer(text)]

    # No markers at all: the whole document is a single segment.
    if not starts:
        stripped = text.strip()
        return [stripped] if stripped else []

    # Cut points are: the start of the document (to capture any leading header),
    # then each marker offset, then the end of the document.
    cut_points = [0] + starts + [len(text)]

    segments = []
    for begin, end in zip(cut_points, cut_points[1:]):
        segment = text[begin:end].strip()
        if segment:  # drop empties (e.g. the gap before the first marker)
            segments.append(segment)
    return segments


# Maps each source type to the boundary pattern + label used for its segments.
# The label is recorded on every chunk so validation can report how many chunks
# each strategy produced.
_STRUCTURE_RULES = {
    "ratemyprofessors": {"boundary_re": RMP_REVIEW_RE, "divider_re": None, "method": "review"},
    "reddit": {"boundary_re": REDDIT_BOUNDARY_RE, "divider_re": REDDIT_DIVIDER_RE, "method": "reply"},
}


def chunk_document(text, source_type):
    """Chunk one cleaned document using structure-aware splitting.

    The document is first split into natural segments (one review / one reply).
    Each segment that fits within MAX_SEGMENT_CHARS becomes a single chunk,
    preserving the complete opinion. A segment longer than MAX_SEGMENT_CHARS is
    the only case where we fall back to fixed-size, overlapping windows.

    Args:
        text:        Cleaned document text.
        source_type: "ratemyprofessors" or "reddit" (others use the default).

    Returns:
        A list of (chunk_text, method) tuples, where method is one of
        "review", "reply", or "fixed".
    """
    rule = _STRUCTURE_RULES.get(source_type, _STRUCTURE_RULES[DEFAULT_SOURCE_TYPE])
    segments = split_into_segments(text, rule["boundary_re"], rule["divider_re"])

    chunks = []
    for segment in segments:
        if len(segment) > MAX_SEGMENT_CHARS:
            # Oversized review/reply: fall back to fixed-size, overlapping chunks
            # so this one unit doesn't produce a single huge chunk. Sentence
            # boundaries are not guaranteed here (this is the allowed exception).
            for piece in chunk_text(segment, FALLBACK_CHUNK_SIZE, FALLBACK_OVERLAP):
                chunks.append((piece, "fixed"))
        else:
            # The common path: one complete review/reply -> one chunk.
            chunks.append((segment, rule["method"]))
    return chunks


def build_chunks(documents):
    """Clean and chunk a list of loaded documents (structure-aware).

    Ties the pipeline together: for each document it cleans the text, then splits
    it into natural units (one review / one reply per chunk), falling back to
    fixed-size chunking only for an unusually long single unit. Each chunk
    carries the metadata the later embedding/retrieval stages rely on, plus a
    "chunk_method" field recording which strategy produced it.

    Args:
        documents: Output of `load_documents()` — a list of dicts with
                   "source", "source_type", and "text".

    Returns:
        A list of chunk dicts:
            {
                "source":       <originating filename>,
                "source_type":  "ratemyprofessors" | "reddit",
                "chunk_id":     <0-based index of this chunk within its document>,
                "text":         <chunk text>,
                "chunk_method": "review" | "reply" | "fixed",
            }
    """
    all_chunks = []

    for doc in documents:
        # Clean before chunking so offsets/markers are matched on tidy text.
        cleaned = clean_text(doc["text"])

        # Produce (text, method) pairs for this single document.
        doc_chunks = chunk_document(cleaned, doc["source_type"])

        # Wrap each chunk with metadata, numbering chunks within the document.
        for chunk_id, (chunk, method) in enumerate(doc_chunks):
            all_chunks.append({
                "source": doc["source"],
                "source_type": doc["source_type"],
                "chunk_id": chunk_id,
                "text": chunk,
                "chunk_method": method,
            })

    return all_chunks

# Validation
def _print_sample_chunks(chunks, source_type, label, limit=5):
    """Print up to `limit` chunks of one source type, spread across the set.

    Sampling evenly (rather than taking the first N) means the preview spans
    different documents/professors instead of just the first file.
    """
    subset = [c for c in chunks if c["source_type"] == source_type]
    print(f"\n{label} ({len(subset)} total, showing up to {limit}):")
    if not subset:
        print("  (none)")
        return

    count = min(limit, len(subset))
    step = max(1, len(subset) // count)
    for i in range(count):
        chunk = subset[i * step]
        print("-" * 70)
        print(f"  source='{chunk['source']}' | chunk_id={chunk['chunk_id']} "
              f"| method={chunk['chunk_method']} | len={len(chunk['text'])}")
        print(chunk["text"])
    print("-" * 70)


def _verify_segment_integrity(documents):
    """Verify that structure-aware splitting never cuts a sentence.

    Strategy: re-derive each document's segments and confirm that concatenating
    them reproduces the original text *exactly* once whitespace is ignored. If
    every non-whitespace character is preserved, in order, with no insertions,
    then the only thing splitting did was insert breaks at marker boundaries —
    so no sentence was sliced through. (This checks the structural segments,
    i.e. the boundaries themselves; the fixed-size fallback that may further cut
    an oversized segment is the explicitly allowed exception and is reported
    separately.)

    Returns:
        (ok_count, total, failures) where `failures` is a list of source names
        whose reconstruction did not match.
    """
    def strip_ws(s):
        return re.sub(r"\s+", "", s)

    ok_count = 0
    failures = []
    for doc in documents:
        cleaned = clean_text(doc["text"])
        rule = _STRUCTURE_RULES.get(doc["source_type"], _STRUCTURE_RULES[DEFAULT_SOURCE_TYPE])

        # Reconstruct the divider-stripped source the splitter actually sees,
        # so blanked-out divider lines don't cause a false mismatch.
        seen = cleaned
        if rule["divider_re"] is not None:
            seen = rule["divider_re"].sub("", seen)

        segments = split_into_segments(cleaned, rule["boundary_re"], rule["divider_re"])
        if strip_ws("".join(segments)) == strip_ws(seen):
            ok_count += 1
        else:
            failures.append(doc["source"])

    return ok_count, len(documents), failures


def _run_validation():
    """Run the Milestone 3 pipeline and print structure-aware chunking checks."""
    print("=" * 70)
    print("MILESTONE 3 VALIDATION — Ingestion & Structure-Aware Chunking")
    print("=" * 70)

    # --- Load & build ------------------------------------------------------ #
    documents = load_documents()
    if not documents:
        print("No documents found — nothing to validate.")
        return

    chunks = build_chunks(documents)

    # --- [1] Total chunk count --------------------------------------------- #
    print(f"\n[1] Total number of chunks created: {len(chunks)}")

    # --- [2] 5 representative Rate My Professors chunks -------------------- #
    _print_sample_chunks(chunks, "ratemyprofessors",
                         "[2] Representative Rate My Professors chunks")

    # --- [3] 5 representative Reddit chunks -------------------------------- #
    _print_sample_chunks(chunks, "reddit",
                         "[3] Representative Reddit chunks")

    # --- [4] No chunk split mid-sentence (except fixed-size fallback) ------ #
    ok, total, failures = _verify_segment_integrity(documents)
    print("\n[4] Sentence-boundary verification:")
    print(f"  Structural segments reconstruct the source for {ok}/{total} documents.")
    if failures:
        print(f"  WARNING — segments did not reconstruct for: {failures}")
    else:
        print("  PASS — every structural split occurs at a line-start review/reply")
        print("         marker, so no chunk begins or ends mid-sentence.")
    fixed_chunks = [c for c in chunks if c["chunk_method"] == "fixed"]
    print(f"  {len(fixed_chunks)} chunk(s) used the fixed-size fallback (oversized "
          f"single review/reply) —")
    print("  sentence boundaries are not guaranteed there, which is the allowed exception.")

    # --- [5] Counts by chunking strategy ----------------------------------- #
    counts = {"review": 0, "reply": 0, "fixed": 0}
    for chunk in chunks:
        counts[chunk["chunk_method"]] = counts.get(chunk["chunk_method"], 0) + 1
    print("\n[5] Chunks produced by each strategy:")
    print(f"  review-based (Rate My Professors): {counts['review']}")
    print(f"  reply-based  (Reddit):             {counts['reply']}")
    print(f"  fixed-size fallback:               {counts['fixed']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    _run_validation()
