import logging
import json

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.schemas.question import QuestionAI, QuestionSetAI, UsageStats
from app.services.keyvault import get_secret
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Precios DeepSeek V3 (USD por millón de tokens) aproximados ───────────────
PRICE_INPUT_PER_M  = 0.14
PRICE_OUTPUT_PER_M = 0.28
PRICE_CACHE_HIT_PER_M = 0.0028

# ── Prompts ───────────────────────────────────────────────────────────────────
INDEX_PROMPT_SYSTEM = """\
Eres un experto analista académico. 
Tu tarea es leer el texto proporcionado y extraer un ÍNDICE EXHAUSTIVO de todos los temas, conceptos, epígrafes o ideas clave que contiene, de principio a fin.
ES CRÍTICO QUE NO TE SALTES ABSOLUTAMENTE NINGÚN CONCEPTO DEL TEXTO. Cada detalle mínimamente relevante o evaluable debe quedar recogido dentro de uno de los temas del índice.
El índice será usado paso a paso para generar preguntas. Si omites algo, nunca se preguntará sobre ello.
Devuelve ÚNICAMENTE un JSON válido con este formato:
{
  "topics": [
    "Nombre del Tema 1",
    "Nombre del Tema 2"
  ]
}\
"""

TOPIC_PROMPT_SYSTEM = """\
Eres un experto en pedagogía especializado en crear tests de evaluación de alta calidad.
Tu única fuente de información es el documento de estudio que el usuario te facilitará.
NUNCA uses conocimiento externo al texto.
"""

TOPIC_PROMPT_USER = """\
DOCUMENTO COMPLETO:
---
{full_text}
---

INSTRUCCIONES ESTRICTAS:
1. Genera preguntas tipo test EXCLUSIVAMENTE para el siguiente tema extraído del documento:
   >> TEMA ACTUAL: "{topic}" <<

2. DEBES preguntar por ABSOLUTAMENTE TODOS los conceptos expuestos sobre este TEMA ACTUAL en el documento. No te dejes ningún detalle evaluable sin su correspondiente pregunta.
3. CIÑETE ESTRICTAMENTE A LA INFORMACIÓN EXPLÍCITA. No extrapoles.
4. NO repitas preguntas sobre conceptos que claramente pertenezcan a otros temas generales del documento.
5. Cada pregunta debe tener exactamente 4 opciones: la PRIMERA opción de la lista DEBE ser SIEMPRE la correcta, y las otras 3 totalmente falsas e inconfundibles.
6. Si descubres que el tema actual no tiene contenido útil para evaluar en el texto, devuelve la lista de preguntas vacía.
7. Devuelve ÚNICAMENTE el siguiente JSON minificado donde 't' es el enunciado y 'o' es la lista de opciones:
{
  "questions": [
    {
      "t": "Enunciado",
      "o": ["Correcta", "Falsa 1", "Falsa 2", "Falsa 3"]
    }
  ]
}\
"""

class TopicIndex(BaseModel):
    topics: list[str]

# ── Extracción de Métricas ────────────────────────────────────────────────────
def _extract_usage_metrics(usage):
    if not usage:
        return 0, 0, 0, 0, 0
    
    prompt = getattr(usage, "prompt_tokens", 0) or 0
    completion = getattr(usage, "completion_tokens", 0) or 0
    total = getattr(usage, "total_tokens", 0) or 0
    
    usage_dict = usage.model_dump() if hasattr(usage, "model_dump") else getattr(usage, "__dict__", {})
    
    cached = getattr(usage, "prompt_cache_hit_tokens", None)
    if cached is None:
        cached = usage_dict.get("prompt_cache_hit_tokens")
    if cached is None:
        details = getattr(usage, "prompt_tokens_details", None)
        if details:
            cached = getattr(details, "cached_tokens", 0) or 0
        else:
            cached = usage_dict.get("prompt_tokens_details", {}).get("cached_tokens", 0) or 0
            
    miss = getattr(usage, "prompt_cache_miss_tokens", None)
    if miss is None:
        miss = usage_dict.get("prompt_cache_miss_tokens")
    if miss is None:
        miss = max(0, prompt - cached)
        
    if not total:
        total = prompt + completion

    return prompt, completion, total, cached, miss

def _compute_usage(
    chunks_processed: int,
    total_input: int,
    total_output: int,
    total_t: int,
    total_cached: int,
    total_miss: int,
) -> UsageStats:
    cost_input = (total_miss * PRICE_INPUT_PER_M / 1_000_000) + (total_cached * PRICE_CACHE_HIT_PER_M / 1_000_000)
    cost_output = total_output * PRICE_OUTPUT_PER_M / 1_000_000
    
    return UsageStats(
        chunks_processed=chunks_processed,
        input_tokens=total_input,
        cached_tokens=total_cached,
        output_tokens=total_output,
        total_tokens=total_t,
        cost_input_usd=round(cost_input, 6),
        cost_output_usd=round(cost_output, 6),
        cost_total_usd=round(cost_input + cost_output, 6),
    )

def _clean_json_response(raw_text: str) -> str:
    raw_text = raw_text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
        
    start = raw_text.find('{')
    end = raw_text.rfind('}')
    if start != -1 and end != -1:
        raw_text = raw_text[start:end+1]
    return raw_text

# ── Funciones de IA ──────────────────────────────────────────────────────────

def _generate_topic_index(client, model_name: str, text: str) -> tuple[list[str], int, int, int, int, int]:
    @retry(
        wait=wait_exponential(multiplier=2, min=10, max=60),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def _call():
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": INDEX_PROMPT_SYSTEM},
                {"role": "user", "content": f"DOCUMENTO:\n---\n{text}\n---"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=8192,
        )
        raw_text = _clean_json_response(response.choices[0].message.content)
        try:
            index_data = TopicIndex.model_validate_json(raw_text)
            return response, index_data.topics
        except Exception as json_exc:
            logger.warning("JSON de índice inválido. Reintentando... Detalle: %s", json_exc)
            raise ValueError(f"JSON inválido: {json_exc}") from json_exc

    response, topics = _call()
    usage = getattr(response, "usage", None)
    inp, out, tot, cached, miss = _extract_usage_metrics(usage)
    return topics, inp, out, tot, cached, miss

def _generate_for_topic(client, model_name: str, text: str, topic: str) -> tuple[list[QuestionAI], int, int, int, int, int]:
    prompt_user = TOPIC_PROMPT_USER.format(full_text=text, topic=topic)

    @retry(
        wait=wait_exponential(multiplier=2, min=10, max=60),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def _call():
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": TOPIC_PROMPT_SYSTEM},
                {"role": "user", "content": prompt_user}
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=8192,
        )
        raw_text = _clean_json_response(response.choices[0].message.content)
        try:
            q_set = QuestionSetAI.model_validate_json(raw_text)
            return response, q_set
        except Exception as json_exc:
            logger.warning("JSON de preguntas inválido (Tema: %s). Reintentando... Detalle: %s", topic, json_exc)
            raise ValueError(f"JSON inválido: {json_exc}") from json_exc

    response, question_set = _call()
    usage = getattr(response, "usage", None)
    inp, out, tot, cached, miss = _extract_usage_metrics(usage)

    valid: list[QuestionAI] = []
    for q in question_set.questions:
        if 1 <= q.correct_option <= len(q.options):
            valid.append(q)
        else:
            logger.warning("Pregunta descartada (índice c=%d inválido): '%s'", q.correct_option, q.text[:60])

    return valid, inp, out, tot, cached, miss

# ── Punto de entrada público ──────────────────────────────────────────────────

from typing import Callable

def generate_questions_cached(
    text: str, 
    settings: Settings,
    progress_callback: Callable[[int, int], None] | None = None
) -> QuestionSetAI:
    from openai import OpenAI

    api_key = settings.ai_api_key
    if settings.azure_key_vault_url:
        try:
            api_key = get_secret(settings, settings.ai_api_key_secret_name)
        except Exception:
            pass
            
    if not api_key:
        raise RuntimeError("AI_API_KEY no está configurada (ni en .env ni en Key Vault).")

    client = OpenAI(api_key=api_key.strip(), base_url=settings.ai_base_url)

    logger.info("Iniciando generación cached para documento de %d chars.", len(text))

    total_input = 0
    total_output = 0
    total_t = 0
    total_cache = 0
    total_miss = 0

    # 1. Generar Índice
    logger.info("Generando Índice de temas...")
    topics, inp, out, tot, cached, miss = _generate_topic_index(client, settings.ai_model, text)
    total_input += inp
    total_output += out
    total_t += tot
    total_cache += cached
    total_miss += miss

    logger.info("Índice extraído con %d temas: %s", len(topics), topics)

    all_questions: list[QuestionAI] = []
    
    # 2. Iterar por Temas
    total_topics = len(topics)
    for i, topic in enumerate(topics, start=1):
        logger.info("Generando preguntas para tema %d/%d: %s", i, total_topics, topic)
        try:
            new_qs, inp, out, tot, cached, miss = _generate_for_topic(client, settings.ai_model, text, topic)
            all_questions.extend(new_qs)
            
            total_input += inp
            total_output += out
            total_t += tot
            total_cache += cached
            total_miss += miss
            
            logger.info(
                "Tema %d completado: +%d preguntas | caché usada=%d | acumulado: %d preguntas",
                i, len(new_qs), cached, len(all_questions)
            )
        except Exception as exc:
            logger.error("Error en tema %d ('%s'): %s. Continuando...", i, topic, exc)
            
        if progress_callback:
            progress_callback(i, total_topics)

    usage = _compute_usage(len(topics), total_input, total_output, total_t, total_cache, total_miss)

    logger.info(
        "✅ Generación Cached completada: %d preguntas | %d tokens entrada (%d cacheados) | %d tokens salida | coste: $%.4f USD",
        len(all_questions),
        total_input,
        total_cache,
        total_output,
        usage.cost_total_usd,
    )

    return QuestionSetAI(questions=all_questions, usage=usage)
