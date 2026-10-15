import unicodedata


def normalizar_nombre(texto):
    """
    Forma comparable de un nombre: sin tildes, sin mayúsculas y con los
    espacios colapsados. "  Máiz  " y "maiz" dan el mismo resultado.
    """
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto or "")
        if not unicodedata.combining(c)
    )
    return " ".join(sin_tildes.casefold().split())
