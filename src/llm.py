import json

from openai import OpenAI

from src.config import OPENAI_API_KEY, OPENAI_MODEL


SYSTEM_PROMPT = """
You translate Spanish business questions about Rappi operational data into a safe JSON plan.
Return only valid JSON. Do not return SQL.

Allowed intents:
- top_zones
- compare_zone_type
- trend
- high_low
- order_growth
- fallback

Allowed metrics:
- % PRO Users Who Breakeven
- % Restaurants Sessions With Optimal Assortment
- Gross Profit UE
- Lead Penetration
- MLTV Top Verticals Adoption
- Non PRO PTC > OP
- Perfect Orders
- Pro Adoption Last Week Status
- Restaurants Markdowns GMV
- Restaurants SS > ATC CVR
- Restaurants SST > SS CVR
- Retail SST > SS CVR
- Turbo Adoption

Return this JSON shape:
{
  "intent": "top_zones",
  "metric": "Lead Penetration",
  "country": null,
  "city": null,
  "zone": null,
  "week_lag": 0,
  "weeks_back": 8,
  "limit": 5,
  "high_metric": null,
  "low_metric": null,
  "high_threshold": null,
  "low_threshold": null
}

Rules:
- If the user asks "ultimas N semanas", set "weeks_back" to N.
- If the user asks "top N" or "N zonas", set "limit" to N.
- If the user asks "esta semana", set "week_lag" to 0.
- For high/low questions, fill high_metric, low_metric, high_threshold and low_threshold when explicit.
- If a threshold is not explicit, use null and let the backend defaults apply.
- If the question asks for growth in orders over N weeks, use intent "order_growth" and weeks_back N.
"""


def is_llm_available() -> bool:
    return bool(OPENAI_API_KEY)


def interpret_question(question: str) -> dict:
    """Use the LLM to convert a natural-language question into a controlled plan."""
    if not is_llm_available():
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )

    content = response.choices[0].message.content or "{}"
    return json.loads(content)


def summarize_answer(question: str, data_markdown: str, base_answer: str) -> str:
    """Use the LLM to produce a concise executive answer from real query results."""
    if not is_llm_available():
        return base_answer

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an operations analytics assistant. Answer in Spanish, concise and executive. "
                    "Use only the provided table. Do not invent data."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pregunta: {question}\n\n"
                    f"Respuesta base: {base_answer}\n\n"
                    f"Datos:\n{data_markdown}\n\n"
                    "Redacta una respuesta ejecutiva de 2 a 4 frases."
                ),
            },
        ],
    )

    return response.choices[0].message.content or base_answer
