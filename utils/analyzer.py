"""Analyze an academic document against reference materials using Claude."""

import json
import asyncio
from typing import Any

import anthropic


_SYSTEM_PROMPT = """Eres un evaluador experto en documentos académicos. \
Tu tarea es determinar con precisión y detalle si un documento cumple con \
los lineamientos, syllabus y objetivos entregados como referencia.

Criterios de evaluación:
- Estructura y formato del documento
- Cobertura de los temas exigidos
- Profundidad y calidad del contenido
- Cumplimiento de objetivos declarados
- Uso apropiado del lenguaje académico
- Coherencia interna y organización

Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional ni bloques de código."""


def _build_prompt(
    reference_texts: list[dict],
    eval_text: str,
    eval_filename: str,
) -> str:
    refs = ""
    for i, ref in enumerate(reference_texts, 1):
        refs += (
            f"\n### [{i}] {ref['name']}\n\n"
            f"{ref['content']}\n\n"
            "---\n"
        )

    return f"""Analiza el documento a evaluar en función de los materiales de referencia proporcionados.

═══════════════════════════════════════
MATERIALES DE REFERENCIA
═══════════════════════════════════════
{refs}

═══════════════════════════════════════
DOCUMENTO A EVALUAR: {eval_filename}
═══════════════════════════════════════
{eval_text}

═══════════════════════════════════════
INSTRUCCIONES
═══════════════════════════════════════
Devuelve un JSON con esta estructura exacta (sin texto adicional):

{{
  "overall_compliance": <entero 0-100>,
  "executive_summary": "<resumen ejecutivo de 3-5 oraciones que describa el nivel de cumplimiento general>",
  "sections": [
    {{
      "section_name": "<nombre del aspecto o sección evaluada>",
      "compliance_percentage": <entero 0-100>,
      "observations": "<análisis detallado de este aspecto>",
      "corrections": ["<corrección específica y accionable 1>", "<corrección 2>"],
      "strengths": ["<fortaleza identificada 1>", "<fortaleza 2>"]
    }}
  ],
  "general_recommendations": ["<recomendación general 1>", "<recomendación 2>"],
  "missing_elements": ["<elemento o sección faltante 1>", "<elemento 2>"]
}}

Evalúa al menos 4 secciones o aspectos distintos del documento."""


def _sync_analyze(
    reference_texts: list[dict],
    eval_text: str,
    eval_filename: str,
) -> dict[str, Any]:
    client = anthropic.Anthropic()
    prompt = _build_prompt(reference_texts, eval_text, eval_filename)

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        final_message = stream.get_final_message()

    # Extract text block (skip thinking blocks)
    response_text = ""
    for block in final_message.content:
        if block.type == "text":
            response_text = block.text
            break

    return _parse_json(response_text)


def _parse_json(raw: str) -> dict[str, Any]:
    """Parse Claude's response, tolerating markdown code fences."""
    text = raw.strip()
    # Strip optional ```json ... ``` wrapper
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


async def analyze_document(
    reference_texts: list[dict],
    eval_text: str,
    eval_filename: str,
) -> dict[str, Any]:
    """Run the analysis in a thread pool to avoid blocking the event loop."""
    return await asyncio.to_thread(
        _sync_analyze, reference_texts, eval_text, eval_filename
    )
