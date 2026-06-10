# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section _after_ you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

This system covers student reviews, ratings, and experiences with professors at the University of Texas at Arlington. The information is valuable because it helps students make informed decisions about course selection by providing insights into teaching style, workload, grading policies and practices, and exam difficulty. This knowledge is difficult to find through official university's course description or instructors' profile as they don't conver detailed student experiences or opinions.

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| #   | Source                                                                 | Type                     | URL or file path                                                                                         |
| --- | ---------------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------- |
| 1   | Rate My Professor - David Kung                                         | Professor Review         | https://www.ratemyprofessors.com/professor/1226648                                                       |
| 2   | Rate My Professor - Ishfaq Ahmad                                       | Professor Review         | https://www.ratemyprofessors.com/professor/1444520                                                       |
| 3   | Rate My Professor - Jimmie Davis                                       | Professor Review         | https://www.ratemyprofessors.com/professor/2218914                                                       |
| 4   | Rate My Professor - Linda Barasch                                      | Professor Review         | https://www.ratemyprofessors.com/professor/619690                                                        |
| 5   | Rate My Professor - Manfred Huber                                      | Professor Review         | https://www.ratemyprofessors.com/professor/529522                                                        |
| 6   | Rate My Professor - Donna French                                       | Professor Review         | https://www.ratemyprofessors.com/professor/2346663                                                       |
| 7   | Rate My Professor - Bob Weems                                          | Professor Review         | https://www.ratemyprofessors.com/professor/432105                                                        |
| 8   | Rate My Professor - Bahram Khalili                                     | Professor Review         | https://www.ratemyprofessors.com/professor/1055888                                                       |
| 9   | Rate My Professor - John Robb                                          | Professor Review         | https://www.ratemyprofessors.com/professor/1998025                                                       |
| 10  | Rate My Professor - Changekai Li                                       | Professor Review         | https://www.ratemyprofessors.com/professor/1151666                                                       |
| 11  | Rate My Professor - Marika Apostolova                                  | Professor Review         | https://www.ratemyprofessors.com/professor/2925654                                                       |
| 12  | Rate My Professor - Bhanu Jain                                         | Professor Review         | https://www.ratemyprofessors.com/professor/2473801                                                       |
| 13  | Rate My Professor - Vamsikrishna Gopikrishna                           | Professor Review         | https://www.ratemyprofessors.com/professor/2272923                                                       |
| 14  | Rate My Professor - Nadra Guizani                                      | Professor Review         | https://www.ratemyprofessors.com/professor/2635253                                                       |
| 15  | Rate My Professor - Abhishek Santra                                    | Professor Review         | https://www.ratemyprofessors.com/professor/2774504                                                       |
| 16  | Reddit - Help in choosing classes based on professors need preferences | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1ps7xnd/help_in_choosing_classes_based_on_professors_need/ |
| 17  | Reddit - Review of CSE 3311 CSE 3302 CSE 4322                          | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1kquhqp/review_of_cse_3311_cse_3302_cse_4322/              |
| 18  | Reddit - CSE 4308                                                      | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1s8te40/cse_4308/                                          |
| 19  | Reddit - CSE 3330                                                      | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1omzpnr/cse_3330/                                          |
| 20  | Reddit - Cse 3315 theoretical                                          | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1olduor/cse_3315_theoretical/                              |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** The project initially used fixed-size chunking because the corpus consisted primarily of short reviews and discussion posts. However, after testing retrieval quality, I found that fixed-size chunks sometimes split important ideas across chunk boundaries. As a result, I switched to variable-length, structure-aware chunking. Each Rate My Professors review is treated as a single chunk, and each Reddit reply or comment is treated as a single chunk. Since these units naturally represent complete thoughts and opinions, they provide richer semantic context during retrieval.

**Overlap:** With variable length chunking, overlap size is none. Because each chunk corresponds to an entire review or Reddit reply, the chunks are generally understandable on their own without requiring neighboring context. This also reduces redundancy in the vector database and avoids repeatedly embedding the same information.

**Why these choices fit your documents:** My documents consist of purely Rate My Professor reviews and Reddit discussions about UTA professors. Before chunking, the documents were manually cleaned and converted into plain text. Reddit discussions were structured using clear boundaries (e.g., question, Reply 1, Reply 2), and Rate My Professors reviews were separated into individual entries to facilitate structure-aware chunking.

Preserving these natural boundaries allowed each chunk to retain its complete semantic meaning, resulting in more accurate retrieval. During evaluation, this approach consistently produced more relevant results than the original fixed-size chunking strategy.

**Final chunk count:** Total Size: 103; 90: Rate My Professors, and 13: Reddit Discussion Forums

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** all-MiniLM-L6-v2 from sentence-transformers

**Production tradeoff reflection:** If cost wasn't a constraint when deploying for real users, I would consider using a more powerful embedding model with higher overall retrieval accuracy. The tradeoff I would evaluate include retrieval quality, latency, API-hosted (easily supportable for wide internet users), and accuracy on domain-specific text which implies better retrieval quality.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
Grounding is not just merely requested, rather it is enforced. The system prompt gives the model four hard rules such as:

1. Answer ONLY using the information in the provided context below.
2. Do NOT use any outside knowledge or anything you learned during
   training.
3. Do NOT infer, assume, or add any fact that is not directly stated in
   the context.
4. If the context does not contain enough information to answer the
   question, reply with EXACTLY this sentence and nothing else.

These hard rule prevent the LLM from answering beyond the retrieved documents.

- Regarding structural choices, I've implemented following:

* Context formatting, i.e., the retrieved chunks are assembled into a single numbered block, each labelled with its source file. For instance, (source: rmp_manfred_huber.txt)\n<chunk text>, placed under a (Context:) header above the Question:. This makes sure that user can verify where the answer is retrieved from, thus further enforcing grounding.
* Retrieval short-circuit: If we find zero related chunks, the code returns the refusal sentence without ever calling the LLM.

  **How source attribution is surfaced in the response:**
  -> To sufrace the source attribution, the extract_sources() reads the source filename from each retrieved chunk and builds a list. Later in the final response, this gets appended under a Sources: heading, and the Gradio UI shows it in a seperate "Retrieved from" box.
  For instance:
  Sources:
  - rmp_chengkai_li.txt
  - reddit_choosing_classes.txt

  The list is contructed from the retrieved chunk metadata, hence it only ever contain documents that genuinely came out of the vector store, not something LLM itself makes up.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| #   | Question                                                                       | Expected answer                                                                                                          | System response (summarized)                                                       | Retrieval quality  | Response accuracy  |
| --- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | ------------------ | ------------------ |
| 1   | How does Professor Manfred Huber typically conduct his lectures?               | He uses little to no slides and primarily teaches by working through mathematical derivations on the whiteboard.         | Lectures are recorded; he uses a whiteboard for "pure mathematics" with no slides. | Relevant           | Accurate           |
| 2   | Which professor do students commonly recommend for CSE 3318?                   | Students commonly recommend Professor Donna French or Professor Stefan for CSE 3318.                                     | Dr. Stefan is recommended for CSE 3318.                                            | Relevant           | Partially accurate |
| 3   | When do students suggest taking CSE 3318 with Donna French?                    | Students recommend taking CSE 3318 during the summer if the course is available.                                         | "I don't have enough information on that." (refused)                               | Off-target         | Inaccurate         |
| 4   | How is grading curved in David Kung's CSE 3311 class?                          | The grading scale is automatically curved, with approximately a 60 corresponding to a C and an 85 corresponding to an A. | Auto-curved: a 60 is a C and an 85 is an A.                                        | Relevant           | Accurate           |
| 5   | What percentage of students say they would take Abhishek Santra's class again? | Approximately 88.9% of students said they would take his class again.                                                    | "I don't have enough information on that." (refused)                               | Partially relevant | Inaccurate         |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

1. What percentage of students say they would take Abhishek Santra's class again?
   -> Approximately 88.9% of students said they would take his class again.

**What the system returned:**
-> Generated Answer: "I don't have enough information on that."

**Root cause (tied to a specific pipeline stage):**
-> The root cause is limitation of relevant information in ingestion stage. As thought of as anticipated challenge in the planning stage, due to not enough context, the LLM was unable to provide us with the correct answer.

**What you would change to fix it:**
-> I would explicitly extract structured statistics from Rate My Professors pages and refine retrieval settings to improve the chances of returning those facts when relevant. Also, including more information from various sources would allow me to fix the problem.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
-> Spending time on planning.md kept me on the right track throughout the project. Since I had already thought through the architecture and end goals, it became much easier to work with AI tools, debug issues, and make decisions about tradeoffs and improvements because I understood what I was trying to achieve.

**One way your implementation diverged from the spec, and why:**
-> I initially planned to use fixed-size chunking, but testing showed that it sometimes split complete ideas across chunks. Since my Reddit data was already organized into questions and replies, and Rate My Professors reviews were separated individually, I treated each reply or review as its own chunk. This preserved the full meaning of each opinion and improved retrieval quality.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- _What I gave the AI:_ My Grounded Generation requirements from planning.md, the output format of my retrieval function, and the Groq model I wanted to use. I asked Claude to build the generation step.
- _What it produced:_ A generation.py with the strict system prompt, a prompt template that combines the context and question, the Groq call, and a function that builds the source list directly from the retrieved chunks.
- _What I changed or overrode:_ I rewrote a couple of the prompt comments in my own words so I understood them, and I decided to keep the Gradio interface in a separate app.py instead of bundling it into generation.py so the logic and the UI stay separate.

**Instance 2**

- _What I gave the AI:_ My ChromaDB error and the full traceback when retrieval.py crashed, and asked what was going wrong.
- _What it produced:_ It traced the crash to a bug in the older chromadb version's SQLite handling and upgraded the package to fix it, leaving my retrieval code unchanged.
- _What I changed or overrode:_ I had it bump the minimum chromadb version in requirements.txt so a fresh install wouldn't pull the broken version again, rather than just fixing it on my machine.
