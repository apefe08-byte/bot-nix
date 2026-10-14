"""
Bot Nix 🐴🏈 — anuncia en Telegram los nuevos episodios del podcast
y los nuevos artículos del blog de Los Indies de la NFL.

Se ejecuta cada X minutos (GitHub Actions). Lee los feeds RSS, compara
con lo ya anunciado (state.json) y publica lo nuevo en el grupo.

Uso:
  python bot_nix.py            -> ejecución normal
  python bot_nix.py --test     -> manda el último episodio y el último artículo
                                  (para probar, sin tocar el estado)
  python bot_nix.py --dry-run  -> no envía nada, solo muestra qué enviaría
"""

import html
import json
import os
import random
import re
import sys
from pathlib import Path

import feedparser
import requests

from mensajes import mensaje_blog, mensaje_podcast

# ---------------------------------------------------------------- config
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
THREAD_ID = os.environ.get("TELEGRAM_THREAD_ID", "")  # opcional: tema del grupo

PODCAST_RSS = os.environ.get("PODCAST_RSS") or "https://anchor.fm/s/fa9420b4/podcast/rss"
BLOG_RSS = os.environ.get("BLOG_RSS") or "https://indiesnfl.es/feed/"
SPOTIFY_URL = (
    os.environ.get("SPOTIFY_URL") or "https://open.spotify.com/show/60ikh8mQVTQuX9bRH3cWE3"
)
APPLE_URL = os.environ.get("APPLE_URL", "")

STATE_FILE = Path(__file__).with_name("state.json")
MAX_POR_EJECUCION = 3  # tope de avisos por feed y ejecución, por si acaso
GUIDS_GUARDADOS = 200  # cuántos IDs recordar por feed

DRY_RUN = "--dry-run" in sys.argv or os.environ.get("DRY_RUN") == "1"
TEST = "--test" in sys.argv

API = f"https://api.telegram.org/bot{TOKEN}"


# ---------------------------------------------------------------- estado
def cargar_estado() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def guardar_estado(estado: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------- utilidades
def id_entrada(e) -> str:
    return e.get("id") or e.get("guid") or e.get("link") or e.get("title", "")


def limpiar_html(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = html.unescape(texto)
    texto = texto.replace("[…]", "").replace("[&#8230;]", "")
    return re.sub(r"\s+", " ", texto).strip()


def recortar(texto: str, n: int = 220) -> str:
    if len(texto) <= n:
        return texto
    corte = texto[:n].rsplit(" ", 1)[0]
    return corte.rstrip(",.;:") + "…"


def imagen_podcast(e, feed) -> str | None:
    # portada del episodio (itunes:image) o, si no, la del podcast
    if e.get("image") and e["image"].get("href"):
        return e["image"]["href"]
    for m in e.get("media_content", []) + e.get("media_thumbnail", []):
        if m.get("url"):
            return m["url"]
    img = feed.feed.get("image", {})
    return img.get("href") or img.get("url")


def imagen_blog(e) -> str | None:
    # primera imagen del artículo (WordPress la mete en content:encoded)
    contenido = ""
    if e.get("content"):
        contenido = e["content"][0].get("value", "")
    contenido = contenido or e.get("summary", "")
    m = re.search(r'data-orig-file="([^"]+)"', contenido) or re.search(
        r'<img[^>]+src="([^"]+)"', contenido
    )
    return html.unescape(m.group(1)) if m else None


# ---------------------------------------------------------------- telegram
def enviar(texto: str, imagen: str | None, botones: list[list[dict]]) -> bool:
    if DRY_RUN:
        print("---- [DRY RUN] ----")
        print(texto)
        print("imagen:", imagen)
        print("botones:", botones)
        return True

    base = {"chat_id": CHAT_ID, "parse_mode": "HTML"}
    if THREAD_ID:
        base["message_thread_id"] = int(THREAD_ID)
    if botones:
        base["reply_markup"] = json.dumps({"inline_keyboard": botones})

    # con foto (el pie de foto admite 1024 caracteres)
    if imagen and len(texto) <= 1024:
        r = requests.post(
            f"{API}/sendPhoto", data={**base, "photo": imagen, "caption": texto}, timeout=30
        )
        if r.ok:
            return True
        print("No se pudo enviar con foto, pruebo sin ella:", r.text)

    r = requests.post(
        f"{API}/sendMessage",
        data={**base, "text": texto, "disable_web_page_preview": False},
        timeout=30,
    )
    if not r.ok:
        print("Error de Telegram:", r.text)
    return r.ok


# ---------------------------------------------------------------- feeds
def procesar(nombre: str, url: str, estado: dict, construir) -> None:
    if not url:
        print(f"[{nombre}] sin URL configurada, lo salto")
        return

    feed = feedparser.parse(url, agent="BotNix/1.0 (+https://indiesnfl.es)")
    if feed.bozo and not feed.entries:
        print(f"[{nombre}] no se pudo leer el feed: {feed.bozo_exception}")
        return

    entradas = list(feed.entries)

    if TEST:
        if entradas:
            texto, imagen, botones = construir(entradas[0], feed)
            enviar(texto, imagen, botones)
        return

    vistos = estado.get(nombre)

    # primera vez: lo marcamos todo como visto para no inundar el grupo
    if vistos is None:
        estado[nombre] = [id_entrada(e) for e in entradas][:GUIDS_GUARDADOS]
        print(f"[{nombre}] primera ejecución: {len(entradas)} entradas marcadas como vistas")
        return

    nuevas = [e for e in entradas if id_entrada(e) not in vistos]
    nuevas.reverse()  # de la más antigua a la más reciente
    for e in nuevas[:MAX_POR_EJECUCION]:
        texto, imagen, botones = construir(e, feed)
        if enviar(texto, imagen, botones):
            vistos.insert(0, id_entrada(e))
            print(f"[{nombre}] anunciado: {e.get('title')}")
    estado[nombre] = vistos[:GUIDS_GUARDADOS]


def construir_podcast(e, feed):
    titulo = e.get("title", "Nuevo episodio")
    resumen = recortar(limpiar_html(e.get("summary", "")))
    texto = mensaje_podcast(html.escape(titulo), html.escape(resumen))
    botones = []
    fila = []
    if SPOTIFY_URL:
        fila.append({"text": "🎧 Spotify", "url": SPOTIFY_URL})
    if APPLE_URL:
        fila.append({"text": "🍎 Apple Podcasts", "url": APPLE_URL})
    if fila:
        botones.append(fila)
    if e.get("link") and not fila:
        botones.append([{"text": "🎧 Escuchar", "url": e["link"]}])
    return texto, imagen_podcast(e, feed), botones


def construir_blog(e, feed):
    titulo = e.get("title", "Nuevo artículo")
    resumen = recortar(limpiar_html(e.get("summary", "")))
    categorias = [t.get("term", "") for t in e.get("tags", [])]
    texto = mensaje_blog(html.escape(titulo), html.escape(resumen), categorias)
    botones = [[{"text": "📖 Leer en la web", "url": e.get("link", "https://indiesnfl.es")}]]
    return texto, imagen_blog(e), botones


def main() -> None:
    if not DRY_RUN and (not TOKEN or not CHAT_ID):
        sys.exit("Faltan TELEGRAM_TOKEN y/o TELEGRAM_CHAT_ID")

    estado = cargar_estado()
    procesar("podcast", PODCAST_RSS, estado, construir_podcast)
    procesar("blog", BLOG_RSS, estado, construir_blog)
    if not TEST:
        guardar_estado(estado)


if __name__ == "__main__":
    random.seed()
    main()
