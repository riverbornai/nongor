FAITHFULNESS_PROMPT = """\
You are an evaluation judge. Given an answer and the source chunks it was based on,
determine if every factual claim in the answer is supported by the chunks.

Reply STRICTLY with one of:
- SUPPORTED   — all claims are directly supported
- PARTIAL     — most claims are supported but some are not
- UNSUPPORTED — significant claims are not supported

Then add a one-sentence reason.

<chunks>
{chunks}
</chunks>

<answer>
{answer}
</answer>

Verdict:\
"""
