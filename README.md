# Levantamiento de Perfiles de Cargo — Puelche

Herramienta web interna para levantar Perfiles de Cargo a partir de reuniones con clientes,
de tres formas:

1. **Transcripción de la reunión** — pega el texto o sube el archivo (.txt/.docx) de una
   transcripción ya hecha con otra herramienta (Zoom, Meet, la app de Gemini, Otter, etc.).
   Esta app **no** graba ni transcribe audio — solo toma una transcripción que ya tengas.
2. **Foto de notas** — sube una foto de una hoja con notas manuscritas o impresas; se hace OCR
   automáticamente.
3. **Texto escrito** — escribe o pega directamente las notas de la reunión.

En los tres casos, **Claude (API de Anthropic)** estructura el contenido en el formato estándar
de Perfil de Cargo de Puelche (Datos Generales Empresa, Organigrama, Descripción del Cargo,
Requisitos, Perfil Candidato, Competencias y Condiciones Laborales). Puedes revisar y editar
todo antes de descargar el documento Word final. **No se usa ninguna API de Google/Gemini.**

## 1. Cómo desplegarlo en Render (recomendado, sin usar la terminal)

### Paso 1 — Sube este proyecto a GitHub

1. Crea un repositorio nuevo en tu cuenta de GitHub (puede ser privado), por ejemplo
   `perfilador-clientes-puelche`.
2. Sube todos los archivos de esta carpeta a ese repositorio. La forma más simple: en la página
   del repo recién creado, usa "uploading an existing file" y arrastra todos los archivos y
   carpetas (`app.py`, `claude_service.py`, `docx_generator.py`, `schema.py`, `templates/`,
   `static/`, `assets/`, `requirements.txt`, `Procfile`, `render.yaml`, etc.).

### Paso 2 — Consigue tu API key de Anthropic

1. Ve a https://console.anthropic.com y crea una cuenta (o inicia sesión) con la cuenta que va a
   usar el equipo para esto — idealmente una cuenta corporativa dedicada, ya que esta key queda
   corriendo en el servidor.
2. **Importante**: esta cuenta de la Consola de Anthropic (con facturación propia, por uso) es
   distinta de la cuenta de Claude/Cowork con la que hablas normalmente. Vas a necesitar agregar
   un método de pago ahí (funciona por uso, como la mayoría de las APIs de IA — no es una
   suscripción mensual fija).
3. Ve a **API Keys** en el menú y crea una key nueva ("Create Key"). Cópiala y guárdala — la vas
   a necesitar en el paso siguiente.

### Paso 3 — Crea el servicio en Render

1. Entra a https://dashboard.render.com y crea una cuenta (puedes usar tu cuenta de GitHub para
   iniciar sesión).
2. Haz clic en **New +** → **Blueprint**, y selecciona el repositorio que acabas de crear. Render
   va a detectar automáticamente el archivo `render.yaml` incluido en este proyecto y va a
   proponer crear el servicio web con la configuración correcta.
3. Cuando te pida la variable `ANTHROPIC_API_KEY`, pega la API key que obtuviste en el paso 2.
4. Confirma y espera a que termine el despliegue (unos minutos). Render te va a dar una URL
   pública del tipo `https://perfilador-clientes-puelche.onrender.com` — esa es la URL que
   comparten con el equipo.

Si prefieres no usar Blueprint, también puedes crear el servicio manualmente: **New + → Web
Service**, conecta el repo, y configura:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app --timeout 600 --workers 2 --threads 4`
- Variable de entorno `ANTHROPIC_API_KEY` con tu API key.
- Plan: **Free** (así no te pide tarjeta de crédito de Render — la tarjeta que sí necesitas es
  la de la cuenta de Anthropic, para la API).

**Sobre el plan gratuito de Render**: `render.yaml` usa el plan **Free**, que no requiere
tarjeta de crédito en Render. La única limitación es que si nadie usa la herramienta durante 15
minutos seguidos, el servicio "se duerme" y la primera solicitud después de eso tarda cerca de 1
minuto en responder (las siguientes son normales). Si más adelante el equipo la usa muy seguido
y esa espera molesta, se puede subir al plan Starter (~USD 7/mes) cambiando el plan directamente
en Render — Settings del servicio → Instance Type.

### Actualizaciones futuras

Cada vez que subas cambios al repositorio de GitHub (por ejemplo, si le pides a Claude que
ajuste algo de la plantilla), Render vuelve a desplegar automáticamente la nueva versión.

## 2. Cómo correrlo en tu computador (opcional, para probar antes de desplegar)

```bash
python3 -m venv venv
source venv/bin/activate       # en Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # y pega tu ANTHROPIC_API_KEY dentro de .env
export $(cat .env | xargs)     # en Windows usa otra forma de cargar variables de entorno
python app.py
```

Abre http://localhost:5000 en el navegador.

## 3. Notas importantes

- **Costos**: cada foto procesada (OCR) y cada estructuración de un perfil consume la API de
  Anthropic de la cuenta cuya key configuraste — se cobra por uso (tokens), no es un plan fijo.
  Revisa tu uso y límites en https://console.anthropic.com/settings/usage. Esto es independiente
  de cualquier suscripción de Claude/Cowork que el equipo use para chatear — son sistemas de
  facturación separados.
- **Ya no se usa Gemini ni se sube/transcribe audio automáticamente**: la pestaña "Transcripción
  de la reunión" espera que la transcripción ya venga hecha (pegada como texto, o en un archivo
  .txt/.docx) — por ejemplo, generada con la app de Gemini, Zoom, Meet, Otter, etc. por fuera de
  esta herramienta. La app solo toma ese texto y arma el Perfil de Cargo con Claude.
- **Errores temporales de Claude (saturación, error 529/429)**: pueden pasar en horas de alta
  demanda. La app ya reintenta automáticamente (el SDK de Anthropic reintenta solo unas veces) y,
  si el modelo principal sigue sin responder, prueba una vez con un modelo de respaldo más rápido
  (`CLAUDE_MODEL_TEXT_FALLBACK` / `CLAUDE_MODEL_VISION_FALLBACK`, por defecto
  `claude-haiku-4-5-20251001`). Si aun así falla, generalmente basta con esperar un minuto y
  volver a intentar.
- **Privacidad**: las fotos y transcripciones que suban se envían a la API de Anthropic para su
  procesamiento, y el archivo temporal se borra del servidor después de procesarse. No se guarda
  ningún historial de perfiles en el servidor — cada sesión es independiente y el Word se
  descarga directo al computador de quien lo generó.
- **Formatos de imagen soportados**: jpg, png, webp, gif (Claude no acepta HEIC directamente —
  si alguien sube una foto HEIC de iPhone, hay que convertirla a jpg/png antes, por ejemplo
  compartiéndola por WhatsApp o exportándola como "Más compatible" desde el iPhone).
- **Plantilla del Word**: el diseño del documento generado (títulos numerados en gris, tablas
  con encabezado verde claro, logo de Puelche) está en `docx_generator.py`. Si cambia el formato
  oficial de Puelche, se ajusta ahí.
- Este proyecto usa el modelo `claude-sonnet-5` para OCR y estructuración. Se puede cambiar con
  las variables de entorno `CLAUDE_MODEL_TEXT` y `CLAUDE_MODEL_VISION` en Render (por ejemplo, a
  un modelo más económico como `claude-haiku-4-5-20251001` si el volumen de uso lo justifica).
