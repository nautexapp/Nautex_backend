import logging
import json
from openai import OpenAI

from app.config import Settings
from app.services.keyvault import get_secret

logger = logging.getLogger(__name__)

# Constants
MAX_CHARS_FOR_SHORT_SUMMARY = 20000

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

def _log_usage_cost(name: str, prompt: int, completion: int, total: int, cached: int, miss: int):
    cost_input = (miss * PRICE_INPUT_PER_M / 1_000_000) + (cached * PRICE_CACHE_HIT_PER_M / 1_000_000)
    cost_output = completion * PRICE_OUTPUT_PER_M / 1_000_000
    total_cost = cost_input + cost_output
    logger.info(
        f"Tokens consumidos ({name}): Entrada: {prompt} (Caché: {cached}, Miss: {miss}) | Salida: {completion} | Total: {total} | "
        f"Coste Entrada: ${cost_input:.6f} | Coste Salida: ${cost_output:.6f} | Coste Total: ${total_cost:.6f} USD"
    )

SYSTEM_PROMPT = """\
Eres un experto pedagogo creando resúmenes de estudio de alta calidad.
Tu única fuente de información es el texto que el usuario te proporciona.
NUNCA uses conocimiento externo al texto facilitado.
No inventes información, cíñete estrictamente al material proporcionado.\
"""

SHORT_SUMMARY_PROMPT = """\
Lee el siguiente documento de estudio y redacta un resumen didáctico completo y bien estructurado.
Usa formato Markdown (encabezados, listas, negritas) para que sea fácil de estudiar.
Asegúrate de cubrir todos los puntos importantes.

--- DOCUMENTO ---
{text}
"""

INDEX_PROMPT = """\
Lee el siguiente documento de estudio y extrae un índice de los temas o conceptos principales que trata.
El resultado DEBE ser ÚNICAMENTE un JSON con un array de strings bajo la clave "topics".
Ejemplo: {"topics": ["Concepto A", "Procedimiento B", "Consecuencias C"]}

--- DOCUMENTO ---
{text}
"""

TOPIC_SUMMARY_PROMPT = """\
A continuación tienes un documento de estudio completo y un TEMA específico que debes resumir.

--- DOCUMENTO ---
{text}

--- TEMA A RESUMIR ---
{topic}

INSTRUCCIONES ESTRICTAS:
1. Redacta un resumen didáctico exhaustivo SOLAMENTE sobre el TEMA A RESUMIR, usando EXCLUSIVAMENTE la información que aparece en el documento.
2. Si el documento no menciona nada sobre el tema, responde indicando brevemente que el documento no contiene información sobre este punto.
3. Usa formato Markdown (encabezados, listas, negritas) para estructurar el contenido de forma óptima para el estudio.
4. No incluyas un saludo ni una introducción general, empieza directamente con el contenido del resumen bajo un encabezado Markdown de nivel 2 (##).
"""

def _get_client(settings: Settings) -> OpenAI:
    api_key = settings.ai_api_key
    if settings.azure_key_vault_url:
        try:
            api_key = get_secret(settings, settings.ai_api_key_secret_name)
        except Exception:
            pass
            
    if not api_key:
        raise RuntimeError("AI_API_KEY no está configurada.")

    return OpenAI(api_key=api_key.strip(), base_url=settings.ai_base_url)

def _generate_short_summary(client: OpenAI, model_name: str, text: str) -> str:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": SHORT_SUMMARY_PROMPT.format(text=text)}
        ],
        temperature=0.3,
        max_tokens=384000,
    )
    
    if response.usage:
        p, c, t, cached, miss = _extract_usage_metrics(response.usage)
        _log_usage_cost("Resumen Corto", p, c, t, cached, miss)
        
    return response.choices[0].message.content.strip()

def _generate_long_summary(client: OpenAI, model_name: str, text: str) -> str:
    # 1. Ask for index
    index_response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": INDEX_PROMPT.format(text=text)}
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=384000,
    )
    
    raw_json = index_response.choices[0].message.content.strip()
    # Limpiar posible markdown en la respuesta JSON
    if raw_json.startswith("```json"):
        raw_json = raw_json[7:]
    if raw_json.startswith("```"):
        raw_json = raw_json[3:]
    if raw_json.endswith("```"):
        raw_json = raw_json[:-3]
        
    start = raw_json.find('{')
    end = raw_json.rfind('}')
    if start != -1 and end != -1:
        raw_json = raw_json[start:end+1]
        
    try:
        index_data = json.loads(raw_json)
        topics = index_data.get("topics", [])
    except json.JSONDecodeError as exc:
        logger.error(f"Error decodificando JSON del índice: {exc}")
        topics = ["Resumen general"] # Fallback
        
    if not topics:
        topics = ["Resumen general"]

    logger.info(f"Índice generado con {len(topics)} temas: {topics}")
    
    # 2. Iterate over topics and ask for summary
    summaries = []
    total_p, total_c, total_t, total_cached, total_miss = _extract_usage_metrics(index_response.usage)
    
    for topic in topics:
        logger.info(f"Generando resumen para el tema: {topic}")
        topic_resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": TOPIC_SUMMARY_PROMPT.format(text=text, topic=topic)}
            ],
            temperature=0.3,
            max_tokens=384000,
        )
        
        if topic_resp.usage:
            p, c, t, cached, miss = _extract_usage_metrics(topic_resp.usage)
            total_p += p
            total_c += c
            total_t += t
            total_cached += cached
            total_miss += miss
            
        summaries.append(topic_resp.choices[0].message.content.strip())
        
    _log_usage_cost("Resumen Largo", total_p, total_c, total_t, total_cached, total_miss)
        
    # Assemble final markdown
    final_md = "# Resumen Didáctico\n\n"
    final_md += "\n\n".join(summaries)
    return final_md

def generate_summary(text: str, settings: Settings) -> str:
    """
    Genera un resumen didáctico del texto. Si es corto, usa una sola pasada.
    Si es largo, extrae un índice y resume cada punto.
    """
    client = _get_client(settings)
    
    if len(text) <= MAX_CHARS_FOR_SHORT_SUMMARY:
        logger.info(f"Texto corto ({len(text)} chars). Usando resumen directo.")
        return _generate_short_summary(client, settings.ai_model, text)
    else:
        logger.info(f"Texto largo ({len(text)} chars). Usando resumen por índice.")
        return _generate_long_summary(client, settings.ai_model, text)
