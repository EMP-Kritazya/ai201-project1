import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# We reuse Milestone 4's retrieval function unchanged. retrieve(query, k)
# returns a list of dicts: {"text", "source", "chunk_id", "distance"}.
from retrieval import retrieve, DEFAULT_TOP_K

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Groq's recommended model for this project (per the milestone instructions).
GROQ_MODEL = "llama-3.3-70b-versatile"

# temperature=0 makes the model as deterministic as possible. For a grounded
# Q&A system we do NOT want creative variation — we want it to stick to the
# facts in the context, so we turn the "randomness" all the way down.
GROQ_TEMPERATURE = 0.0

# The EXACT sentence the model must return when the context is insufficient.
# We keep it in one constant so the prompt, the short-circuit, and the
# grounding check all agree on the same wording.
REFUSAL_MESSAGE = "I don't have enough information on that."

# Path to the .env file that holds GROQ_API_KEY (lives next to this script).
ENV_PATH = Path(__file__).parent / ".env"

# Module-level singleton so we build the Groq client only once per run.
_client = None


# Prompt Construction for our Agent. This is almost as the heart of grounding our LLM

# This is the what we feed our model to act as. We define its role and what it shall keep in mind when answering
SYSTEM_PROMPT = (
    "You are a careful assistant that answers questions about University of "
    "Texas at Arlington Computer Science professors.\n"
    "\n"
    "You must obey these rules at all times:\n"
    "1. Answer ONLY using the information in the provided context below.\n"
    "2. Do NOT use any outside knowledge or anything you learned during "
    "training.\n"
    "3. Do NOT infer, assume, or add any fact that is not directly stated in "
    "the context.\n"
    "4. If the context does not contain enough information to answer the "
    "question, reply with EXACTLY this sentence and nothing else:\n"
    f"{REFUSAL_MESSAGE}\n"
)


def format_context(hits):
    """Combine retrieved chunks into one clearly labelled context block.

    Each chunk becomes a numbered section that also names its source file. The
    source label is included so the model can see which document a fact came
    from, but note: the *authoritative* source list shown to the user is built
    separately in `extract_sources()` and never relies on the model.

    Args:
        hits: The list of dicts returned by retrieve().

    Returns:
        A single string holding all chunks, ready to drop into the prompt.
    """
    blocks = []
    for i, hit in enumerate(hits, start=1):
        # e.g. "[1] (source: rmp_manfred_huber.txt)\n<chunk text>"
        blocks.append(f"[{i}] (source: {hit['source']})\n{hit['text']}")
    # A blank line between chunks keeps the context readable for the model.
    return "\n\n".join(blocks)


def build_user_prompt(question, hits):
    """Build the user-turn prompt: the context, then the question.

    Args:
        question: The user's natural-language question.
        hits:     Retrieved chunks from retrieve().

    Returns:
        The user message string.
    """
    context = format_context(hits)
    return (
        "Context:\n"
        f"{context}\n"
        "\n"
        f"Question: {question}\n"
        "\n"
        "Answer the question using ONLY the context above. If the context does "
        f"not contain the answer, reply exactly: {REFUSAL_MESSAGE}"
    )

def extract_sources(hits):
    """Return the unique source filenames from the retrieved chunks, in order.

    This is the programmatic guarantee: the source list is derived ONLY from the
    retrieved chunks' metadata, so it can never contain a document the retriever
    didn't actually return. Duplicates are removed while preserving the order in
    which sources first appear (most-similar chunk first).

    Args:
        hits: Retrieved chunks from retrieve().

    Returns:
        A list of unique source filename strings.
    """
    seen = set()
    sources = []
    for hit in hits:
        source = hit.get("source")
        if source and source not in seen:
            seen.add(source)
            sources.append(source)
    return sources


def get_groq_client():
    """Return a cached Groq client, loading GROQ_API_KEY from .env on first use.

    load_dotenv() reads the .env file and puts its values into the process
    environment, so os.environ can see GROQ_API_KEY. We build the client once
    and reuse it for every request.

    Raises:
        RuntimeError: if GROQ_API_KEY is missing, with a clear hint.
    """
    global _client
    if _client is None:
        # Read .env (next to this file) into the environment.
        load_dotenv(ENV_PATH)

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not found. Copy .env.example to .env and put your "
                "Groq API key there (get one free at https://console.groq.com)."
            )

        # Groq(api_key=...) creates the API client object. All chat requests go
        # through this client.
        _client = Groq(api_key=api_key)
    return _client


def generate_answer(question, hits):
    client = get_groq_client()

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=GROQ_TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, hits)},
        ],
    )

    # The generated text lives on the first choice's message content.
    return response.choices[0].message.content.strip()


def _is_refusal(answer):
    normalized = answer.strip().rstrip(".").lower()
    return normalized == REFUSAL_MESSAGE.rstrip(".").lower()

def format_response(answer, sources):
    parts = [f"Answer:\n{answer}"]
    if sources:
        source_lines = "\n".join(f"- {s}" for s in sources)
        parts.append(f"Sources:\n{source_lines}")
    return "\n\n".join(parts)

# Retrieves the k most relevant chunks, builds the ground prompt and calls Groq.
def answer_question(question, k=DEFAULT_TOP_K):
    answer, sources = _answer_and_sources(question, k)
    return format_response(answer, sources)


def _answer_and_sources(question, k=DEFAULT_TOP_K):
    """Core logic shared by the CLI/validation and the Gradio interface.

    Returns:
        A (answer_text, sources_list) tuple. `sources_list` is empty whenever
        the system could not answer from the retrieved context.
    """
    # 1. Retrieve relevant chunks.
    hits = retrieve(question, k=k)

    # 2. Nothing retrieved -> refuse without calling the model.
    if not hits:
        return REFUSAL_MESSAGE, []

    # 3. Generate the grounded answer.
    answer = generate_answer(question, hits)

    # 4. If the model refused, don't attach sources to a "no info" answer.
    if _is_refusal(answer):
        return REFUSAL_MESSAGE, []

    # 5. Build the authoritative source list from the retrieved chunks.
    return answer, extract_sources(hits)


def answer_with_sources(question, k=DEFAULT_TOP_K):
    """Public entry point for the interface (app.py).

    Returns the answer and its programmatic source list as a dict, which is a
    convenient shape for a UI that shows the two separately:

        {"answer": "<text>", "sources": ["rmp_x.txt", "reddit_y.txt", ...]}

    `sources` is an empty list whenever the system could not answer from the
    retrieved context (so the UI can render "(none)").

    Args:
        question: The user's natural-language question.
        k:        How many chunks to retrieve (default = planning.md top-k = 5).
    """
    answer, sources = _answer_and_sources(question, k)
    return {"answer": answer, "sources": sources}



def _grounding_overlap(answer, hits):
    """Heuristic: fraction of the answer's content words that appear in context.

    This is NOT a proof of grounding (only a human can judge that fully), but it
    is a useful signal: if the answer uses many words that never appear in the
    retrieved chunks, that's a red flag the model pulled in outside knowledge.

    Returns:
        A float in [0.0, 1.0]; higher means more of the answer's words are
        actually present in the retrieved context.
    """
    import re

    # Very small stopword list so common words don't inflate the overlap.
    stopwords = {
        "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for",
        "is", "are", "was", "were", "be", "with", "as", "at", "by", "it",
        "this", "that", "his", "her", "their", "they", "he", "she", "you",
        "would", "do", "does", "have", "has", "i", "not", "no", "if",
    }

    def content_words(text):
        words = re.findall(r"[a-z0-9]+", text.lower())
        return [w for w in words if w not in stopwords and len(w) > 2]

    context_words = set()
    for hit in hits:
        context_words.update(content_words(hit["text"]))

    answer_words = content_words(answer)
    if not answer_words:
        return 1.0  # nothing to ground (e.g. empty answer)

    present = sum(1 for w in answer_words if w in context_words)
    return present / len(answer_words)


def _run_validation():
    """Run several queries end-to-end and report retrieved sources + grounding.

    For each query we print:
        * the sources retrieved,
        * the generated answer,
        * a grounding verdict that answers the evaluation question:
          "Could this response have come from anywhere other than the
           retrieved chunks?"
    """
    print("=" * 78)
    print("MILESTONE 5 VALIDATION — Generation & Grounded Answers")
    print("=" * 78)

    # The 5 evaluation questions from planning.md, plus one deliberately
    # OUT-OF-DOMAIN question to prove the grounding refusal works (the system
    # must NOT answer it from outside knowledge).
    test_queries = [
        "How does Professor Manfred Huber typically conduct his lectures?",
        "Which professor do students commonly recommend for CSE 3318?",
        "When do students suggest taking CSE 3318 with Donna French?",
        "How is grading curved in David Kung's CSE 3311 class?",
        "What percentage of students say they would take Abhishek Santra's class again?",
        "What is the capital of France?",  # This question is out-of-domain so the model must refuse on answering it.
    ]

    # Threshold below which we warn that the answer may not be grounded.
    GROUNDING_WARN_BELOW = 0.5

    for q_num, query in enumerate(test_queries, start=1):
        print("\n" + "=" * 78)
        print(f"Query {q_num}: {query}")
        print("=" * 78)

        # Retrieve first so we can show the sources and run the grounding check.
        hits = retrieve(query, k=DEFAULT_TOP_K)

        # --- Retrieved sources --------------------------------------------- #
        sources = extract_sources(hits)
        print("\nRetrieved sources:")
        if sources:
            for s in sources:
                print(f"  - {s}")
        else:
            print("  (none — collection empty or no matches)")

        # --- Generated answer ---------------------------------------------- #
        answer, final_sources = _answer_and_sources(query)
        print("\nGenerated answer:")
        print(f"  {answer}")

        # --- Grounding verdict --------------------------------------------- #
        print("\nGrounding check — 'Could this have come from outside the chunks?'")
        if _is_refusal(answer):
            # Refusing is the correct, fully-grounded behaviour when the context
            # doesn't support an answer.
            print("  VERDICT: Grounded. The system refused instead of using "
                  "outside knowledge.")
        else:
            overlap = _grounding_overlap(answer, hits)
            print(f"  Word overlap with retrieved context: {overlap:.0%}")
            if overlap >= GROUNDING_WARN_BELOW:
                print("  VERDICT: Appears grounded — the answer's wording is well "
                      "supported by the retrieved chunks.")
            else:
                print("  VERDICT: POSSIBLE GROUNDING FAILURE — much of the answer's "
                      "wording is absent from the retrieved chunks, so it may "
                      "draw on outside knowledge. Inspect manually.")

    print("\n" + "=" * 78)
    print("Validation complete.")
    print("=" * 78)


if __name__ == "__main__":
    # Running this module directly runs the end-to-end validation.
    # The web interface lives in app.py — run `python app.py` for that.
    _run_validation()
