# Rappi AI Ops Assistant

Sistema local de analisis inteligente para operaciones Rappi. El proyecto combina ETL, DuckDB, Streamlit, consultas SQL controladas, bot conversacional con guardrails e insights automaticos.

## Objetivo

Democratizar el acceso a metricas operacionales para usuarios de negocio, permitiendo:

- Hacer preguntas en lenguaje natural sobre zonas, paises, metricas y semanas.
- Ejecutar analisis reproducibles sobre datos limpios.
- Generar insights automaticos accionables.
- Mostrar tablas, graficos y SQL ejecutado para trazabilidad.

## Arquitectura

```text
Excel raw
  -> ETL Python
  -> metrics_with_orders_transformed.csv
  -> DuckDB local
  -> Streamlit app
  -> Bot con LLM + guardrails / reglas deterministicas
  -> Insights automaticos + reporte Markdown
```

La tabla principal queda a grano:

```text
pais + ciudad + zona + semana + metrica
```

Las ordenes se unen como contexto por:

```text
COUNTRY_CODE + CITY + ZONE + WEEK_LAG
```

## Stack

- Python 3.11+
- Streamlit
- Pandas
- DuckDB
- Plotly
- OpenAI API

## Configuracion inicial

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edita `.env` y agrega:

```text
OPENAI_API_KEY=tu_api_key
OPENAI_MODEL=gpt-4o-mini
```

`.env` no debe subirse a GitHub.

## Flujo de ejecucion

1. Procesar datos:

```powershell
python scripts/build_dataset.py
```

2. Construir DuckDB:

```powershell
python scripts/build_database.py
```

3. Validar consultas:

```powershell
python scripts/validate_queries.py
```

4. Generar reporte ejecutivo:

```powershell
python scripts/generate_report.py
```

5. Ejecutar app:

```powershell
streamlit run app.py
```

## App

La app incluye:

- Bot conversacional deterministico y modo `LLM + guardrails`.
- Resumen de filas, paises, ciudades, zonas, metricas y match de ordenes.
- Ranking de zonas por metrica.
- Comparacion por tipo de zona.
- Tendencia temporal por zona.
- Analisis multivariable entre dos metricas.
- Insights automaticos.
- Descarga de reporte Markdown.
- Preview de la tabla SQL principal.

## Preguntas de demo

- `Cuales son las 5 zonas con mayor Lead Penetration esta semana?`
- `Compara el Perfect Orders entre zonas Wealthy y Non Wealthy en Mexico`
- `Muestra la evolucion de Gross Profit UE en Chapinero ultimas 8 semanas`
- `Que zonas tienen alto Lead Penetration pero bajo Perfect Orders?`
- `Cuales son las zonas que mas crecen en ordenes en las ultimas 5 semanas?`

## Decisiones tecnicas

- DuckDB permite una capa SQL local sin depender de infraestructura cloud.
- El LLM no ejecuta SQL libre. Interpreta la pregunta y el backend ejecuta consultas controladas.
- Si OpenAI falla o no hay API key, el bot usa reglas deterministicas.
- El ETL conserva el raw intacto y genera un dataset procesado limpio.
- Los textos se normalizan antes del join para mejorar el match entre fuentes.

## Costo estimado

- Modo deterministico: USD 0 por pregunta.
- Modo LLM: bajo costo por pregunta porque se envia la pregunta, un plan JSON y resultados resumidos. Para una demo de 10 preguntas, el costo esperado es bajo usando `gpt-4o-mini`.

## Limitaciones

- Los datos son anonimizados y randomizados.
- Las ordenes se repiten por metrica en la tabla extendida; para sumar ordenes se debe deduplicar por zona-semana.
- El parser deterministico cubre preguntas clave del caso, no todo lenguaje natural posible.
- Las correlaciones son hipotesis, no causalidad.

## Estructura

```text
app.py                         App Streamlit
src/chatbot.py                 Bot, intents y guardrails
src/database.py                Conexion y carga DuckDB
src/insights.py                Motor de insights automaticos
src/queries.py                 Consultas SQL reutilizables
src/transform.py               ETL y normalizacion
src/text_utils.py              Limpieza de texto
scripts/build_dataset.py       Genera CSV transformado
scripts/build_database.py      Crea DuckDB
scripts/validate_queries.py    Pruebas SQL de negocio
scripts/generate_report.py     Genera reporte Markdown
data/raw/                      Datos originales
data/processed/                Datos procesados y DuckDB
outputs/                       Reportes generados
```
