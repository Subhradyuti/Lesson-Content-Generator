"""
Test fixtures for deterministic workflow testing.
All model responses are mocked — no live API calls in the standard test suite.
"""

from __future__ import annotations

from typing import Any

# ── Passing lesson fixture ─────────────────────────────────────────────────────

PASSING_LESSON = """
# Introduction to RAG (Retrieval-Augmented Generation)

## What You Will Learn
- What RAG means
- Why RAG is useful for language models
- How RAG works step by step
- A concrete example of RAG in action
- Key limitations of RAG

## What RAG Means
RAG stands for Retrieval-Augmented Generation. Let us break this down:
- **Retrieval** means searching for and finding relevant information.
- **Generation** means creating text, like an answer to a question.
- **Augmented** means "made better with extra help."

So RAG is a way to make a language model's answers better by first finding relevant information, then using that information to generate the answer.

## Why RAG Matters
A language model (also called an LLM, or Large Language Model — a computer program trained to understand and produce text) learns from text written before a certain date. After that date, it does not know about new events.

For example, if you ask an LLM "What happened in the news today?", it cannot answer correctly because it does not have today's news.

RAG solves this problem. It lets the model search a collection of documents before answering, so it can use up-to-date or specific information.

## How RAG Works — Step by Step

**Step 1: Prepare your documents.**
You collect the documents you want the system to search. For example, a company's internal manuals or recent news articles.

**Step 2: Split documents into chunks.**
Each document is divided into smaller pieces called *chunks* (small portions of text). This makes searching faster and more accurate.

**Step 3: Create embeddings.**
Each chunk is converted into a list of numbers called an *embedding* (a mathematical representation that captures the meaning of the text). Similar pieces of text have similar embeddings.

**Step 4: Store in a vector database.**
The embeddings are stored in a special database called a *vector database* (a database that stores and searches by mathematical meaning, not just keywords).

**Step 5: User asks a question.**
When you ask a question, the system converts your question into an embedding too.

**Step 6: Retrieve relevant chunks.**
The system searches the vector database for chunks whose embeddings are most similar to your question's embedding. These are the most relevant pieces of information.

**Step 7: Generate the answer.**
The relevant chunks are given to the language model as *context* (background information). The model uses this context to write an accurate, relevant answer.

## Worked Example
Imagine you have a question: "What is the company's refund policy?"

1. You have uploaded 50 company documents to the RAG system.
2. The system splits them into chunks (e.g., "Policy documents," "Refund section: Customers may return items within 30 days...").
3. Your question "What is the company's refund policy?" is converted to an embedding.
4. The vector database finds the chunk about refunds — it has a very similar embedding to your question.
5. That chunk is given to the language model as context.
6. The model generates: "According to the company policy, customers may return items within 30 days of purchase for a full refund."

Without RAG, the model might guess or say "I don't know." With RAG, it finds the right document and gives a specific answer.

## Key Terms Explained
- **LLM (Large Language Model):** A computer program trained on large amounts of text to understand and generate human language.
- **Embedding:** A list of numbers that represents the meaning of a piece of text. Similar texts have similar embeddings.
- **Chunk:** A small portion of a larger document, created to make searching more efficient.
- **Vector database:** A special database that stores embeddings and can quickly find the most similar ones.
- **Context:** The background information given to the language model along with the question.
- **Retrieval:** The process of searching for and finding relevant documents or chunks.
- **Generation:** The process of producing text as an answer.
- **Hallucination:** When a language model generates incorrect or invented information confidently. RAG reduces but does not eliminate this.

## Common Misunderstandings

**Misunderstanding 1: RAG guarantees correct answers.**
This is not true. RAG retrieves relevant documents, but the language model may still make mistakes when generating the answer. The retrieved document may also be outdated or incorrect.

**Misunderstanding 2: RAG retrieval always finds the right information.**
Not always. If your question uses different words than the document, the retrieval step may miss the best chunk. RAG searches by meaning, which is better than keyword search, but it is not perfect.

**Misunderstanding 3: RAG replaces the need for a language model.**
No. RAG still uses a language model to generate the final answer. Retrieval only provides the information; the model writes the response.

## Short Recap
- RAG combines document retrieval with language model generation.
- It solves the problem of LLMs not having up-to-date or specific knowledge.
- The process: prepare documents → chunk → embed → store → retrieve → generate.
- RAG improves answers but does not guarantee accuracy.
- Technical terms like embedding, chunk, and vector database are all part of the RAG workflow.

## Check Your Understanding

**Question 1:** What does RAG stand for?
**Question 2:** Why does a language model sometimes not know the answer to a current question?
**Question 3:** What is an embedding?
**Question 4:** What does the retrieval step do in RAG?
**Question 5:** Does RAG guarantee that the generated answer will always be correct? Why or why not?

### Answer Key
1. RAG stands for Retrieval-Augmented Generation.
2. A language model is trained on data up to a certain date, so it does not know about events or documents created after that date.
3. An embedding is a list of numbers that represents the meaning of a piece of text, allowing the system to find similar texts by comparing these numbers.
4. The retrieval step searches the vector database to find the document chunks most similar to the user's question, providing relevant information for the answer.
5. No. RAG does not guarantee correct answers. The retrieved document may be incorrect or irrelevant, and the language model may still make mistakes when generating the answer.
"""

# ── Failing lesson fixture ─────────────────────────────────────────────────────

FAILING_LESSON = """
# RAG Overview

RAG uses embeddings and vectors to retrieve chunks and augment generation.

The process involves LLMs, vector databases, and retrieval mechanisms.
Embeddings are created and stored. Retrieval finds relevant data. Generation produces output.

Questions:
1. What is RAG?
Answer: It is a retrieval system.
"""

# ── Passing evaluation fixture ─────────────────────────────────────────────────


def make_passing_evaluation(rubric_version: str = "rag-beginner-v1") -> dict[str, Any]:
    """Return a passing evaluation with all 14 checkpoints as PASS."""
    checks = []
    checkpoint_ids = [
        "ACC-01",
        "ACC-02",
        "BEG-01",
        "JAR-01",
        "EX-01",
        "COV-01",
        "COV-02",
        "COV-03",
        "COV-04",
        "FLOW-01",
        "FLOW-02",
        "CHECK-01",
        "CONS-01",
        "SAFE-01",
    ]
    for cid in checkpoint_ids:
        checks.append(
            {
                "id": cid,
                "status": "PASS",
                "evidence": "Lesson clearly covers this requirement.",
                "reason": f"Checkpoint {cid} is satisfied by the lesson content.",
                "required_fix": None,
            }
        )
    return {
        "rubric_version": rubric_version,
        "overall_pass": True,
        "checks": checks,
    }


# ── Failing evaluation fixture ─────────────────────────────────────────────────


def make_failing_evaluation(
    failed_ids: list[str] | None = None,
    rubric_version: str = "rag-beginner-v1",
) -> dict[str, Any]:
    """Return an evaluation with the specified checkpoints as FAIL."""
    if failed_ids is None:
        failed_ids = ["JAR-01", "BEG-01"]

    all_ids = [
        "ACC-01",
        "ACC-02",
        "BEG-01",
        "JAR-01",
        "EX-01",
        "COV-01",
        "COV-02",
        "COV-03",
        "COV-04",
        "FLOW-01",
        "FLOW-02",
        "CHECK-01",
        "CONS-01",
        "SAFE-01",
    ]

    checks = []
    for cid in all_ids:
        if cid in failed_ids:
            checks.append(
                {
                    "id": cid,
                    "status": "FAIL",
                    "evidence": f"The lesson does not adequately address {cid}.",
                    "reason": f"Checkpoint {cid} condition is not met.",
                    "required_fix": f"Please fix the issue with checkpoint {cid}.",
                }
            )
        else:
            checks.append(
                {
                    "id": cid,
                    "status": "PASS",
                    "evidence": "Lesson clearly covers this requirement.",
                    "reason": f"Checkpoint {cid} is satisfied.",
                    "required_fix": None,
                }
            )

    return {
        "rubric_version": rubric_version,
        "overall_pass": False,
        "checks": checks,
    }


# ── Malformed evaluation fixture ───────────────────────────────────────────────

MALFORMED_EVALUATION_JSON = '{"rubric_version": "rag-beginner-v1", "checks": "not_a_list"}'

EVALUATION_MISSING_CHECKPOINT = {
    "rubric_version": "rag-beginner-v1",
    "overall_pass": True,
    "checks": [
        {
            "id": "ACC-01",
            "status": "PASS",
            "evidence": "Some evidence.",
            "reason": "Passes.",
            "required_fix": None,
        }
        # Missing 13 checkpoints
    ],
}

EVALUATION_DUPLICATE_CHECKPOINT = {
    "rubric_version": "rag-beginner-v1",
    "overall_pass": True,
    "checks": [
        {"id": "ACC-01", "status": "PASS", "evidence": "e1", "reason": "r1", "required_fix": None},
        {"id": "ACC-01", "status": "PASS", "evidence": "e2", "reason": "r2", "required_fix": None},
    ],
}


# ── Lesson plan fixture ────────────────────────────────────────────────────────

PASSING_LESSON_PLAN = {
    "learning_objectives": [
        "Explain what RAG means in simple terms",
        "Describe the basic RAG workflow",
        "Give one practical example of RAG",
    ],
    "prerequisites": [],
    "key_concepts": ["retrieval", "generation", "embedding", "vector database", "context"],
    "teaching_order": [
        "Define RAG and its components",
        "Explain why LLMs need external information",
        "Walk through the RAG workflow step by step",
        "Show a concrete worked example",
        "Discuss limitations",
    ],
    "worked_example": "A customer asks 'What is your refund policy?' The RAG system retrieves the relevant policy chunk and the LLM generates a specific answer.",
    "misconceptions": [
        "RAG guarantees correct answers",
        "RAG replaces the language model",
    ],
}
