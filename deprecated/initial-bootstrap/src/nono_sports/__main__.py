import logging

from .config import configure_logging


def main() -> None:
    """Punto de entrada principal del paquete nono-sports."""
    configure_logging()
    logging.info("nono-sports cargado correctamente")
    logging.info(
        "Ejecute los módulos de sincronización, normalización o integración "
        "según su flujo de trabajo."
    )
