"""
Bot Nix - la jornada del domingo con horario de España 🗓️
Los domingos por la mañana publica todos los partidos del día en hora española,
agrupados por franja, y añade el Monday Night del lunes.

Lo llama bot_nix.py en cada ejecución. Solo envía una vez, la primera vez que
se ejecute un domingo entre HORA_INICIO y HORA_FIN (hora de Madrid).

Probar a mano:
  python jornada.py --ver 2026-10-25   -> muestra el mensaje de ese domingo (sin enviar)
"""

import html
import random
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

MADRID = ZoneInfo("Europe/Madrid")
HORA_INICIO = 10  # a partir de las 10:00
HORA_FIN = 13     # si a las 13:00 no ha salido, ya no sale

ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

BANDERAS = {
    "spain": "🇪🇸", "españa": "🇪🇸", "france": "🇫🇷", "germany": "🇩🇪",
    "england": "🇬🇧", "united kingdom": "🇬🇧", "uk": "🇬🇧", "ireland": "🇮🇪",
    "mexico": "🇲🇽", "méxico": "🇲🇽", "brazil": "🇧🇷", "australia": "🇦🇺",
    "canada": "🇨🇦",
}

APERTURAS = [
    "☀️ <b>¡Buenos días, Indies! Hoy es domingo de NFL.</b> Bot Nix os trae el menú:",
    "🗓️ <b>Domingo sagrado.</b> Cancelad planes, cargad el sofá y apuntad horarios:",
    "🐴 Bot Nix ha preparado la <b>hoja de partidos</b> del domingo. En hora española, que aquí no somos de Kansas:",
    "📺 <b>Mando a mano y nachos a punto.</b> Esto es lo que hay hoy:",
    "🏈 <b>Huddle dominical:</b> estos son los partidos de hoy, en horario de España:",
]

CIERRES = [
    "Que gane vuestro equipo… o al menos que no os arruine el fantasy 🙏",
    "Comentad aquí la jornada. Y mañana a primera hora, ¡spoilers tapados! 🙈",
    "Bot Nix se pone la camiseta. ¿Y vosotros? 🏈",
    "Hidratación, paciencia y fe en vuestro QB. ¡Feliz domingo! 🍻",
]


def consultar(fecha_usa: str) -> dict | None:
    try:
        r = requests.get(ESPN, params={"dates": fecha_usa}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        print(f"[jornada] no pude consultar ESPN ({fecha_usa}): {exc}")
        return None


def partido(evento: dict) -> dict:
    comp = (evento.get("competitions") or [{}])[0]
    equipos = {c.get("homeAway"): c.get("team", {}) for c in comp.get("competitors", [])}
    local = equipos.get("home", {}).get("shortDisplayName", "?")
    visit = equipos.get("away", {}).get("shortDisplayName", "?")
    neutral = comp.get("neutralSite", False)

    pais = (comp.get("venue", {}).get("address", {}).get("country") or "").strip()
    ciudad = (comp.get("venue", {}).get("address", {}).get("city") or "").strip()
    internacional = pais and pais.lower() not in ("usa", "united states", "us")

    hora = datetime.fromisoformat(evento["date"].replace("Z", "+00:00")).astimezone(MADRID)
    return {
        "hora": hora,
        "texto": f"{visit} {'vs' if neutral else '@'} {local}",
        "extra": f" {BANDERAS.get(pais.lower(), '🌍')} <i>{html.escape(ciudad)}</i>" if internacional else "",
    }


def fecha_bonita(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"


def mensaje(domingo: date, datos_dom: dict, datos_lun: dict | None) -> str | None:
    partidos = sorted((partido(e) for e in datos_dom.get("events", [])), key=lambda p: p["hora"])
    if not partidos:
        return None

    semana = (datos_dom.get("week") or {}).get("number")
    cab = f"🏈 <b>Jornada NFL · {fecha_bonita(domingo).capitalize()}"
    cab += f" · Semana {semana}</b>" if semana else "</b>"

    partes = [random.choice(APERTURAS), "", cab]

    # agrupar por franja horaria
    franjas: dict[datetime, list[dict]] = {}
    for p in partidos:
        franjas.setdefault(p["hora"], []).append(p)

    for hora, lista in franjas.items():
        icono = "🌙" if hora.date() > domingo else "⏰"
        etiqueta = f"{hora:%H:%M}"
        if hora.date() > domingo:
            etiqueta += " (madrugada del lunes)"
        partes += ["", f"{icono} <b>{etiqueta}</b>"]
        for p in lista:
            partes.append(f"• {html.escape(p['texto'])}{p['extra']}")

    # Monday Night (solo lo que se juega el lunes, hora de EE. UU.)
    if datos_lun:
        lunes = sorted((partido(e) for e in datos_lun.get("events", [])), key=lambda p: p["hora"])
        if lunes:
            partes += ["", "📅 <b>Y el Monday Night</b> (madrugada del martes):"]
            for p in lunes:
                partes.append(f"• {p['hora']:%H:%M} · {html.escape(p['texto'])}{p['extra']}")

    partes += ["", random.choice(CIERRES)]
    return "\n".join(partes)


def preparar(estado: dict, ahora: datetime | None = None) -> str | None:
    """Devuelve el mensaje si toca enviarlo ahora; si no, None."""
    ahora = ahora or datetime.now(MADRID)
    hoy = ahora.date()
    if hoy.weekday() != 6:  # solo domingos
        return None
    if estado.get("jornada_ultimo") == hoy.isoformat():
        return None
    if not (HORA_INICIO <= ahora.hour < HORA_FIN):
        return None

    datos_dom = consultar(hoy.strftime("%Y%m%d"))
    if not datos_dom:
        return None
    datos_lun = consultar((hoy + timedelta(days=1)).strftime("%Y%m%d"))
    return mensaje(hoy, datos_dom, datos_lun)


if __name__ == "__main__":
    if "--ver" in sys.argv:
        idx = sys.argv.index("--ver")
        d = date.fromisoformat(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else date.today()
        dom = consultar(d.strftime("%Y%m%d"))
        lun = consultar((d + timedelta(days=1)).strftime("%Y%m%d"))
        print(mensaje(d, dom or {}, lun) or "No hay partidos ese día")
