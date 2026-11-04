from django.conf import settings
from ollama import Client


def polacz_z_modelem():
    return Client(host=settings.OLLAMA_HOST, timeout=180)

