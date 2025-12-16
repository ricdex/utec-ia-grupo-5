"""
LLM-as-Judge evaluator for FinAdvisor
Uses Claude to evaluate response quality
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def create_explainability_judge():
    """
    Creates an LLM-as-judge evaluator for explainability scoring.

    Returns a function that can be used as a LangSmith evaluator.
    Uses Claude via Anthropic API for evaluation.
    """
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        logger.warning("langchain-anthropic not installed. LLM judge disabled.")
        return None

    # Check if API key is available
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY not set. LLM judge disabled.")
        return None

    # Initialize Claude (using Haiku for speed and cost-effectiveness)
    judge_llm = ChatAnthropic(
        model="claude-3-5-haiku-20241022",  # Fast and cost-effective
        temperature=0,  # Deterministic evaluation
        max_tokens=500
    )

    # Evaluation prompt
    JUDGE_PROMPT = """Eres un evaluador experto de respuestas financieras en español.

Tu tarea es calificar la calidad de la respuesta de un asistente financiero IA en una escala de 1 a 5.

CRITERIOS DE EVALUACIÓN:

**5 - Excelente:**
- TL;DR o resumen ejecutivo claro al inicio
- Explicación detallada del razonamiento (riesgo, retorno, horizonte)
- Lenguaje educativo que explica conceptos financieros
- Disclaimer apropiado presente
- Alineación perfecta con las metas del cliente

**4 - Muy Bueno:**
- Resumen presente pero podría ser más claro
- Buen razonamiento con explicaciones
- Usa terminología financiera correctamente
- Disclaimer presente
- Mayormente alineado con metas

**3 - Aceptable:**
- Resumen ausente o poco claro
- Razonamiento básico presente
- Algunos términos financieros usados
- Disclaimer genérico o débil
- Parcialmente alineado con metas

**2 - Deficiente:**
- Sin resumen
- Razonamiento pobre o confuso
- Lenguaje muy técnico o muy simple
- Disclaimer ausente o inadecuado
- Poco alineado con metas

**1 - Inaceptable:**
- Sin estructura ni claridad
- Sin razonamiento
- Sin educación financiera
- Sin disclaimers
- No responde a las necesidades del cliente

---

MENSAJE DEL USUARIO:
{input}

RESPUESTA DEL ASISTENTE:
{output}

---

INSTRUCCIONES:
1. Evalúa la respuesta según los criterios de arriba
2. Responde SOLO con un número del 1 al 5
3. No incluyas explicaciones, solo el número

CALIFICACIÓN:"""

    def llm_explainability_judge(run, example) -> Dict[str, Any]:
        """
        LLM-as-judge evaluator using Claude.

        Args:
            run: LangSmith run object with outputs
            example: LangSmith example object with inputs

        Returns:
            Dict with score (0-1 normalized) and comment
        """
        try:
            # Extract input and output
            inputs = example.inputs or {}
            outputs = run.outputs or {}

            user_message = inputs.get("message", "")

            # Extract response
            response_text = ""
            if isinstance(outputs, dict):
                response_text = outputs.get("response",
                               outputs.get("answer",
                               outputs.get("message", "")))
            elif isinstance(outputs, str):
                response_text = outputs

            if not response_text or not user_message:
                return {
                    "key": "explainability_score_llm",
                    "score": 0.0,
                    "comment": "Missing input or output text"
                }

            # Call Claude for judgment
            prompt_text = JUDGE_PROMPT.format(
                input=user_message,
                output=response_text
            )

            response = judge_llm.invoke(prompt_text)
            score_text = response.content.strip()

            # Parse score (1-5) and normalize to 0-1
            try:
                score_value = int(score_text)
                if score_value < 1 or score_value > 5:
                    raise ValueError(f"Score out of range: {score_value}")

                normalized_score = score_value / 5.0

                return {
                    "key": "explainability_score_llm",
                    "score": normalized_score,
                    "comment": f"Claude judge: {score_value}/5"
                }
            except (ValueError, AttributeError) as e:
                logger.error(f"Failed to parse LLM score: {score_text}, error: {e}")
                return {
                    "key": "explainability_score_llm",
                    "score": 0.0,
                    "comment": f"Failed to parse score: {score_text}"
                }

        except Exception as e:
            logger.error(f"LLM judge error: {e}")
            return {
                "key": "explainability_score_llm",
                "score": 0.0,
                "comment": f"Evaluation error: {str(e)}"
            }

    return llm_explainability_judge


# Global instance
_llm_judge_instance = None


def get_llm_judge():
    """Get or create LLM judge singleton"""
    global _llm_judge_instance
    if _llm_judge_instance is None:
        _llm_judge_instance = create_explainability_judge()
    return _llm_judge_instance
