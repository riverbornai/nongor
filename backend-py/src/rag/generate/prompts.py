from __future__ import annotations

# ── Prompt used when relevant context chunks are available ──────────────────
ANSWER_PROMPT = """\
You are a knowledgeable and helpful AI assistant with access to a curated knowledge base.
Your job is to answer the user's question as accurately and helpfully as possible.

Guidelines:
1. PRIORITIZE the provided context — if the answer is present there, cite the relevant
   source(s) by placing the bare UUID in square brackets immediately after the claim,
   like this: [d023daf1-c4f9-4c46-9a1e-bd4f0a9c0794]. Multiple citations: [uuid1][uuid2].
   The UUID is the value shown after "ref:" in each context block below.
2. If the context only partially answers the question, cite what it covers and supplement
   with your general knowledge. Clearly indicate which parts come from the knowledge base.
3. If the context is entirely irrelevant to the question, answer using your general
   knowledge. Do NOT mention that context was missing — just answer naturally.
4. If multiple chunks contradict each other, acknowledge both sides and cite each.
5. Be clear, concise, and helpful.
6. NEVER copy the "[ref:uuid]" label into your answer. Only embed the bare [uuid].

<context>
{context_blocks}
</context>

<question>
{question}
</question>

Answer:\
"""

# ── Prompt used when NO context chunks were retrieved at all ────────────────
NO_CONTEXT_PROMPT = """\
You are a knowledgeable and helpful AI assistant.
No specific knowledge-base documents were found for this query, so answer using
your general training knowledge.

Be accurate, concise, and helpful. If the question is outside your knowledge,
say so honestly — but do not refuse to engage.

<question>
{question}
</question>

Answer:\
"""

CONTEXT_BLOCK_TEMPLATE = """\
[ref:{id}]
source: {source}
section: {section}
---
{text}\
"""


def build_answer_prompt(query: str, chunks: list[dict]) -> str:
    """Build a prompt that includes retrieved context chunks."""
    context_blocks = "\n\n".join(
        CONTEXT_BLOCK_TEMPLATE.format(
            id=c["id"],
            source=c["source"],
            section=" > ".join(c.get("section_path") or []) or "(root)",
            text=c["text"],
        )
        for c in chunks
    )
    return ANSWER_PROMPT.format(context_blocks=context_blocks, question=query)


def build_no_context_prompt(query: str) -> str:
    """Build a general-knowledge prompt when no context was retrieved."""
    return NO_CONTEXT_PROMPT.format(question=query)
