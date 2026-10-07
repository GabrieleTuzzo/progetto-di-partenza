import json
from json import JSONDecodeError
from typing import Any


def _testo(evento: dict[str, Any]) -> str:
    """Estrae il testo dai soli eventi OpenCode di tipo 'text'."""
    if evento.get("type") != "text":
        return ""

    parte = evento.get("part", {})
    if not isinstance(parte, dict):
        return ""

    testo = parte.get("text", "")
    return testo if isinstance(testo, str) else ""


def _token_e_costo(evento: dict[str, Any]) -> tuple[int, float]:
    """Estrae il totale di token e il costo da un evento 'step_finish'."""
    if evento.get("type") != "step_finish":
        return 0, 0.0

    parte = evento.get("part", {})
    if not isinstance(parte, dict):
        raise ValueError("Evento step_finish senza un campo 'part' valido")

    token = parte.get("tokens", {})
    if not isinstance(token, dict):
        raise ValueError("Campo 'tokens' non valido nell'evento step_finish")

    cache = token.get("cache", {})
    if not isinstance(cache, dict):
        raise ValueError("Campo 'cache' non valido nell'evento step_finish")

    valori = [
        token.get("input", 0),
        token.get("output", 0),
        token.get("reasoning", 0),
        cache.get("read", 0),
    ]

    # I contatori possono mancare se valgono zero.
    totale_token = 0
    for valore in valori:
        if valore is None:
            continue
        if not isinstance(valore, int) or isinstance(valore, bool):
            raise ValueError(f"Contatore di token non valido: {valore!r}")
        totale_token += valore

    costo = parte.get("cost", 0.0)
    if not isinstance(costo, (int, float)) or isinstance(costo, bool):
        raise ValueError(f"Costo non valido: {costo!r}")

    return totale_token, float(costo)


def _primo_array_json(testo: str) -> list[Any] | None:
    """Trova il primo array JSON valido, anche se è circondato da prosa o Markdown."""
    decodificatore = json.JSONDecoder()

    for posizione, carattere in enumerate(testo):
        if carattere != "[":
            continue

        try:
            valore, _ = decodificatore.raw_decode(testo, posizione)
        except JSONDecodeError:
            continue

        if isinstance(valore, list):
            return valore

    return None