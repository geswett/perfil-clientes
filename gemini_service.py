"""Funciones que hablan con la API de Gemini:

1. transcribe_audio()   -> transcribe una grabación de reunión (audio) a texto.
2. transcribe_image()   -> transcribe una foto de una hoja (manuscrita o impresa) a texto.
3. structure_profile()  -> toma el texto en bruto (transcripción o texto escrito en
   computador) y lo estructura en el esquema PerfilCargo definido en schema.py.

El modelo se puede ajustar con las variables de entorno GEMINI_MODEL_MULTIMODAL
(para audio/imagen) y GEMINI_MODEL_TEXT (para estructurar el perfil). Por
defecto se usa gemini-3.7-flash en ambos casos.

Los modelos de Gemini a veces devuelven errores temporales (503 "high demand",
429 con cupo agotado por unos segundos, etc.). Para no depender de que la
persona vuelva a hacer clic manualmente, cada llamada reintenta automáticamente
con espera creciente y, si el modelo principal sigue sin responder, prueba una
vez con un modelo de respaldo (GEMINI_MODEL_*_FALLBACK).
"""

import os
import time

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from schema import PerfilCargo, REQUISITOS_FILAS

MODEL_MULTIMODAL = os.environ.get("GEMINI_MODEL_MULTIMODAL", "gemini-3.7-flash")
MODEL_TEXT = os.environ.get("GEMINI_MODEL_TEXT", "gemini-3.7-flash")

# Modelo(s) de respaldo si el principal está saturado (503) o sin cupo (429).
FALLBACK_MODEL_MULTIMODAL = os.environ.get("GEMINI_MODEL_MULTIMODAL_FALLBACK", "gemini-2.5-flash")
FALLBACK_MODEL_TEXT = os.environ.get("GEMINI_MODEL_TEXT_FALLBACK", "gemini-2.5-flash")

# Códigos de error que vale la pena reintentar (problemas temporales del
# servidor de Gemini o cupo agotado por ráfaga), no errores de configuración.
RETRYABLE_CODES = {429, 500, 502, 503, 504}
MAX_INTENTOS_POR_MODELO = 3
ESPERA_BASE_SEGUNDOS = 4  # 4s, 8s, 16s...


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta la variable de entorno GEMINI_API_KEY en el servidor. "
            "Configúrala en Render (Environment) con la API key del equipo."
        )
    return genai.Client(api_key=api_key)


def _generate_with_retry(client, model, fallback_model, contents, config=None):
    """Llama a generate_content reintentando ante errores temporales, y si el
    modelo principal sigue fallando, prueba una vez con el modelo de respaldo."""
    modelos = [model] if model == fallback_model else [model, fallback_model]
    ultimo_error = None

    for i, m in enumerate(modelos):
        for intento in range(MAX_INTENTOS_POR_MODELO):
            try:
                kwargs = {"model": m, "contents": contents}
                if config is not None:
                    kwargs["config"] = config
                return client.models.generate_content(**kwargs)
            except genai_errors.APIError as e:
                ultimo_error = e
                es_reintentable = getattr(e, "code", None) in RETRYABLE_CODES
                es_ultimo_intento = intento == MAX_INTENTOS_POR_MODELO - 1
                if es_reintentable and not es_ultimo_intento:
                    time.sleep(ESPERA_BASE_SEGUNDOS * (2 ** intento))
                    continue
                break  # pasa al modelo de respaldo (si queda alguno)

    detalle = getattr(ultimo_error, "message", None) or str(ultimo_error)
    raise RuntimeError(
        "Gemini no pudo procesar la solicitud después de varios intentos "
        f"(probamos: {', '.join(modelos)}). Esto suele ser temporal (alta demanda "
        f"del modelo) — intenta de nuevo en uno o dos minutos. Detalle: {detalle}"
    )


def transcribe_audio(file_path: str, mime_type: str) -> str:
    """Sube y transcribe una grabación de reunión con un cliente."""
    client = _get_client()
    uploaded = client.files.upload(file=file_path, config={"mime_type": mime_type})

    prompt = (
        "Esto es la grabación de una reunión de levantamiento de perfil de cargo entre un/a "
        "consultor/a de reclutamiento y un/a cliente. Transcribe COMPLETO el audio en español, "
        "de la manera más fiel posible. Si logras distinguir distintos hablantes, indícalos como "
        "'Consultor/a:' y 'Cliente:' (o por nombre si se menciona). No resumas ni omitas "
        "contenido, incluso si hay silencios, muletillas o partes poco claras (en ese caso escribe "
        "'[inaudible]'). Devuelve solo la transcripción, sin comentarios adicionales."
    )

    response = _generate_with_retry(
        client, MODEL_MULTIMODAL, FALLBACK_MODEL_MULTIMODAL, [uploaded, prompt]
    )
    return response.text


def transcribe_image(file_path: str, mime_type: str) -> str:
    """Transcribe una foto de una hoja con notas (manuscritas o impresas)."""
    client = _get_client()
    uploaded = client.files.upload(file=file_path, config={"mime_type": mime_type})

    prompt = (
        "Esta imagen es una foto de una hoja con notas tomadas durante una reunión de "
        "levantamiento de perfil de cargo con un cliente. El texto puede estar manuscrito o "
        "impreso, y puede incluir letra poco clara, abreviaciones, flechas o viñetas. Transcribe "
        "TODO el texto visible en español, respetando en lo posible el orden y la estructura "
        "(títulos, viñetas, columnas) tal como aparecen en la hoja. Si una palabra es realmente "
        "ilegible, escribe '[ilegible]' en su lugar en vez de inventar contenido. Devuelve solo "
        "la transcripción, sin comentarios adicionales."
    )

    response = _generate_with_retry(
        client, MODEL_MULTIMODAL, FALLBACK_MODEL_MULTIMODAL, [uploaded, prompt]
    )
    return response.text


def structure_profile(raw_text: str, empresa: str = "", cargo: str = "") -> dict:
    """Estructura un texto en bruto (transcripción o notas) en el esquema PerfilCargo."""
    client = _get_client()

    contexto = ""
    if empresa:
        contexto += f"Nombre de la empresa cliente: {empresa}\n"
    if cargo:
        contexto += f"Cargo a buscar (si se conoce de antemano): {cargo}\n"

    filas = ", ".join(REQUISITOS_FILAS)

    prompt = f"""Eres un/a consultor/a senior de reclutamiento (executive search) redactando un
"Perfil de Cargo" a partir de las notas o transcripción de una reunión de levantamiento con un
cliente. Tu tarea es leer el siguiente contenido y estructurarlo en el formato JSON solicitado.

{contexto}
Contenido de la reunión (transcripción de audio, OCR de notas manuscritas, o texto escrito
directamente):
---
{raw_text}
---

Instrucciones:
- Escribe en español formal de Chile, con el tono de un documento corporativo de consultoría
  (como el que usaría una consultora de headhunting para presentar un perfil a sus propios
  consultores). No uses markdown ni viñetas con símbolos "-" o "*"; usa prosa clara y directa,
  salvo en "funciones_cargo" donde cada elemento de la lista es una función individual.
- Sintetiza y ordena la información aunque en la reunión haya sido mencionada de forma
  desordenada o coloquial; no transcribas literal, redacta profesionalmente.
- NO inventes datos que no se mencionaron. Si un campo no fue mencionado en el contenido,
  dilo explícitamente con una frase como "Por definir" o "No mencionado en la reunión", según
  corresponda al campo — nunca lo dejes vacío ni inventes cifras, nombres o condiciones.
- En "requisitos" incluye exactamente estas 6 filas, en este orden: {filas}.
- En "competencias" propone entre 5 y 9 competencias relevantes para el cargo, basadas en lo
  conversado (funciones, contexto, tipo de industria, desafíos mencionados).
- En "funciones_cargo" cada función debe partir con un verbo en infinitivo (ej. "Controlar...",
  "Diseñar...", "Coordinar...").
"""

    response = _generate_with_retry(
        client,
        MODEL_TEXT,
        FALLBACK_MODEL_TEXT,
        prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PerfilCargo,
            temperature=0.3,
        ),
    )

    if response.parsed is not None:
        return response.parsed.model_dump()

    # Fallback por si el parseo automático falla: intentar cargar el texto crudo.
    import json

    return json.loads(response.text)
