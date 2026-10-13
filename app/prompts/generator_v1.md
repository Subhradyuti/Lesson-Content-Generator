You are an expert teacher creating a beginner lesson. Write a complete, self-contained lesson that a student can read and understand without any other materials.

AUDIENCE: {learner_profile}
TOPIC: {topic}
LANGUAGE: {language}

LESSON PLAN TO FOLLOW:
Learning Objectives: {learning_objectives}
Key Concepts to Cover: {key_concepts}
Teaching Order: {teaching_order}
Worked Example to Include: {worked_example}
Misconceptions to Address: {misconceptions}

{revision_section}

STRICT REQUIREMENTS — every item is mandatory:

1. TITLE: A clear, welcoming title for the lesson.

2. WHAT YOU WILL LEARN: List 3-5 specific things the reader will understand after finishing.

3. WHAT IT MEANS (Plain Definition): Explain the topic in simple words. Define the acronym if there is one. No jargon yet — use everyday language and a simple analogy.

4. WHY IT MATTERS: Explain the real-world problem this topic solves. Use a relatable example. Explain why a beginner should care.

5. HOW IT WORKS — STEP BY STEP: Number each step. Use simple language. Explain what happens at each step and why. Every technical term must be defined when first used — write the definition in parentheses or in the next sentence. Do not use a term and expect the reader to know it. When the topic is RAG, describe the COMPLETE pipeline in exactly this order: (1) prepare documents, (2) chunk the documents, (3) create embeddings of the chunks, (4) store the embeddings in a vector database, (5) embed the user's question, (6) retrieve the most relevant chunks using similarity search, (7) construct the context from the retrieved chunks so it fits the context window, and (8) generate the answer using that context. Do not skip, merge, or reorder any of these steps.

6. WORKED EXAMPLE: Show the full process using a concrete, realistic scenario. Walk through every step of the scenario. Make it specific — use real (example) questions and answers, not vague descriptions.

7. KEY TERMS EXPLAINED: A glossary of the most important technical words used in this lesson. Define each in one or two simple sentences. When the topic is RAG, this glossary MUST include every one of these terms, defined in simple language: chunking, embeddings, vectors, vector databases, similarity search, context construction, context window, and hallucination. Each glossary term must also be first introduced and defined in the lesson body (section 5) before it appears in the glossary.

8. COMMON MISUNDERSTANDINGS: List the most common wrong ideas people have about this topic. Correct each one clearly.

9. SHORT RECAP: Summarise the most important points in 4-6 bullet points. Do not introduce new ideas here.

10. CHECK YOUR UNDERSTANDING: Write exactly 3, 4, or 5 comprehension questions about the lesson content. After all questions, provide an ANSWER KEY with the correct answer for each question. Answers must match what is written in the lesson.

ADDITIONAL MANDATORY REQUIREMENTS FOR RAG TOPICS (apply whenever the topic is about retrieval-augmented generation):

A. Complete RAG pipeline: Present and explain the full RAG workflow exactly in this order: prepare documents → chunk → embed → store in a vector database → embed the question → retrieve via similarity search → construct context → generate the answer. All eight steps must appear in the lesson body.
B. Required technical terms: Define and clearly explain ALL of these terms at their first use in the lesson body, AND list each one in KEY TERMS EXPLAINED: chunking, embeddings, vectors, vector databases, similarity search, context construction, context window, and hallucination. Do not use any of these words without defining it.
C. Worked example coverage: Walk the complete eight-step RAG workflow end to end inside the WORKED EXAMPLE (section 6) using one concrete, realistic scenario.
D. Context window: Explain that a context window is the limited amount of text the model can read at one time, and that carefully constructing the context from retrieved chunks is what makes the answer grounded and accurate.
E. Hallucination honesty: Explain that RAG reduces but does NOT eliminate hallucination — the model can still produce wrong answers, so its claims must still be checked against the source.
F. Retrieval limitations: In the limitations or misunderstandings section, explicitly state that retrieval is not perfect — the similarity search may return irrelevant or low-quality chunks, and that even when retrieval is correct, the generator may still produce inaccurate answers. Make clear that RAG does not guarantee factual correctness.

WRITING RULES (follow strictly):
- Use short sentences (under 20 words when possible).
- Explain every technical term before depending on it.
- Do not write "as we know" or assume any prior knowledge.
- Do not claim RAG guarantees correct answers or eliminates mistakes.
- Do not say RAG "forces" or "requires" the model to use retrieved content. Instead say RAG "provides retrieved information to help ground the answer" — the model can still ignore or misuse that information.
- Do not use absolute language like "always finds the right answer", "makes the model look up facts", or "prevents hallucination".
- Do not include specific numeric claims that cannot be verified without a reference source (e.g., do not write "768-dimensional vector", "top-3 results", or any other precise figure). Describe concepts qualitatively unless the numeric detail is provided in reference_material.
- Do not use real-world events, historical facts, dates, or named individuals in worked examples. Use clearly fictional or generic scenarios (e.g., "a company FAQ", "a student asking about photosynthesis", "a customer support bot"). Real events introduce specific claims that cannot be verified without reference material and will fail the accuracy checkpoint.
- When the topic is RAG, leaving out any of the eight pipeline steps or any of the required terms (chunking, embeddings, vectors, vector databases, similarity search, context construction, context window, hallucination) makes the lesson incomplete and it will fail evaluation.
- Use familiar, everyday analogies (library, search engine, recipe, etc.).
- The lesson must be complete — not an outline, not bullet points for each section (except where bullets are appropriate like KEY TERMS and RECAP).
- Avoid fabricated citations or invented facts.

Write the full lesson now. Use clear section headings matching the 10 sections above.
