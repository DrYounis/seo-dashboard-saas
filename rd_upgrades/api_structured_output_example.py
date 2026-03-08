# Upgrade: Structured LLM Outputs with Pydantic
# Category: reliability
# Risk: safe
# Generated: 2026-02-18T07:39:27.351892
# Description: Use Groq's structured output mode for reliable JSON responses

# ── BEFORE ───────────────────────────────────────────────────────────────────
# Old: parse LLM text manually
result = llm.complete("Generate code for: " + task)
# Hope it returns valid JSON...
code = result.split("```")[1]

# ── AFTER (APPLY THIS) ────────────────────────────────────────────────────────
# New: structured outputs (2025 pattern)
from pydantic import BaseModel
from groq import Groq

class CodeOutput(BaseModel):
    code: str
    language: str
    explanation: str
    tests: list[str]

client = Groq()
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": f"Generate code for: {task}"}],
    response_format={"type": "json_object"},  # Structured output
)
output = CodeOutput.model_validate_json(response.choices[0].message.content)
