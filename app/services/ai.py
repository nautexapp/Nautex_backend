import logging
import re

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings
from app.schemas.question import QuestionAI, QuestionSetAI, UsageStats
from app.services.keyvault import get_secret

logger = logging.getLogger(__name__)

# ── Precios DeepSeek V3 (USD por millón de tokens) aproximados ───────────────
PRICE_INPUT_PER_M  = 0.14
PRICE_OUTPUT_PER_M = 0.28
PRICE_CACHE_HIT_PER_M = 0.0028

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

# ── Configuración de chunking ─────────────────────────────────────────────────
MAX_CHUNK_CHARS = 2500
MIN_CHUNK_CHARS = 500
MAX_EXISTING_QUESTIONS_IN_PROMPT = 15

# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
Eres un experto en pedagogía especializado en crear tests de evaluación de alta calidad.
Tu única fuente de información son los fragmentos de texto que el usuario te proporciona.
NUNCA uses conocimiento externo al texto facilitado.
Responde ÚNICAMENTE con JSON válido siguiendo exactamente el esquema que se te indique.\
"""

CHUNK_PROMPT_TEMPLATE = """\
A continuación tienes un fragmento de un documento de estudio:

---
{chunk}
---
{existing_block}
INSTRUCCIONES ESTRICTAS:
1. Genera TODAS las preguntas tipo test posibles a partir del fragmento de texto anterior.
   No hay un máximo: crea tantas como sean necesarias para cubrir cada concepto, dato,
   definición, procedimiento o hecho relevante del texto.
2. CIÑETE ESTRICTAMENTE A LA INFORMACIÓN EXPLÍCITA. No extrapoles ni asumas consecuencias lógicas que no estén literalmente escritas en el fragmento.
3. NO repitas ni parafrasees ninguna de las preguntas ya generadas listadas arriba.
4. Cada pregunta debe tener exactamente 4 opciones: la PRIMERA opción de la lista DEBE ser SIEMPRE la correcta, y las otras 3 totalmente falsas. Asegúrate rigurosamente de que no haya ambigüedad.
5. Varía el tipo de preguntas: definición, aplicación, comparación, consecuencia, etc.
6. Si el fragmento no contiene contenido evaluable, devuelve {{"questions": []}}.
7. Genera las preguntas en el mismo orden cronológico en el que aparecen los conceptos en el texto.
8. NUNCA comiences el enunciado de las preguntas con frases como "Según el texto", "De acuerdo al documento", "El fragmento menciona que", etc. Haz las preguntas de forma directa y universal.
9. Devuelve ÚNICAMENTE el siguiente JSON minificado (sin markdown, sin texto extra) donde 't' es el enunciado y 'o' es la lista de opciones (la primera es la correcta):
{{
  "questions": [
    {{
      "t": "Enunciado de la pregunta",
      "o": [
        "Opción correcta",
        "Opción falsa 1",
        "Opción falsa 2",
        "Opción falsa 3"
      ]
    }}
  ]
}}\
"""

EXISTING_BLOCK_TEMPLATE = """\
Preguntas ya generadas para este documento (NO las repitas ni las parafrasees):
{questions_list}

"""


# ── Chunking ──────────────────────────────────────────────────────────────────

def _split_by_headings(text: str) -> list[str]:
    sections = re.split(r"(?m)^(?=#{1,4}\s)", text)
    return [s.strip() for s in sections if s.strip()]


def _split_by_paragraphs(text: str, max_chars: int) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chars and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = [para]
            current_len = len(para)
        else:
            current_parts.append(para)
            current_len += len(para)

    if current_parts:
        chunks.append("\n\n".join(current_parts))
    return chunks


def _prepare_chunks(text: str) -> list[str]:
    sections = _split_by_headings(text)
    chunks: list[str] = []
    buffer = ""

    for section in sections:
        if len(section) > MAX_CHUNK_CHARS:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(_split_by_paragraphs(section, MAX_CHUNK_CHARS))
        elif len(buffer) + len(section) > MAX_CHUNK_CHARS:
            chunks.append(buffer)
            buffer = section
        else:
            buffer = (buffer + "\n\n" + section).strip() if buffer else section

    if buffer:
        chunks.append(buffer)

    return [c for c in chunks if len(c.strip()) >= MIN_CHUNK_CHARS]


# ── Generación por chunk ──────────────────────────────────────────────────────

def _generate_for_chunk(
    client,
    model_name: str,
    chunk: str,
    existing_questions: list[QuestionAI],
    depth: int = 0,
) -> tuple[list[QuestionAI], int, int]:
    """
    Genera preguntas para un chunk.

    Returns:
        Tupla (preguntas_válidas, tokens_entrada, tokens_salida)
    """
    if existing_questions:
        sample = existing_questions[-MAX_EXISTING_QUESTIONS_IN_PROMPT:]
        q_list = "\n".join(f"- {q.text}" for q in sample)
        existing_block = EXISTING_BLOCK_TEMPLATE.format(questions_list=q_list)
    else:
        existing_block = ""

    prompt = CHUNK_PROMPT_TEMPLATE.format(chunk=chunk, existing_block=existing_block)

    @retry(
        wait=wait_exponential(multiplier=2, min=10, max=60),
        stop=stop_after_attempt(5),
        reraise=True
    )
    def _call_api_with_retry():
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=384000,
        )

        raw_text = response.choices[0].message.content
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
            
        try:
            q_set = QuestionSetAI.model_validate_json(raw_text)
            return response, q_set
        except Exception as json_exc:
            logger.warning("JSON inválido o truncado devuelto por la IA. Reintentando... Detalle: %s", json_exc)
            raise ValueError(f"JSON inválido: {json_exc}") from json_exc

    try:
        response, question_set = _call_api_with_retry()
    except Exception as exc:
        if depth < 2 and len(chunk) > MIN_CHUNK_CHARS * 2:
            logger.warning("Chunk falló (profundidad %d). Dividiendo chunk por la mitad. Detalle: %s", depth, exc)
            mid = len(chunk) // 2
            break_point = chunk.rfind('\n\n', 0, mid + 500)
            if break_point == -1 or break_point < len(chunk) // 4:
                break_point = chunk.rfind('\n', 0, mid + 500)
            if break_point == -1 or break_point < len(chunk) // 4:
                break_point = chunk.rfind('.', 0, mid + 500)
                if break_point != -1:
                    break_point += 1
            if break_point <= 0:
                break_point = mid
                
            chunk1 = chunk[:break_point].strip()
            chunk2 = chunk[break_point:].strip()
            
            valid_q = []
            total_in = 0
            total_out = 0
            total_t = 0
            total_cache = 0
            total_miss = 0
            
            if chunk1:
                q1, in1, out1, t1, cache1, miss1 = _generate_for_chunk(client, model_name, chunk1, existing_questions, depth=depth+1)
                valid_q.extend(q1)
                total_in += in1
                total_out += out1
                total_t += t1
                total_cache += cache1
                total_miss += miss1
                
            if chunk2:
                q2, in2, out2, t2, cache2, miss2 = _generate_for_chunk(client, model_name, chunk2, existing_questions + valid_q, depth=depth+1)
                valid_q.extend(q2)
                total_in += in2
                total_out += out2
                total_t += t2
                total_cache += cache2
                total_miss += miss2
                
            return valid_q, total_in, total_out, total_t, total_cache, total_miss
        else:
            raise RuntimeError(f"Error al llamar a la API tras reintentos y subdivisiones máximas: {exc}") from exc

    # Extraer conteo de tokens
    usage = getattr(response, "usage", None)
    input_tokens, output_tokens, total_tokens, cached_tokens, miss_tokens = _extract_usage_metrics(usage)

    # Validar que el índice de la opción correcta es válido
    valid: list[QuestionAI] = []
    for q in question_set.questions:
        if 1 <= q.correct_option <= len(q.options):
            valid.append(q)
        else:
            logger.warning("Pregunta descartada (índice c=%d inválido): '%s'", q.correct_option, q.text[:60])

    return valid, input_tokens, output_tokens, total_tokens, cached_tokens, miss_tokens


# ── Cálculo de coste ──────────────────────────────────────────────────────────

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


# ── Punto de entrada público ──────────────────────────────────────────────────

def generate_questions(text: str, settings: Settings) -> QuestionSetAI:
    """
    Genera todas las preguntas posibles del documento dividiéndolo en chunks.

    Devuelve un QuestionSetAI con las preguntas y las métricas de uso/coste.
    """
    from openai import OpenAI

    # Obtener clave API (prioridad: Key Vault -> .env)
    api_key = settings.ai_api_key
    if settings.azure_key_vault_url:
        try:
            api_key = get_secret(settings, settings.ai_api_key_secret_name)
        except Exception:
            pass
            
    if not api_key:
        raise RuntimeError("AI_API_KEY no está configurada (ni en .env ni en Key Vault).")

    client = OpenAI(api_key=api_key.strip(), base_url=settings.ai_base_url)

    chunks = _prepare_chunks(text)
    logger.info(
        "Documento dividido en %d chunks (total %d caracteres).",
        len(chunks), len(text),
    )

    all_questions: list[QuestionAI] = []
    total_input = 0
    total_output = 0
    chunks_ok = 0

    for i, chunk in enumerate(chunks, start=1):
        logger.info("Procesando chunk %d/%d (%d chars)...", i, len(chunks), len(chunk))
        try:
            new_qs, inp, out = _generate_for_chunk(client, settings.ai_model, chunk, all_questions)
            all_questions.extend(new_qs)
            total_input  += inp
            total_output += out
            chunks_ok    += 1
            logger.info(
                "Chunk %d: +%d preguntas | tokens in=%d out=%d | acumulado: %d preguntas",
                i, len(new_qs), inp, out, len(all_questions),
            )
        except Exception as exc:
            logger.error("Error en chunk %d: %s. Continuando...", i, exc)

    usage = _compute_usage(chunks_ok, total_input, total_output)

    logger.info(
        "✅ Generación completada: %d preguntas | %d tokens entrada | %d tokens salida | "
        "coste total: $%.4f USD",
        len(all_questions),
        total_input,
        total_output,
        usage.cost_total_usd,
    )

    return QuestionSetAI(questions=all_questions, usage=usage)
