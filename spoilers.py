"""
Bot Nix - aviso anti-spoilers 🙈
La mañana después de una jornada NFL recuerda al grupo que, hasta las 12:00,
los comentarios del partido van con formato spoiler.

Lo llama bot_nix.py en cada ejecución. Solo envía una vez al día, la primera vez
que se ejecute entre HORA_INICIO y HORA_FIN (hora de Madrid), y solo si la noche
anterior (fecha de EE. UU.) hubo partidos de la NFL.

Probar a mano:
  python spoilers.py --ver         -> muestra el mensaje de hoy (sin enviar)
"""

import html
import random
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

MADRID = ZoneInfo("Europe/Madrid")
HORA_INICIO = 7   # a partir de las 7:00
HORA_FIN = 11     # si a las 11:00 no ha salido, ya no sale (no tendría sentido)
HORA_SPOILERS = "12:00"

ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# Si ESPN falla, días en que normalmente toca (0=lunes … 6=domingo):
# viernes (Thursday Night), lunes (domingo) y martes (Monday Night)
DIAS_POR_DEFECTO = {0, 1, 4}

# ------------------------------------------------------------ frases
APERTURAS = [
    "🙈 <b>¡Buenos días, Indies!</b> Anoche hubo football y aquí hay gente que todavía no lo ha visto.",
    "☕ <b>Alerta de spoilers matutina.</b> Bot Nix se ha tomado el café y viene a poner orden.",
    "🚨 <b>Flag por spoiler:</b> 15 yardas y pérdida de down para quien suelte el resultado sin avisar.",
    "🐴 Bot Nix ha madrugado más que un kicker en training camp para recordaros algo importante…",
    "📺 <b>Hay Indies con el partido grabado</b> y el móvil boca abajo. Respetemos su sufrimiento.",
    "🌅 Amanece en Europa, duerme América… y el partido de anoche <b>sigue siendo secreto</b>.",
]

NORMAS = [
    "Hasta las <b>{h}</b>, todo comentario del partido va con <b>formato spoiler</b>.",
    "Hasta las <b>{h}</b>, resultados, jugadas y dramas, siempre <b>tapados con spoiler</b>.",
    "Zona libre de spoilers hasta las <b>{h}</b>: quien comente, que lo tape.",
]

COMO = (
    "<i>Cómo se hace: escribe el mensaje, selecciona el texto y en el menú de formato "
    "elige «Spoiler».</i>"
)

GUINOS = [
    "Ejemplo de buen comportamiento: <tg-spoiler>Bot Nix se durmió en el descanso y tampoco sabe quién ganó</tg-spoiler>",
    "Así se hace: <tg-spoiler>el kicker falló un extra point y Bot Nix lloró</tg-spoiler>",
    "Practicad con este: <tg-spoiler>no hay nada aquí, os la he colado 🐴</tg-spoiler>",
    "Ejemplo homologado: <tg-spoiler>hubo un pick six y Bot Nix gritó en silencio</tg-spoiler>",
]

CIERRES = [
    "A partir de las {h}, barra libre 🍻",
    "A las {h} se levanta la bandera y que empiece el debate 🏈",
    "Quien suelte spoilers sin tapar, castigo: escuchar el Palantir dos veces 😄",
    "Bot Nix vigila. Bot Nix siempre vigila 👀",
]


# ------------------------------------------------------------ lógica
def partidos_de(fecha_usa: str) -> list[str] | None:
    """Lista 'SEA @ DEN' de los partidos de esa fecha (EE. UU.). None si ESPN falla."""
    try:
        r = requests.get(ESPN, params={"dates": fecha_usa}, timeout=20)
        r.raise_for_status()
        eventos = r.json().get("events", [])
        return [e.get("shortName") or e.get("name", "") for e in eventos]
    except Exception as exc:  # noqa: BLE001
        print(f"[spoilers] no pude consultar ESPN: {exc}")
        return None


def mensaje(partidos: list[str] | None) -> str:
    partes = [random.choice(APERTURAS), ""]
    if partidos:
        if len(partidos) <= 3:
            lista = ", ".join(html.escape(p) for p in partidos)
            partes.append(f"🏈 Anoche: <b>{lista}</b>")
        else:
            partes.append(f"🏈 Anoche se jugaron <b>{len(partidos)} partidos</b>.")
        partes.append("")
    partes += [
        random.choice(NORMAS).format(h=HORA_SPOILERS),
        "",
        COMO,
        "",
        random.choice(GUINOS),
        "",
        random.choice(CIERRES).format(h=HORA_SPOILERS),
    ]
    return "\n".join(partes)


def toca_hoy(estado: dict, ahora: datetime | None = None) -> tuple[bool, list[str] | None]:
    """Decide si hay que enviar el aviso ahora. Devuelve (enviar, partidos)."""
    ahora = ahora or datetime.now(MADRID)
    hoy = ahora.date().isoformat()

    if estado.get("spoilers_ultimo") == hoy:
        return False, None  # ya enviado hoy
    if not (HORA_INICIO <= ahora.hour < HORA_FIN):
        return False, None

    ayer_usa = (ahora - timedelta(days=1)).strftime("%Y%m%d")
    partidos = partidos_de(ayer_usa)
    if partidos is None:  # ESPN caído: tiramos de calendario habitual
        return ahora.weekday() in DIAS_POR_DEFECTO, None
    return bool(partidos), partidos


# ------------------------------------------------------------ fin de spoilers
FIN_INICIO = 12   # a partir de las 12:00
FIN_FIN = 14      # si a las 14:00 no ha salido, ya no sale

FIN_APERTURAS = [
    "🔓 <b>¡Ya pasaron las 12:00!</b> Se acabó la ley del silencio.",
    "🏁 <b>Fin de la zona anti-spoilers.</b> Bot Nix levanta la bandera.",
    "📢 <b>¡Barra libre de spoilers!</b> Quien no lo haya visto aún, que silencie el grupo YA.",
    "⏰ <b>Two-minute warning… y tiempo cumplido.</b> Ya se puede hablar del partido sin tapar nada.",
    "🐴 Bot Nix suelta las riendas: <b>spoilers permitidos.</b>",
    "🎉 <b>Mediodía en Europa:</b> el partido de anoche ya es de dominio público.",
]

FIN_INVITACIONES = [
    "¿MVP del partido? ¿Jugada de la noche? ¿Arbitraje de la vergüenza? Todo vuestro.",
    "Resultados, dramas, celebraciones y lloros: el vestuario es vuestro.",
    "Ahora sí: análisis serio, memes o desahogo. Lo que el cuerpo os pida.",
    "Venga, ¿quién ha ganado la apuesta del desayuno?",
]

FIN_CIERRES = [
    "Y quien todavía no lo ha visto… lo sentimos, avisados estabais 😄",
    "Bot Nix se va a echar la siesta. ¡A debatir! 🏈",
    "El micro es vuestro. Que no se diga que los Indies no opinan 🎙️",
    "Recordad: comentar no es lo mismo que sobrerreaccionar. O sí 😏",
]


def mensaje_fin() -> str:
    return "\n".join(
        [
            random.choice(FIN_APERTURAS),
            "",
            random.choice(FIN_INVITACIONES),
            "",
            random.choice(FIN_CIERRES),
        ]
    )


def toca_fin(estado: dict, ahora: datetime | None = None) -> bool:
    """Solo los días en que salió el aviso de la mañana, una vez, entre 12:00 y 14:00."""
    ahora = ahora or datetime.now(MADRID)
    hoy = ahora.date().isoformat()
    return (
        estado.get("spoilers_ultimo") == hoy
        and estado.get("spoilers_fin") != hoy
        and FIN_INICIO <= ahora.hour < FIN_FIN
    )


if __name__ == "__main__":
    if "--ver" in sys.argv:
        ayer = (datetime.now(MADRID) - timedelta(days=1)).strftime("%Y%m%d")
        print(mensaje(partidos_de(ayer)))
