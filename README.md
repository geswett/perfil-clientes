# Levantamiento de Perfiles de Cargo — Puelche

Herramienta web interna para levantar Perfiles de Cargo a partir de reuniones con clientes,
de dos formas:

1. **Audio** — sube la grabación de la reunión y se transcribe automáticamente con Gemini.
2. **Foto o texto** — sube una foto de notas manuscritas/impresas (se hace OCR con Gemini) o
   escribe directamente el texto.

En ambos casos, Gemini estructura el contenido en el formato estándar de Perfil de Cargo de
Puelche (Datos Generales Empresa, Organigrama, Descripción del Cargo, Requisitos, Perfil
Candidato, Competencias y Condiciones Laborales). Puedes revisar y editar todo antes de
descargar el documento Word final.

## 1. Cómo desplegarlo en Render (recomendado, sin usar la terminal)

### Paso 1 — Sube este proyecto a GitHub

1. Crea un repositorio nuevo en tu cuenta de GitHub (puede ser privado), por ejemplo
   `perfilador-clientes-puelche`.
2. Sube todos los archivos de esta carpeta a ese repositorio. La forma más simple: en la página
   del repo recién creado, usa "uploading an existing file" y arrastra todos los archivos y
   carpetas (`app.py`, `gemini_service.py`, `docx_generator.py`, `schema.py`, `templates/`,
   `static/`, `assets/`, `requirements.txt`, `Procfile`, `render.yaml`, etc.).

### Paso 2 — Consigue tu API key de Gemini

Ve a https://aistudio.google.com/apikey, inicia sesión con la cuenta de Google que va a usar el
equipo, y crea una API key (botón "Create API key"). Guárdala, la vas a necesitar en el paso
siguiente.

### Paso 3 — Crea el servicio en Render

1. Entra a https://dashboard.render.com y crea una cuenta (puedes usar tu cuenta de GitHub para
   iniciar sesión).
2. Haz clic en **New +** → **Blueprint**, y selecciona el repositorio que acabas de crear. Render
   va a detectar automáticamente el archivo `render.yaml` incluido en este proyecto y va a
   proponer crear el servicio web con la configuración correcta.
3. Cuando te pida la variable `GEMINI_API_KEY`, pega la API key que obtuviste en el paso 2.
4. Confirma y espera a que termine el despliegue (unos minutos). Render te va a dar una URL
   pública del tipo `https://perfilador-clientes-puelche.onrender.com` — esa es la URL que
   comparten con el equipo.

Si prefieres no usar Blueprint, también puedes crear el servicio manualmente: **New + → Web
Service**, conecta el repo, y configura:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app --timeout 600 --workers 2 --threads 4`
- Variable de entorno `GEMINI_API_KEY` con tu API key.

### Actualizaciones futuras

Cada vez que subas cambios al repositorio de GitHub (por ejemplo, si le pides a Claude que
ajuste algo de la plantilla), Render vuelve a desplegar automáticamente la nueva versión.

## 2. Cómo correrlo en tu computador (opcional, para probar antes de desplegar)

```bash
python3 -m venv venv
source venv/bin/activate       # en Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # y pega tu GEMINI_API_KEY dentro de .env
export $(cat .env | xargs)     # en Windows usa otra forma de cargar variables de entorno
python app.py
```

Abre http://localhost:5000 en el navegador.

## 3. Notas importantes

- **Costos**: cada transcripción de audio/foto y cada estructuración del perfil consume la API
  de Gemini de la cuenta cuya key configuraste. Revisa el uso y límites en
  https://aistudio.google.com/.
- **Privacidad**: los audios y fotos que suban se envían a la API de Gemini para su
  procesamiento (Google), y el archivo temporal se borra del servidor después de procesarse.
  No se guarda ningún historial de perfiles en el servidor — cada sesión es independiente y el
  Word se descarga directo al computador de quien lo generó.
- **Audios muy largos**: si una grabación es muy larga (más de ~1 hora) y el procesamiento
  demora demasiado, es posible que el servidor de Render corte la conexión antes de que termine.
  Si esto pasa seguido, dímelo y ajustamos la arquitectura (por ejemplo, procesar en segundo
  plano y avisar cuando esté listo) en vez de esperar la respuesta en la misma conexión.
- **Plantilla del Word**: el diseño del documento generado (títulos numerados en gris, tablas
  con encabezado verde claro, logo de Puelche) está en `docx_generator.py`. Si cambia el formato
  oficial de Puelche, se ajusta ahí.
- Este proyecto usa el modelo `gemini-2.5-pro` para transcripción y estructuración. Se puede
  cambiar con las variables de entorno `GEMINI_MODEL_MULTIMODAL` y `GEMINI_MODEL_TEXT` en Render
  (por ejemplo, a un modelo más rápido/económico si el volumen de uso lo justifica).
