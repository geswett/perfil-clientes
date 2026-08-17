import os
import tempfile
import traceback

from flask import Flask, request, jsonify, render_template, send_file

import gemini_service
from docx_generator import generar_docx

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024  # 300 MB (audios largos)

ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".aiff", ".webm", ".mp4"}
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}

MIME_BY_EXT = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aiff": "audio/aiff",
    ".webm": "audio/webm",
    ".mp4": "audio/mp4",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


@app.route("/api/procesar", methods=["POST"])
def procesar():
    """Recibe audio, imagen o texto y devuelve el Perfil de Cargo estructurado."""
    modo = request.form.get("modo")
    empresa = request.form.get("empresa", "").strip()
    cargo = request.form.get("cargo", "").strip()

    if modo not in ("audio", "imagen", "texto"):
        return jsonify({"error": "Modo inválido. Debe ser 'audio', 'imagen' o 'texto'."}), 400

    tmp_path = None
    try:
        if modo == "texto":
            raw_text = request.form.get("texto", "").strip()
            if not raw_text:
                return jsonify({"error": "No se recibió texto para procesar."}), 400

        else:
            archivo = request.files.get("archivo")
            if not archivo or archivo.filename == "":
                return jsonify({"error": "No se recibió ningún archivo."}), 400

            ext = os.path.splitext(archivo.filename)[1].lower()
            allowed = ALLOWED_AUDIO_EXT if modo == "audio" else ALLOWED_IMAGE_EXT
            if ext not in allowed:
                return jsonify({
                    "error": f"Formato '{ext}' no soportado para {modo}. "
                             f"Formatos permitidos: {', '.join(sorted(allowed))}"
                }), 400

            mime_type = MIME_BY_EXT.get(ext, "application/octet-stream")

            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                archivo.save(tmp.name)
                tmp_path = tmp.name

            if modo == "audio":
                raw_text = gemini_service.transcribe_audio(tmp_path, mime_type)
            else:
                raw_text = gemini_service.transcribe_image(tmp_path, mime_type)

        perfil = gemini_service.structure_profile(raw_text, empresa=empresa, cargo=cargo)

        return jsonify({
            "transcripcion": raw_text,
            "perfil": perfil,
        })

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Ocurrió un error procesando la solicitud: {e}"}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.route("/api/generar-docx", methods=["POST"])
def api_generar_docx():
    """Recibe el perfil (ya revisado/editado por el usuario) y devuelve el .docx."""
    data = request.get_json(force=True, silent=True) or {}
    perfil = data.get("perfil")
    empresa = data.get("empresa", "")
    cargo = data.get("cargo", "")
    consultor = data.get("consultor", "")

    if not perfil:
        return jsonify({"error": "Falta el perfil a exportar."}), 400

    try:
        contenido, filename = generar_docx(perfil, empresa, cargo, consultor)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"No se pudo generar el documento: {e}"}), 500

    import io
    return send_file(
        io.BytesIO(contenido),
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
