# Bot Nix 🐴🏈

Avisa en el grupo de Telegram de Los Indies de la NFL cuando sale un episodio nuevo del podcast o un artículo nuevo en indiesnfl.es. Corre gratis en GitHub Actions cada 20 minutos.

## Puesta en marcha

### 1. Telegram
1. Habla con **@BotFather** → `/newbot` → nombre `Bot Nix` → usuario `BotNixBot` (o `BotNix_bot`). Guarda el token.
2. Opcional: `/setuserpic` para ponerle foto y `/setdescription` para la bio.
3. Añade el bot al grupo **como administrador** (basta con "enviar mensajes").
4. Saca el **ID del grupo**: añade un momento @RawDataBot al grupo, te responde con el `chat.id` (empieza por `-100…`) y lo expulsas.
5. Si el grupo usa **temas**, apunta el ID del tema donde quieres los avisos (es el número final del enlace a cualquier mensaje de ese tema).

### 2. GitHub
1. Crea un repositorio (puede ser **privado**) y sube todos estos archivos, incluida la carpeta `.github`.
2. *Settings → Secrets and variables → Actions*:
   - **Secrets**: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
   - **Variables** (todas opcionales; el RSS del podcast, el del blog y Spotify ya vienen puestos en el código):
     - `APPLE_URL` → ficha en Apple Podcasts, para añadir su botón
     - `TELEGRAM_THREAD_ID` → solo si usáis temas
     - `PODCAST_RSS`, `BLOG_RSS`, `SPOTIFY_URL` → solo si algún día cambian
3. *Actions → Bot Nix → Run workflow*:
   - `dry-run`: comprueba que lee los feeds, sin enviar nada.
   - `test`: manda al grupo el último episodio y el último artículo.
   - `normal`: la primera vez marca todo lo publicado como "visto" (no inunda el grupo). A partir de ahí solo anuncia lo nuevo.

Listo. Desde ese momento se ejecuta solo cada 20 minutos.

## Personalizar
Todas las frases están en `mensajes.py`: añade, quita o cambia lo que quieras. Hay frases especiales para los episodios con "Ruta 32" o "Campus" en el título y para cada categoría del blog.

## Notas
- GitHub puede retrasar unos minutos las ejecuciones programadas; es normal.
- Si el repositorio pasa 60 días sin ningún cambio, GitHub pausa las tareas programadas. Como Bot Nix guarda un cambio cada vez que anuncia algo, con publicaciones regulares no pasa. Si se pausa, se reactiva desde la pestaña Actions.
