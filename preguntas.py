"""
Bot Nix - llamada semanal a #preguntasindies
Cada martes por la mañana invita al grupo a mandar preguntas para el programa.

Uso:
  python preguntas.py           -> solo envía si en Madrid es la HORA indicada
  python preguntas.py --ahora   -> envía ya (para probar)
"""

import os
import random
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
THREAD_ID = os.environ.get("TELEGRAM_THREAD_ID", "")

HORA = 10  # hora de Madrid a la que sale el mensaje

# ------------------------------------------------------------ frases
APERTURAS = [
    "🎙️ <b>¡Martes de preguntas!</b> El micro de Los Indies está abierto y Bot Nix recoge el correo.",
    "📬 <b>Buzón Indie abierto.</b> Bot Nix ha vaciado la taquilla y quiere llenarla otra vez.",
    "🏈 <b>Huddle de los martes:</b> ¿qué queréis que comentemos en el próximo programa?",
    "🐴 Bot Nix pide tiempo muerto: <b>es vuestro turno de preguntar.</b>",
    "📋 <b>Rueda de prensa abierta.</b> Los Indies se sientan delante de los micros… y preguntáis vosotros.",
    "🔮 Ni el Palantir sabe lo que vais a preguntar esta semana. <b>¡Sorprendednos!</b>",
]

IDEAS = [
    "Ese equipo que no entendéis, la jugada polémica del domingo, el rookie que os tiene enamorados o el traspaso que nadie vio venir.",
    "NFL, College, UFL, fantasy, historia… o esa duda de reglas que os da vergüenza preguntar en voz alta.",
    "Predicciones locas, dramas de banquillo, quarterbacks en crisis o lo que sea que os ronde por la cabeza.",
    "Vale todo: análisis serio, teorías conspiranoicas o pura curiosidad.",
]

CIERRES = [
    "Las mejores salen en el programa. Las peores… también 😄",
    "Bot Nix las recoge y Los Indies las responden. Trato hecho 🤝",
    "Sin preguntas no hay programa. Bueno, sí lo hay, pero peor.",
    "Prometemos no hacer fair catch con ninguna 🏈",
]


def mensaje() -> str:
    return "\n".join(
        [
            random.choice(APERTURAS),
            "",
            "Dejad vuestras preguntas aquí con el hashtag 👇",
            "",
            "<b>#preguntasindies</b>",
            "",
            f"<i>{random.choice(IDEAS)}</i>",
            "",
            random.choice(CIERRES),
        ]
    )


def main() -> None:
    ahora = datetime.now(ZoneInfo("Europe/Madrid"))
    if "--ahora" not in sys.argv and ahora.hour != HORA:
        print(f"En Madrid son las {ahora:%H:%M}; toca a las {HORA}:00. No envío nada.")
        return

    if not TOKEN or not CHAT_ID:
        sys.exit("Faltan TELEGRAM_TOKEN y/o TELEGRAM_CHAT_ID")

    datos = {"chat_id": CHAT_ID, "text": mensaje(), "parse_mode": "HTML"}
    if THREAD_ID:
        datos["message_thread_id"] = int(THREAD_ID)
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=datos, timeout=30)
    if not r.ok:
        sys.exit(f"Error de Telegram: {r.text}")
    print("Mensaje de #preguntasindies enviado")


if __name__ == "__main__":
    main()
