"""OpenAI file transcription for the short, 16 kHz microphone capture."""
from io import BytesIO
import os
from pathlib import Path
import wave

import numpy as np

DEFAULT_TRANSCRIPTION_MODEL = 'gpt-transcribe'
TRANSCRIPTION_MODELS = (DEFAULT_TRANSCRIPTION_MODEL, 'whisper-1')
ENV_FILE = Path(__file__).resolve().parents[3] / '.env.local'


class VoiceError(RuntimeError):
    """An error safe to display and record in the session log."""


def api_error(operation, exc):
    status = getattr(exc, 'status_code', None)
    detail = f'HTTP {status}' if isinstance(status, int) else type(exc).__name__
    return VoiceError(f'OpenAI no pudo {operation} ({detail})')


class WhisperAPI:
    def __init__(self, model=DEFAULT_TRANSCRIPTION_MODEL, client=None):
        self.model = model
        self.client = client

    def prepare(self):
        if self.client is None:
            api_key = os.environ.get('OPENAI_API_KEY', '').strip()
            if not api_key and ENV_FILE.is_file():
                try:
                    from dotenv import dotenv_values
                except ImportError as exc:
                    raise VoiceError('Instalá las dependencias de requirements-voice.txt') from exc
                try:
                    values = dotenv_values(ENV_FILE, interpolate=False, encoding='utf-8-sig')
                except (OSError, UnicodeError) as exc:
                    raise VoiceError('No se pudo leer .env.local') from exc
                api_key = (values.get('OPENAI_API_KEY') or '').strip()
            if not api_key:
                raise VoiceError('Falta OPENAI_API_KEY en .env.local o en el entorno')
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise VoiceError('Instalá las dependencias de requirements-voice.txt') from exc
            self.client = OpenAI(api_key=api_key, timeout=8.0, max_retries=0)

    def transcribe(self, samples):
        self.prepare()
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim != 1 or not samples.size or not np.isfinite(samples).all():
            raise VoiceError('Audio mono vacío o inválido')
        with BytesIO() as audio:
            audio.name = 'orden.wav'
            with wave.open(audio, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes((np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes())
            audio.seek(0)
            language_hint = (
                {'language': 'es'} if self.model == 'whisper-1'
                else {'extra_body': {'languages': ['es']}}
            )
            try:
                response = self.client.audio.transcriptions.create(
                    model=self.model, file=audio, **language_hint,
                )
            except Exception as exc:
                raise api_error('transcribir el audio', exc) from exc
        return response.text.strip()

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None
