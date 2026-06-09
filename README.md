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
| 1   | Rate My Professor - Sajib Datta                                        | Professor Review         | https://www.ratemyprofessors.com/professor/1892339                                                       |
| 2   | Rate My Professor - David Levine                                       | Professor Review         | https://www.ratemyprofessors.com/professor/1055887                                                       |
| 3   | Rate My Professor - David Kung                                         | Professor Review         | https://www.ratemyprofessors.com/professor/1226648                                                       |
| 4   | Rate My Professor - Ishfaq Ahmad                                       | Professor Review         | https://www.ratemyprofessors.com/professor/1444520                                                       |
| 5   | Rate My Professor - Jimmie Davis                                       | Professor Review         | https://www.ratemyprofessors.com/professor/2218914                                                       |
| 6   | Rate My Professor - Linda Barasch                                      | Professor Review         | https://www.ratemyprofessors.com/professor/619690                                                        |
| 7   | Rate My Professor - Carter Tiernan                                     | Professor Review         | https://www.ratemyprofessors.com/professor/529523                                                        |
| 8   | Rate My Professor - Manfred Huber                                      | Professor Review         | https://www.ratemyprofessors.com/professor/529522                                                        |
| 9   | Rate My Professor - Donna French                                       | Professor Review         | https://www.ratemyprofessors.com/professor/2346663                                                       |
| 10  | Rate My Professor - Bob Weems                                          | Professor Review         | https://www.ratemyprofessors.com/professor/432105                                                        |
| 11  | Rate My Professor - Bahram Khalili                                     | Professor Review         | https://www.ratemyprofessors.com/professor/1055888                                                       |
| 12  | Rate My Professor - John Robb                                          | Professor Review         | https://www.ratemyprofessors.com/professor/1998025                                                       |
| 13  | Rate My Professor - Chance Eary                                        | Professor Review         | https://www.ratemyprofessors.com/professor/2152345                                                       |
| 14  | Rate My Professor - Brian Dalio                                        | Professor Review         | https://www.ratemyprofessors.com/professor/2364252                                                       |
| 15  | Rate My Professor - Ramez Elmasri                                      | Professor Review         | https://www.ratemyprofessors.com/professor/1024272                                                       |
| 16  | Rate My Professor - Fadiah Qudah                                       | Professor Review         | https://www.ratemyprofessors.com/professor/2260245                                                       |
| 17  | Rate My Professor - Mostafa Ghandehari                                 | Professor Review         | https://www.ratemyprofessors.com/professor/849267                                                        |
| 18  | Rate My Professor - Changekai Li                                       | Professor Review         | https://www.ratemyprofessors.com/professor/1151666                                                       |
| 19  | Rate My Professor - Ali Sharifara                                      | Professor Review         | https://www.ratemyprofessors.com/professor/2294905                                                       |
| 20  | Rate My Professor - Henry Kearny                                       | Professor Review         | https://www.ratemyprofessors.com/professor/56918                                                         |
| 21  | Rate My Professor - Raymond Springston                                 | Professor Review         | https://www.ratemyprofessors.com/professor/430610                                                        |
| 22  | Rate My Professor - Marika Apostolova                                  | Professor Review         | https://www.ratemyprofessors.com/professor/2925654                                                       |
| 23  | Rate My Professor - Bhanu Jain                                         | Professor Review         | https://www.ratemyprofessors.com/professor/2473801                                                       |
| 24  | Rate My Professor - Jiandong Wang                                      | Professor Review         | https://www.ratemyprofessors.com/professor/3067391                                                       |
| 24  | Rate My Professor - Dianqi Han                                         | Professor Review         | https://www.ratemyprofessors.com/professor/2892962                                                       |
| 25  | Rate My Professor - Vamsikrishna Gopikrishna                           | Professor Review         | https://www.ratemyprofessors.com/professor/2272923                                                       |
| 26  | Rate My Professor - Nadra Guizani                                      | Professor Review         | https://www.ratemyprofessors.com/professor/2635253                                                       |
| 27  | Rate My Professor - Abhishek Santra                                    | Professor Review         | https://www.ratemyprofessors.com/professor/2774504                                                       |
| 28  | Reddit - Help in choosing classes based on professors need preferences | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1ps7xnd/help_in_choosing_classes_based_on_professors_need/ |
| 29  | Reddit - Review of CSE 3311 CSE 3302 CSE 4322                          | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1kquhqp/review_of_cse_3311_cse_3302_cse_4322/              |
| 30  | Reddit - CSE 4308                                                      | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1s8te40/cse_4308/                                          |
| 31  | Reddit - CSE 3330                                                      | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1omzpnr/cse_3330/                                          |
| 32  | Reddit - Cse 3315 theoretical                                          | Reddit Discussion Thread | https://www.reddit.com/r/utarlington/comments/1olduor/cse_3315_theoretical/                              |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**

**Overlap:**

**Why these choices fit your documents:**

**Final chunk count:**

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**

**Production tradeoff reflection:**

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| #   | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
| --- | -------- | --------------- | ---------------------------- | ----------------- | ----------------- |
| 1   |          |                 |                              |                   |                   |
| 2   |          |                 |                              |                   |                   |
| 3   |          |                 |                              |                   |                   |
| 4   |          |                 |                              |                   |                   |
| 5   |          |                 |                              |                   |                   |

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

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

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

- _What I gave the AI:_
- _What it produced:_
- _What I changed or overrode:_

**Instance 2**

- _What I gave the AI:_
- _What it produced:_
- _What I changed or overrode:_
