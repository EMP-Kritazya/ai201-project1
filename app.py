"""Milestone 5 — Query Interface (Gradio web UI).

This is the user-facing front door to the RAG pipeline. It does NOT contain any
retrieval or generation logic itself — that all lives in generation.py. This
file's only job is to take a typed question, hand it to the end-to-end function,
and display the grounded answer plus its source list.

Run it with:

    python app.py

then open http://localhost:7860 in a browser.
"""

import gradio as gr

# answer_with_sources(question) runs the whole pipeline (retrieve -> ground ->
# generate -> attribute) and returns {"answer": str, "sources": [filenames]}.
from generation import answer_with_sources


def handle_query(question):
    """Gradio callback: turn a typed question into (answer_text, sources_text).

    Gradio passes the textbox value in as `question` and routes each returned
    value to its matching output box (answer -> Answer box, sources -> Sources
    box).

    Args:
        question: The raw text the user typed.

    Returns:
        A (answer, sources) tuple of display strings.
    """
    # Guard against an empty/whitespace submission so the demo never calls the
    # model with nothing.
    if not question or not question.strip():
        return "Please type a question first.", ""

    # Run the pipeline. result is {"answer": ..., "sources": [...]}.
    result = answer_with_sources(question)

    # Format the source filenames as a bulleted list. When the system couldn't
    # answer from the reviews, `sources` is empty, so we show "(none)".
    if result["sources"]:
        sources = "\n".join(f"• {s}" for s in result["sources"])
    else:
        sources = "(none)"

    return result["answer"], sources


# --------------------------------------------------------------------------- #
# Layout: a question box, an Ask button, and two read-only output boxes.
# --------------------------------------------------------------------------- #

with gr.Blocks(title="UTA CS Professor Reviews") as demo:
    gr.Markdown(
        "# UTA CS Professor Reviews\n"
        "Ask about University of Texas at Arlington Computer Science professors. "
        "Answers come **only** from retrieved student reviews (Rate My "
        "Professors + Reddit). If the reviews don't cover your question, the "
        "system will say so instead of guessing."
    )

    inp = gr.Textbox(
        label="Your question",
        placeholder="e.g. How does Professor Manfred Huber conduct his lectures?",
        lines=2,
    )
    btn = gr.Button("Ask", variant="primary")

    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)

    # Clicking "Ask" OR pressing Enter in the textbox both trigger the query.
    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

    # A few clickable examples so a viewer immediately understands how to use it.
    gr.Examples(
        examples=[
            "How does Professor Manfred Huber typically conduct his lectures?",
            "Which professor do students commonly recommend for CSE 3318?",
            "How is grading curved in David Kung's CSE 3311 class?",
        ],
        inputs=inp,
    )


if __name__ == "__main__":
    # launch() starts a local web server (default http://localhost:7860).
    demo.launch()
