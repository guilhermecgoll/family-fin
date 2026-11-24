import unicodedata


def chave_alfabetica(texto: str) -> str:
    """Chave de ordenação/comparação que ignora acentos, maiúsculas e espaços extras.

    Independe da collation do banco: "Débito" fica antes de "Dinheiro".
    """
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )
    return " ".join(sem_acentos.casefold().split())
