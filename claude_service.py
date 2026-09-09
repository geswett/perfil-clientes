"""Funciones que hablan con la API de Anthropic (Claude):

1. transcribe_image()   -> transcribe una foto de una hoja (manuscrita o impresa) a texto.
2. extract_pdf_text()   -> extrae/transcribe el texto de un PDF (incluye PDFs escaneados).
3. structure_profile()  -> toma el texto en bruto (transcripción subida, OCR de una foto,
   texto de un PDF, o texto escrito en computador) y lo estructura en el esquema PerfilCargo
   definido en schema.py.

Ya NO se usa la API de Gemini en ningún punto de la aplicación. El audio de la reunión ya no
se sube ni se transcribe automáticamente: se espera que la transcripción venga hecha de antes,
subida como archivo (.doc, .docx, .pdf o .txt) — ver la función extraer_texto_de_archivo() en
app.py.

El modelo se puede ajustar con las variables de entorno CLAUDE_MODEL_TEXT (para estructurar
el perfil) y CLAUDE_MODEL_VISION (para leer fotos). Por defecto se usa claude-sonnet-5 en
ambos casos, con claude-haiku-4-5-20251001 como respaldo si el modelo principal está saturado.
"""

import base64
import io
import os

import anthropic
from PIL import Image

from schema import PerfilCargo, REQUISITOS_FILAS

MODEL_TEXT = os.environ.get("CLAUDE_MODEL_TEXT", "claude-sonnet-5")
MODEL_VISION = os.environ.get("CLAUDE_MODEL_VISION", "claude-sonnet-5")

# Modelo de respaldo si el principal está saturado (529) o sin cupo (429).
FALLBACK_MODEL_TEXT = os.environ.get("CLAUDE_MODEL_TEXT_FALLBACK", "claude-haiku-4-5-20251001")
FALLBACK_MODEL_VISION = os.environ.get("CLAUDE_MODEL_VISION_FALLBACK", "claude-haiku-4-5-20251001")

# Códigos de error temporales del lado de Anthropic que vale la pena reintentar con el
# modelo de respaldo (el SDK ya reintenta automáticamente el mismo modelo antes de esto).
RETRYABLE_STATUS = {429, 500, 502, 503, 529}

# Claude solo acepta imágenes en estos formatos.
MEDIA_TYPES_SOPORTADOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}
LADO_MAX_PIXELES = 1568  # recomendado por Anthropic para no perder calidad ni gastar de más


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta la variable de entorno ANTHROPIC_API_KEY en el servidor. "
            "Configúrala en Render (Environment) con una API key de Anthropic "
            "(se obtiene en console.anthropic.com — es distinta de tu cuenta de Claude/Cowork)."
        )
    return anthropic.Anthropic(api_key=api_key, max_retries=4)


def _create_with_fallback(client, model, fallback_model, **kwargs):
    """Llama a messages.create() y, si el modelo principal falla por saturación/cupo
    (después de que el SDK ya reintentó internamente), prueba una vez con el modelo de
    respaldo antes de rendirse."""
    modelos = [model] if model == fallback_model else [model, fallback_model]
    ultimo_error = None

    for m in modelos:
        try:
            return client.messages.create(model=m, **kwargs)
        except anthropic.APIStatusError as e:
            ultimo_error = e
            if e.status_code not in RETRYABLE_STATUS:
                raise RuntimeError(f"Error de la API de Claude ({e.status_code}): {e.message}") from e
            continue  # prueba con el siguiente modelo de la lista

    detalle = getattr(ultimo_error, "message", None) or str(ultimo_error)
    raise RuntimeError(
        "Claude no pudo procesar la solicitud después de varios intentos "
        f"(probamos: {', '.join(modelos)}). Esto suele ser temporal (alta demanda del "
        f"modelo) — intenta de nuevo en uno o dos minutos. Detalle: {detalle}"
    )


def _preparar_imagen(file_path: str, mime_type: str) -> tuple[str, str]:
    """Redimensiona/convierte la imagen si hace falta y la devuelve en base64.

    Devuelve (media_type, base64_data). Convierte a JPEG si el formato original no es uno
    de los que acepta Claude (por ejemplo HEIC de iPhone)."""
    with Image.open(file_path) as img:
        img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
        ancho, alto = img.size
        lado_mayor = max(ancho, alto)
        if lado_mayor > LADO_MAX_PIXELES:
            factor = LADO_MAX_PIXELES / lado_mayor
            img = img.resize((int(ancho * factor), int(alto * factor)))

        buffer = io.BytesIO()
        if mime_type in MEDIA_TYPES_SOPORTADOS and mime_type != "image/gif":
            formato = "JPEG" if mime_type == "image/jpeg" else mime_type.split("/")[1].upper()
            img.save(buffer, format=formato, quality=90)
            media_type = mime_type
        else:
            img.save(buffer, format="JPEG", quality=90)
            media_type = "image/jpeg"

        data = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
        return media_type, data


def transcribe_image(file_path: str, mime_type: str) -> str:
    """Transcribe una foto de una hoja con notas (manuscritas o impresas)."""
    client = _get_client()
    media_type, data = _preparar_imagen(file_path, mime_type)

    prompt = (
        "Esta imagen es una foto de una hoja con notas tomadas durante una reunión de "
        "levantamiento de perfil de cargo con un cliente. El texto puede estar manuscrito o "
        "impreso, y puede incluir letra poco clara, abreviaciones, flechas o viñetas. Transcribe "
        "TODO el texto visible en español, respetando en lo posible el orden y la estructura "
        "(títulos, viñetas, columnas) tal como aparecen en la hoja. Si una palabra es realmente "
        "ilegible, escribe '[ilegible]' en su lugar en vez de inventar contenido. Devuelve solo "
        "la transcripción, sin comentarios adicionales."
    )

    response = _create_with_fallback(
        client,
        MODEL_VISION,
        FALLBACK_MODEL_VISION,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def extract_pdf_text(file_path: str) -> str:
    """Extrae/transcribe el texto completo de un PDF (transcripción, notas escaneadas, etc.).

    Claude lee el PDF directamente como documento (funciona tanto para PDFs con texto real
    como para PDFs escaneados/imágenes, haciendo OCR internamente), así que no hace falta
    ninguna librería extra de por medio."""
    client = _get_client()
    with open(file_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    prompt = (
        "Este PDF contiene la transcripción o notas de una reunión de levantamiento de perfil "
        "de cargo con un cliente. Extrae y transcribe TODO el texto contenido en el documento, "
        "en español, respetando el orden en que aparece. Si el PDF es una imagen escaneada, "
        "transcribe lo que puedas leer con OCR; si alguna parte es realmente ilegible, escribe "
        "'[ilegible]' en su lugar en vez de inventar contenido. Devuelve solo el texto "
        "extraído, sin comentarios adicionales."
    )

    response = _create_with_fallback(
        client,
        MODEL_VISION,
        FALLBACK_MODEL_VISION,
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def structure_profile(raw_text: str, empresa: str = "", cargo: str = "") -> dict:
    """Estructura un texto en bruto (transcripción, OCR de notas, o texto escrito) en el
    esquema PerfilCargo, usando tool use de Claude para forzar una salida JSON válida."""
    client = _get_client()

    contexto = ""
    if empresa:
        contexto += f"Nombre de la empresa cliente: {empresa}\n"
    if cargo:
        contexto += f"Cargo a buscar (si se conoce de antemano): {cargo}\n"

    filas = ", ".join(REQUISITOS_FILAS)

    prompt = f"""Eres un/a consultor/a senior de reclutamiento (executive search) redactando un
"Perfil de Cargo" a partir de las notas o transcripción de una reunión de levantamiento con un
cliente. Tu tarea es leer el siguiente contenido y estructurarlo usando la herramienta
"estructurar_perfil_cargo".

{contexto}
Contenido de la reunión (transcripción de la reunión, OCR de notas manuscritas, o texto escrito
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

    tool = {
        "name": "estructurar_perfil_cargo",
        "description": "Estructura el contenido de la reunión con el cliente en el formato "
                        "de Perfil de Cargo de Puelche.",
        "input_schema": PerfilCargo.model_json_schema(),
    }

    response = _create_with_fallback(
        client,
        MODEL_TEXT,
        FALLBACK_MODEL_TEXT,
        max_tokens=8192,
        tools=[tool],
        tool_choice={"type": "tool", "name": "estructurar_perfil_cargo"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "estructurar_perfil_cargo":
            return block.input

    raise RuntimeError("Claude no devolvió el Perfil de Cargo estructurado esperado.")
