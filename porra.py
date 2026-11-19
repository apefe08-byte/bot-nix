"""
Bot Nix - Rumbo a SoFi, la porra Indie 🏈🐴

Recoge las porras de la comunidad y publica la clasificación.

Cómo llega una porra:
  La página porra/index.html genera un código (p. ej. P1aeknpu...) y abre
  t.me/IndiesnflBot?start=CODIGO. Al pulsar "Iniciar", Telegram manda al bot
  "/start CODIGO" por privado. Este script lo recoge con getUpdates, lo valida,
  lo guarda en porra.json y responde por privado con el resumen.

Uso:
  python porra.py                    -> pasada normal (recoger porras, recordatorio, clasificación del martes)
  python porra.py --anunciar         -> publica en el grupo el anuncio con el botón para jugar
  python porra.py --clasificacion    -> publica ya la clasificación provisional
  python porra.py --dry-run          -> hace todo pero no envía nada a Telegram ni guarda
"""

import html
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
THREAD_ID = os.environ.get("TELEGRAM_THREAD_ID", "")
PORRA_URL = os.environ.get("PORRA_URL", "")

MADRID = ZoneInfo("Europe/Madrid")
BASE = Path(__file__).resolve().parent
CONFIG = json.loads((BASE / "porra" / "config.json").read_text(encoding="utf-8"))
ESTADO_PATH = BASE / "porra.json"
RESULTADOS_PATH = BASE / "porra" / "resultados.json"   # opcional, para corregir a mano
ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"

EQUIPOS = CONFIG["equipos"]
DIVISIONES = CONFIG["divisiones"]
CIERRE = datetime.fromisoformat(CONFIG["cierre"])
ALF = "abcdefghijklmnopqrstuvwxyzABCDEF"   # índice de equipo -> letra (32 equipos)
VERSION = "P1"
LONGITUD = len(VERSION) + 8 + 6 + 2 + 1

DRY = "--dry-run" in sys.argv
CLASIFICACION_DIA = 1    # martes (lunes=0)
CLASIFICACION_HORA = 13  # hora de Madrid

PUNTOS = {"playoffs": 1, "division": 2, "seed1": 3, "campeon": 10}

ALIAS_ESPN = {"WAS": "WSH", "LA": "LAR", "JAC": "JAX", "LVR": "LV", "OAK": "LV"}
IDX_POR_ABR = {e["abr"]: i for i, e in enumerate(EQUIPOS)}


def conf(i: int) -> int:
    """0 = AFC, 1 = NFC"""
    return 0 if EQUIPOS[i]["div"] < 4 else 1


def nombre(i: int) -> str:
    return EQUIPOS[i]["nombre"]


# ------------------------------------------------------------------ código de la porra
def decodificar(codigo: str) -> dict:
    """Convierte el código de la página en picks. Lanza ValueError si no es válido."""
    if not codigo.startswith(VERSION) or len(codigo) != LONGITUD:
        raise ValueError("el código no tiene el formato correcto")
    try:
        idx = [ALF.index(c) for c in codigo[len(VERSION):]]
    except ValueError:
        raise ValueError("el código tiene caracteres raros")

    divisiones, comodines, seeds, campeon = idx[0:8], idx[8:14], idx[14:16], idx[16]

    for d, eq in enumerate(divisiones):
        if EQUIPOS[eq]["div"] != d:
            raise ValueError(f"el ganador de la {DIVISIONES[d]} no es de esa división")
    if len(set(comodines)) != 6:
        raise ValueError("hay comodines repetidos")
    for k, eq in enumerate(comodines):
        if conf(eq) != (0 if k < 3 else 1):
            raise ValueError("hay un comodín en la conferencia equivocada")
        if eq in divisiones:
            raise ValueError("un comodín no puede ser también campeón de división")
    for c, eq in enumerate(seeds):
        if eq not in divisiones[c * 4:(c + 1) * 4]:
            raise ValueError("el #1 seed tiene que ser uno de tus campeones de división")
    if campeon not in divisiones + comodines:
        raise ValueError("el campeón de la Super Bowl tiene que estar en tus playoffs")

    return {"divisiones": divisiones, "comodines": comodines, "seeds": seeds, "campeon": campeon}


def resumen_picks(p: dict) -> str:
    lineas = []
    for c, conf_nombre in enumerate(["AFC", "NFC"]):
        lineas.append(f"<b>{conf_nombre}</b>")
        for d in range(c * 4, c * 4 + 4):
            eq = p["divisiones"][d]
            estrella = " ⭐ #1 seed" if eq == p["seeds"][c] else ""
            lineas.append(f"  🏆 {DIVISIONES[d].split()[1]}: {nombre(eq)}{estrella}")
        wild = ", ".join(EQUIPOS[e]["corto"] for e in p["comodines"][c * 3:c * 3 + 3])
        lineas.append(f"  🎟️ Comodines: {wild}")
        lineas.append("")
    lineas.append(f"💍 <b>Campeón de la Super Bowl LXI:</b> {nombre(p['campeon'])}")
    return "\n".join(lineas)


# ------------------------------------------------------------------ estado
def cargar_estado() -> dict:
    if ESTADO_PATH.exists():
        return json.loads(ESTADO_PATH.read_text(encoding="utf-8"))
    return {"offset": 0, "participantes": {}, "avisos": {}}


def guardar_estado(estado: dict) -> None:
    if DRY:
        print("[dry-run] no guardo porra.json")
        return
    ESTADO_PATH.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ Telegram
def tg(metodo: str, **datos) -> dict:
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/{metodo}", json=datos, timeout=30)
    res = r.json()
    if not res.get("ok"):
        raise RuntimeError(f"Telegram {metodo} falló: {res}")
    return res


def enviar(chat_id, texto: str, boton: tuple | None = None, al_grupo: bool = False) -> None:
    if DRY:
        print(f"\n[dry-run] -> {chat_id}\n{texto}\n")
        return
    datos = {"chat_id": chat_id, "text": texto, "parse_mode": "HTML",
             "disable_web_page_preview": True}
    if al_grupo and THREAD_ID:
        datos["message_thread_id"] = int(THREAD_ID)
    if boton:
        datos["reply_markup"] = {"inline_keyboard": [[{"text": boton[0], "url": boton[1]}]]}
    tg("sendMessage", **datos)


def enviar_privado(chat_id, texto: str, codigo: str = "") -> None:
    """Las respuestas privadas no deben tumbar la pasada si un usuario bloqueó al bot."""
    boton = None
    if PORRA_URL:
        url = f"{PORRA_URL}?c={codigo}" if codigo else PORRA_URL
        boton = ("✏️ Cambiar mi porra" if codigo else "🏈 Hacer mi porra", url)
    try:
        enviar(chat_id, texto, boton=boton)
    except Exception as e:
        print(f"No pude responder a {chat_id}: {e}")


# ------------------------------------------------------------------ recoger porras
AYUDA = (
    "🐴 <b>¡Hola! Soy Bot Nix.</b>\n\n"
    f"Para jugar a <b>{CONFIG['nombre']}</b> haz tus picks en la página y pulsa "
    "<b>Enviar a Bot Nix</b>. Yo te confirmo por aquí.\n\n"
    "Escribe /mipick para ver tu porra.\n"
    "<i>Ojo: paso a recoger porras cada 20 minutos, así que la confirmación puede tardar un poco.</i>"
)


def procesar_mensaje(msg: dict, estado: dict) -> None:
    chat = msg.get("chat", {})
    if chat.get("type") != "private":
        return  # mensajes del grupo: no son para la porra
    texto = (msg.get("text") or "").strip()
    usuario = msg.get("from", {})
    uid = str(usuario.get("id"))
    fecha = datetime.fromtimestamp(msg["date"], tz=MADRID)

    if texto.startswith("/mipick"):
        p = estado["participantes"].get(uid)
        if p:
            enviar_privado(chat["id"], "📋 <b>Tu porra:</b>\n\n" + resumen_picks(p["picks"]), p["codigo"])
        else:
            enviar_privado(chat["id"], "Todavía no tengo tu porra. " + AYUDA)
        return

    if not texto.startswith("/start"):
        return

    partes = texto.split(maxsplit=1)
    if len(partes) < 2 or not partes[1].startswith("P"):
        enviar_privado(chat["id"], AYUDA)
        return

    if fecha >= CIERRE:
        enviar_privado(chat["id"], "⏱️ <b>La porra ya está cerrada.</b> Esta vez llegas tarde, "
                                   "¡pero en enero vuelve con el bracket de playoffs!")
        return

    try:
        picks = decodificar(partes[1])
    except ValueError as e:
        enviar_privado(chat["id"], f"🚩 Flag en el campo: {html.escape(str(e))}. "
                                   "Vuelve a la página y envíala de nuevo.")
        return

    nombre_usuario = " ".join(x for x in [usuario.get("first_name"), usuario.get("last_name")] if x)
    anterior = estado["participantes"].get(uid)
    if anterior and anterior["fecha"] > fecha.isoformat():
        return  # ya tenemos una porra más reciente de esta persona

    estado["participantes"][uid] = {
        "nombre": nombre_usuario or "Indie anónimo",
        "usuario": usuario.get("username", ""),
        "picks": picks,
        "codigo": partes[1],
        "fecha": fecha.isoformat(),
    }
    cabecera = "🔄 <b>Porra actualizada.</b>" if anterior else "✅ <b>¡Porra registrada!</b>"
    cierre_txt = CIERRE.astimezone(MADRID).strftime("%d/%m a las %H:%M")
    enviar_privado(chat["id"], f"{cabecera} Bot Nix la guarda bajo llave 🔐\n\n{resumen_picks(picks)}\n\n"
                               f"<i>Puedes cambiarla hasta el {cierre_txt} (hora de Madrid). "
                               "Cuenta la última que envíes.</i>", partes[1])


def recoger_porras(estado: dict) -> int:
    nuevas = 0
    while True:
        res = tg("getUpdates", offset=estado["offset"], timeout=0, allowed_updates=["message"])
        updates = res["result"]
        if not updates:
            break
        for u in updates:
            estado["offset"] = u["update_id"] + 1
            if "message" in u:
                try:
                    procesar_mensaje(u["message"], estado)
                    nuevas += 1
                except Exception as e:
                    print(f"Error con el update {u['update_id']}: {e}")
    return nuevas


# ------------------------------------------------------------------ resultados y puntos
def seeds_espn() -> dict:
    """Devuelve {indice_equipo: seed} con la clasificación actual ("si acabase hoy")."""
    data = requests.get(ESPN_STANDINGS, timeout=30).json()
    seeds = {}

    def recorrer(nodo):
        if isinstance(nodo, dict):
            team = nodo.get("team")
            stats = nodo.get("stats")
            if isinstance(team, dict) and isinstance(stats, list):
                abr = ALIAS_ESPN.get(team.get("abbreviation", ""), team.get("abbreviation", ""))
                for s in stats:
                    if s.get("name") == "playoffSeed" and abr in IDX_POR_ABR:
                        try:
                            seeds[IDX_POR_ABR[abr]] = int(float(s.get("value")))
                        except (TypeError, ValueError):
                            pass
            for v in nodo.values():
                recorrer(v)
        elif isinstance(nodo, list):
            for v in nodo:
                recorrer(v)

    recorrer(data)
    return seeds


def cargar_resultados() -> tuple[dict, int | None]:
    """Seeds de ESPN, salvo que porra/resultados.json los corrija a mano."""
    campeon = None
    manual = {}
    if RESULTADOS_PATH.exists():
        manual = json.loads(RESULTADOS_PATH.read_text(encoding="utf-8"))
        if manual.get("campeon"):
            campeon = IDX_POR_ABR[manual["campeon"]]
    if manual.get("seeds"):
        seeds = {IDX_POR_ABR[a]: int(s) for a, s in manual["seeds"].items()}
    else:
        seeds = seeds_espn()

    for c in (0, 1):
        de_conf = sorted(s for i, s in seeds.items() if conf(i) == c and 1 <= s <= 7)
        if de_conf != list(range(1, 8)):
            raise RuntimeError(f"Seeds incompletos para la {'AFC' if c == 0 else 'NFC'}: {de_conf}")
    return seeds, campeon


def puntuar(picks: dict, seeds: dict, campeon: int | None) -> dict:
    en_playoffs = {i for i, s in seeds.items() if 1 <= s <= 7}
    campeones_div = {i for i, s in seeds.items() if 1 <= s <= 4}
    seed1 = {i for i, s in seeds.items() if s == 1}

    mis_playoffs = set(picks["divisiones"]) | set(picks["comodines"])
    pts = {
        "playoffs": len(mis_playoffs & en_playoffs) * PUNTOS["playoffs"],
        "division": len(set(picks["divisiones"]) & campeones_div) * PUNTOS["division"],
        "seed1": len(set(picks["seeds"]) & seed1) * PUNTOS["seed1"],
        "campeon": PUNTOS["campeon"] if campeon is not None and picks["campeon"] == campeon else 0,
    }
    pts["total"] = sum(pts.values())
    return pts


def enumerar(nombres: list[str]) -> str:
    return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]


def flecha(antes: int | None, ahora: int) -> str:
    if antes is None:
        return "🆕"
    if antes > ahora:
        return f"⬆️{antes - ahora}"
    if antes < ahora:
        return f"⬇️{ahora - antes}"
    return "➖"


def mensaje_clasificacion(estado: dict) -> tuple[str, dict]:
    """Devuelve el mensaje y las posiciones de esta semana {uid: posición}."""
    seeds, campeon = cargar_resultados()
    filas = []
    for uid, p in estado["participantes"].items():
        pts = puntuar(p["picks"], seeds, campeon)
        filas.append((-pts["total"], p["fecha"], uid, p["nombre"], pts))
    filas.sort()

    # posiciones (los empatados a puntos comparten puesto)
    posiciones, pos_prev, total_prev = {}, 0, None
    for n, (neg, _, uid, _, _) in enumerate(filas, start=1):
        pos = pos_prev if -neg == total_prev else n
        pos_prev, total_prev = pos, -neg
        posiciones[uid] = pos

    anteriores = estado.get("clasif_anterior") or {}
    hay_anterior = bool(anteriores)

    medallas = ["🥇", "🥈", "🥉"]
    lineas = [f"🏈 <b>{CONFIG['nombre']}</b>",
              "📊 <b>Clasificación provisional</b> — <i>si la temporada acabase hoy</i>", ""]
    if not filas:
        lineas.append("Todavía no hay porras... ¿nadie se atreve? 👀")
    for _, _, uid, nom, pts in filas[:10]:
        pos = posiciones[uid]
        icono = medallas[pos - 1] if pos <= 3 else f"{pos}."
        mov = f" {flecha(anteriores.get(uid), pos)}" if hay_anterior else ""
        lineas.append(f"{icono} {html.escape(nom)} — <b>{pts['total']} pts</b>{mov}  "
                      f"<i>({pts['playoffs']} PO · {pts['division']} div · {pts['seed1']} #1)</i>")
    if len(filas) > 10:
        lineas.append(f"\n…y {len(filas) - 10} indies más persiguiendo el anillo.")

    # destacados de la semana
    nombres = {uid: html.escape(nom) for _, _, uid, nom, _ in filas}
    destacados = []
    if hay_anterior:
        subidas = {uid: anteriores[uid] - pos for uid, pos in posiciones.items() if uid in anteriores}
        mejor = max(subidas.values(), default=0)
        if mejor > 0:
            quienes = enumerar([nombres[u] for u, d in subidas.items() if d == mejor])
            destacados.append(f"🚀 <b>El que más sube:</b> {quienes} (⬆️{mejor} "
                              f"{'puesto' if mejor == 1 else 'puestos'})")
    if len(filas) >= 3:
        ultimo = max(posiciones.values())
        farolillos = [nombres[u] for u, pos in posiciones.items() if pos == ultimo]
        if len(farolillos) < len(filas):
            destacados.append(f"🏮 <b>Farolillo rojo:</b> {enumerar(farolillos)}. ¡Aún queda temporada!")
    if destacados:
        lineas += [""] + destacados

    afc = ", ".join(EQUIPOS[i]["corto"] for i, s in sorted(seeds.items(), key=lambda x: x[1]) if conf(i) == 0 and s <= 7)
    nfc = ", ".join(EQUIPOS[i]["corto"] for i, s in sorted(seeds.items(), key=lambda x: x[1]) if conf(i) == 1 and s <= 7)
    lineas += ["", "<b>Así estarían los playoffs hoy:</b>", f"AFC: {afc}", f"NFC: {nfc}", "",
               f"<i>{len(filas)} participantes · Puntos: {PUNTOS['playoffs']} por equipo en playoffs, "
               f"{PUNTOS['division']} por campeón de división, {PUNTOS['seed1']} por #1 seed y "
               f"{PUNTOS['campeon']} por el campeón de la Super Bowl.</i>"]
    return "\n".join(lineas), posiciones


# ------------------------------------------------------------------ mensajes al grupo
def mensaje_anuncio() -> str:
    cierre_txt = CIERRE.astimezone(MADRID).strftime("%A %d/%m a las %H:%M")
    dias = {"Monday": "lunes", "Tuesday": "martes", "Wednesday": "miércoles", "Thursday": "jueves",
            "Friday": "viernes", "Saturday": "sábado", "Sunday": "domingo"}
    for en, es in dias.items():
        cierre_txt = cierre_txt.replace(en, es)
    return (
        f"🏈🐴 <b>¡ARRANCA {CONFIG['nombre'].upper()}!</b>\n\n"
        "¿Quién llegará a playoffs? ¿Quién se lleva el anillo en la Super Bowl LXI?\n"
        "Es el momento de mojarse... y de que luego os lo recordemos en el programa 😏\n\n"
        "<b>Cómo se juega:</b>\n"
        "1️⃣ Pulsa el botón y elige campeones de división, comodines, #1 seeds y campeón.\n"
        "2️⃣ Dale a <b>Enviar a Bot Nix</b> y pulsa <b>Iniciar</b> en el chat conmigo.\n"
        "3️⃣ Te confirmo por privado. Puedes cambiarla las veces que quieras hasta el cierre.\n\n"
        f"⏱️ <b>Cierre:</b> {cierre_txt} (hora de Madrid)\n"
        f"📊 Cada martes, clasificación provisional aquí en el grupo.\n\n"
        f"<b>Puntos:</b> {PUNTOS['playoffs']} por equipo en playoffs · {PUNTOS['division']} por campeón de división · "
        f"{PUNTOS['seed1']} por #1 seed · {PUNTOS['campeon']} por el campeón de la Super Bowl."
    )


def mensaje_recordatorio(estado: dict) -> str:
    n = len(estado["participantes"])
    return (
        "⏰ <b>¡Últimas 24 horas para la porra Indie!</b>\n\n"
        f"Ya hay <b>{n}</b> {'valiente' if n == 1 else 'valientes'} con su porra hecha. "
        "Si te falta la tuya, todavía estás a tiempo. Bot Nix no acepta porras fuera de plazo 🐴"
    )


def semana_iso(dt: datetime) -> str:
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def main() -> None:
    if not TOKEN or not CHAT_ID:
        sys.exit("Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
    boton_jugar = ("🏈 Hacer mi porra", PORRA_URL) if PORRA_URL else None
    estado = cargar_estado()
    ahora = datetime.now(MADRID)

    nuevas = recoger_porras(estado)
    print(f"Mensajes privados procesados: {nuevas} · participantes: {len(estado['participantes'])}")
    guardar_estado(estado)  # las porras quedan guardadas aunque luego falle un mensaje al grupo

    if "--anunciar" in sys.argv:
        enviar(CHAT_ID, mensaje_anuncio(), boton=boton_jugar, al_grupo=True)

    if "--clasificacion" in sys.argv:
        # lanzada a mano: publica, pero no cambia la referencia de las flechas del martes
        enviar(CHAT_ID, mensaje_clasificacion(estado)[0], al_grupo=True)

    # recordatorio 24 h antes del cierre (una sola vez)
    if CIERRE - timedelta(hours=24) <= ahora < CIERRE and not estado["avisos"].get("recordatorio"):
        enviar(CHAT_ID, mensaje_recordatorio(estado), boton=boton_jugar, al_grupo=True)
        estado["avisos"]["recordatorio"] = ahora.isoformat()

    # aviso de cierre (una sola vez)
    if ahora >= CIERRE and not estado["avisos"].get("cerrada"):
        n = len(estado["participantes"])
        enviar(CHAT_ID, f"🔒 <b>¡Porra cerrada!</b> {n} indies se han mojado. "
                        "El martes, primera clasificación provisional. Que empiece el sufrimiento 🍿",
               al_grupo=True)
        estado["avisos"]["cerrada"] = ahora.isoformat()

    # clasificación de los martes (una por semana, después del cierre)
    semana = semana_iso(ahora)
    if (ahora >= CIERRE and ahora.weekday() == CLASIFICACION_DIA and ahora.hour >= CLASIFICACION_HORA
            and estado["avisos"].get("clasificacion") != semana):
        texto, posiciones = mensaje_clasificacion(estado)
        enviar(CHAT_ID, texto, al_grupo=True)
        estado["avisos"]["clasificacion"] = semana
        estado["clasif_anterior"] = posiciones

    guardar_estado(estado)


if __name__ == "__main__":
    main()
