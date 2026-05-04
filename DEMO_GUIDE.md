# Guia de demo - Rappi AI Ops Assistant

## 1. Contexto y approach (3 min)

Mensaje principal:

> El reto no era construir solo un chatbot, sino una capa analitica confiable para que usuarios de negocio puedan consultar metricas operacionales sin saber SQL o Python.

Puntos:

- Interprete el problema como democratizacion de insights operacionales.
- Separe el sistema en ETL, base SQL, bot, visualizaciones e insights automaticos.
- Priorice reproducibilidad y trazabilidad: cada respuesta se basa en DuckDB y muestra el SQL ejecutado.

## 2. Arquitectura (3 min)

Explicar:

```text
Excel raw -> ETL Python -> CSV transformado -> DuckDB -> Streamlit -> Bot + Insights
```

Decisiones:

- DuckDB para SQL local, rapido y reproducible.
- Streamlit para demo viva en localhost.
- LLM solo como capa de interpretacion y redaccion, no para SQL libre.
- Fallback deterministico si falla la API.

Frase clave:

> El LLM interpreta la pregunta, pero los calculos vienen de SQL controlado sobre datos estructurados.

## 3. ETL y modelo de datos (3 min)

Explicar:

- Limpieza de pais, ciudad, zona, tipo de zona, priorizacion y metrica.
- Quitar acentos, separadores raros y espacios dobles.
- Convertir semanas de columnas a filas con `melt`.
- Unir ordenes por `COUNTRY_CODE + CITY + ZONE + WEEK_LAG`.

Grano final:

```text
pais + ciudad + zona + semana + metrica
```

Nota importante:

> Las ordenes se repiten por metrica como contexto. Para sumar ordenes, se deduplica por zona-semana.

## 4. Demo bot (8-10 min)

Preguntas sugeridas:

1. `Cuales son las 5 zonas con mayor Lead Penetration esta semana?`
2. `Compara el Perfect Orders entre zonas Wealthy y Non Wealthy en Mexico`
3. `Muestra la evolucion de Gross Profit UE en Chapinero ultimas 8 semanas`
4. `Que zonas tienen alto Lead Penetration pero bajo Perfect Orders?`
5. `Cuales son las zonas que mas crecen en ordenes en las ultimas 5 semanas?`

Mostrar:

- Respuesta textual.
- Tabla.
- Grafico.
- SQL ejecutado.
- Sugerencias de seguimiento.

## 5. Insights automaticos (5 min)

Mostrar pestana `Insights`.

Categorias:

- Anomalias semana contra semana.
- Tendencias preocupantes.
- Benchmarking contra zonas similares.
- Correlaciones.
- Oportunidades de alto volumen.

Frase clave:

> Las reglas detectan candidatos; el equipo operativo decide accion con contexto de negocio.

## 6. Limitaciones y siguientes pasos (2 min)

Limitaciones:

- Datos anonimizados/randomizados.
- Parser deterministico cubre los casos principales.
- Correlacion no implica causalidad.
- No hay deployment cloud en esta version.

Siguientes pasos:

- Ampliar intents con LLM y validacion semantica.
- Agregar autenticacion y roles.
- Integrar envio semanal por email/Slack/n8n.
- Crear monitoreo automatico de alertas.
- Conectar a warehouse real.

## Preguntas que pueden hacer

**Por que DuckDB?**

Porque da SQL analitico local, rapido y reproducible sin infraestructura.

**Por que no dejar que el LLM genere SQL directamente?**

Por seguridad y precision. El LLM puede alucinar columnas o crear queries riesgosas. Aqui interpreta intencion y el backend ejecuta consultas permitidas.

**Como controlas errores de agregacion con ordenes duplicadas?**

La tabla esta a grano zona-semana-metrica, por eso las ordenes se repiten como contexto. Para totales de ordenes se usa `DISTINCT` por zona-semana o queries controladas.

**Como escalaria?**

Separaria ETL en pipeline orquestado, DuckDB por warehouse, Streamlit por app interna, y agregaria observabilidad, auth y evaluacion de calidad de respuestas.
