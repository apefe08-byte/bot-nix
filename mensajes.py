"""
La personalidad de Bot Nix 🐴🏈
Edita, añade o quita frases libremente: cada aviso elige una al azar.
Formato: HTML de Telegram (<b>negrita</b>, <i>cursiva</i>).
"""

import random

# ------------------------------------------------------------ PODCAST
APERTURAS_PODCAST = [
    "🚨 <b>¡TOUCHDOWN!</b> Bot Nix lanza desde Mile High… ¡y hay episodio nuevo de Los Indies!",
    "🐴 Snap, drop back y… <b>¡pase completo!</b> Ya tenéis programa nuevo.",
    "📣 <b>Flag en el campo:</b> 15 yardas de penalización para quien no lo escuche hoy.",
    "🏈 <b>Cuarta y una.</b> Los Indies van a por ella. Nuevo episodio en el aire.",
    "⏱️ <b>Two-minute drill:</b> lo que tardáis en darle al play. Episodio nuevo.",
    "🎙️ Bot Nix ha leído la defensa y canta audible: <b>¡nuevo programa!</b>",
    "🔥 <b>Pick six</b> de Los Indies: episodio nuevo devuelto hasta la end zone.",
    "📡 Aquí Bot Nix desde la sideline: <b>los micros ya están calientes.</b>",
    "🧢 El coach ha hablado: <b>hoy toca episodio nuevo</b> en el film room.",
    "🏟️ <b>Kickoff</b> de un nuevo programa de Los Indies. ¡Todos al sofá!",
]

CIERRES_PODCAST = [
    "Dale al play y nos vemos en el huddle 🏈",
    "Bot Nix fuera. ¡Cambio y corto! 🐴",
    "Comentadlo aquí, que el vestuario es vuestro.",
    "Ya estáis tardando. Y no aceptamos fair catch.",
    "Esto no se revisa en el replay: es obligatorio escucharlo.",
]

# Frases especiales si el título contiene ciertas palabras (en minúsculas).
# Se mira en este orden: la primera que coincida manda.
ESPECIALES_PODCAST = {
    "palantir": [
        "🔮 <b>El Palantir de los Indies</b> ya brilla: Bot Nix ha visto el futuro de la jornada… y no os lo va a destripar.",
        "🔮 Ni Gandalf se atreve a tanto: <b>el Palantir</b> ya tiene las previas de la semana.",
        "🔮 <b>Un Palantir para predecirlos a todos.</b> Previa nueva, apuestas a vuestro riesgo.",
        "🧙 Bot Nix ha mirado en <b>el Palantir</b> y ha visto upsets. Muchos upsets.",
        "🔮 Antes de que rueden los ovoides, consultad <b>el Palantir de los Indies</b>.",
    ],
    "apuntes": [
        "📒 <b>Los Apuntes del Campus</b> ya están en conserjería. Prohibido copiar en el examen del sábado.",
        "📒 Subrayador en mano: <b>nuevos Apuntes del Campus</b> de la semana universitaria.",
        "🎓 Bot Nix no fue a clase, pero tiene <b>los Apuntes del Campus</b>. Y vosotros también.",
        "📒 Repaso express de College Football: <b>Los Apuntes del Campus</b> ya están listos.",
        "🏫 Suena el timbre: <b>Los Apuntes del Campus</b> de esta semana, recién fotocopiados.",
    ],
    "ruta 32": [
        "🛣️ <b>Ruta 32 de Los Indies</b>: nueva parada en la carretera. Bot Nix ya tiene el depósito lleno.",
        "🛣️ Abrochaos el cinturón: <b>Ruta 32</b> sigue sumando millas.",
    ],
    "campus": [
        "🎓 <b>El Campus de los Indies</b> abre sus puertas: hoy toca visita universitaria.",
        "🎓 Saturday vibes: Bot Nix se ha ido de excursión al <b>Campus</b>.",
    ],
}


def mensaje_podcast(titulo: str, resumen: str) -> str:
    t = titulo.lower()
    apertura = None
    for clave, frases in ESPECIALES_PODCAST.items():
        if clave in t:
            apertura = random.choice(frases)
            break
    apertura = apertura or random.choice(APERTURAS_PODCAST)

    partes = [apertura, "", f"🎧 <b>{titulo}</b>"]
    if resumen:
        partes += ["", f"<i>{resumen}</i>"]
    partes += ["", random.choice(CIERRES_PODCAST)]
    return "\n".join(partes)


# ------------------------------------------------------------ BLOG
APERTURAS_BLOG = [
    "📝 Bot Nix ha leído la defensa: <b>nuevo artículo en la web.</b>",
    "📋 <b>Scouting report</b> recién salido del horno.",
    "🗞️ Nueva jugada dibujada en la <b>pizarra del blog</b>.",
    "✍️ Alguien ha estado en el film room… <b>¡artículo nuevo!</b>",
    "📚 Pausa para leer, que esto no es solo escuchar: <b>nuevo post</b> en indiesnfl.es.",
]

# Según la categoría de WordPress
APERTURAS_CATEGORIA = {
    "College Football": [
        "🎓 <b>Sábado universitario</b> en la web: nueva historia de College Football.",
        "🏟️ Bandas, mascotas y tradiciones: <b>nuevo artículo de College</b>.",
    ],
    "National Football League": [
        "🏈 <b>Domingo eterno:</b> nuevo artículo de NFL en la web.",
        "📈 La NFL no para y nosotros tampoco: <b>nuevo artículo</b>.",
    ],
    "Más Football Indie": [
        "🕰️ Historias que casi nadie cuenta: <b>nuevo Más Football Indie</b>.",
        "🔎 Bot Nix ha encontrado una joya escondida: <b>Más Football Indie</b>.",
    ],
}

CIERRES_BLOG = [
    "Café en mano y a leer ☕",
    "Bot Nix lo recomienda. Y Bot Nix nunca lanza intercepciones 🐴",
    "Luego lo comentamos en el huddle.",
    "Lectura obligatoria para el resto de la semana.",
]


def mensaje_blog(titulo: str, resumen: str, categorias: list[str]) -> str:
    candidatas = []
    for c in categorias:
        candidatas += APERTURAS_CATEGORIA.get(c, [])
    apertura = random.choice(candidatas or APERTURAS_BLOG)

    partes = [apertura, "", f"📰 <b>{titulo}</b>"]
    if resumen:
        partes += ["", f"<i>{resumen}</i>"]
    partes += ["", random.choice(CIERRES_BLOG)]
    return "\n".join(partes)
