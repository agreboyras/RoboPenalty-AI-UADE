from bootstrap import *
from io import StringIO
import json
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

import numpy as np

from audio import AudioConfig
from phase9a.bus import InputBus
from phase9a.commands import EXHIBITION_LABELS, LABELS, LEFT_OPEN, interpret
from phase9a.console import ConsoleInput
from phase9a.control import Control
from phase9a.language import TextInput
from phase9a.voice import VoiceInput
from phase9a.whisper_api import WhisperAPI


def tool_response(name, **arguments):
    call = SimpleNamespace(type='function_call', name=name, arguments=json.dumps(arguments))
    return SimpleNamespace(status='completed', output=[call])


class TranscriptionTests(unittest.TestCase):
    def test_loads_local_key_and_prefers_the_environment(self):
        openai = Mock()
        dotenv = Mock()
        dotenv.dotenv_values.return_value = {'OPENAI_API_KEY': 'test-file-key'}
        with (patch.dict(sys.modules, {'openai': openai, 'dotenv': dotenv}),
              patch('phase9a.whisper_api.ENV_FILE') as env_file):
            env_file.is_file.return_value = True
            with patch.dict('os.environ', {'OPENAI_API_KEY': ''}):
                WhisperAPI().prepare()
            openai.OpenAI.assert_called_once_with(api_key='test-file-key', timeout=8.0, max_retries=0)
            dotenv.dotenv_values.assert_called_once_with(env_file, interpolate=False, encoding='utf-8-sig')
            dotenv.reset_mock()
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-env-key'}):
                WhisperAPI().prepare()
            openai.OpenAI.assert_called_with(api_key='test-env-key', timeout=8.0, max_retries=0)
            dotenv.dotenv_values.assert_not_called()

    def test_audio_format_and_model_specific_language_hint(self):
        for model in ('gpt-transcribe', 'whisper-1'):
            with self.subTest(model=model):
                client = Mock()

                def transcribe(**kwargs):
                    self.assertEqual(kwargs.pop('model'), model)
                    audio = kwargs.pop('file')
                    self.assertEqual(audio.name, 'orden.wav')
                    with wave.open(audio, 'rb') as wav:
                        self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()), (1, 2, 16000))
                        self.assertEqual(wav.readframes(3), np.array([-32767, 0, 32767], dtype='<i2').tobytes())
                    expected = {'language': 'es'} if model == 'whisper-1' else {'extra_body': {'languages': ['es']}}
                    self.assertEqual(kwargs, expected)
                    return SimpleNamespace(text=' Pateá al centro ')

                client.audio.transcriptions.create.side_effect = transcribe
                self.assertEqual(WhisperAPI(model, client).transcribe([-2, 0, 2]), 'Pateá al centro')


class VoiceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.bus = InputBus()
        self.console = []
        self.control = Control(self.bus, emit=lambda line, **kwargs: self.console.append(line))
        self.control.phase = 'PREPARING'
        self.control.active = True
        self.control.penalty = 1
        self.ticket = self.control.open_selection()
        self.client = Mock()
        self.client.audio.transcriptions.create.return_value = SimpleNamespace(text='Pateá a la izquierda')

    def start_capture(self, recognizer=None):
        def capture(config, stop, *, on_ready, **kwargs):
            self.assertNotEqual(threading.get_ident(), self.control.owner)
            on_ready()
            return np.full(800, .1, dtype=np.float32), .1

        self.capture = Mock(side_effect=capture)
        self.worker = VoiceInput(
            self.bus, AudioConfig(), capture_fn=self.capture,
            recognizer=recognizer or WhisperAPI(client=self.client),
        )
        self.control.voice = self.worker
        self.worker.start()
        self.addCleanup(lambda: self.assertTrue(self.worker.close()))
        self.submit('/voz')
        self.assertTrue(self.control.events[-1]['accepted'])

    def submit(self, text):
        self.bus.submit(text)
        self.control.pump()

    def wait_for_capture(self):
        deadline = time.monotonic() + 3
        while not self.worker.metrics and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.worker.metrics, 'Voice capture did not finish')
        self.control.pump()

    def test_compound_direction_uses_parser_and_selects_immediately(self):
        self.assertEqual(interpret('Al centro a la izquierda'), 'shot:left_near_b060')
        self.assertIsNone(interpret('Pateá al centro o a la izquierda'))
        self.assertIsNone(interpret('No patees al centro a la izquierda'))
        text = 'Patea al centro a la izquierda'
        self.client.audio.transcriptions.create.return_value.text = text
        self.start_capture()
        self.wait_for_capture()
        self.client.responses.create.assert_not_called()
        self.assertTrue(any(text in line and 'centro-izquierda' in line for line in self.console))
        self.assertEqual(self.control.pending_shot['action'], 'left_near_b060')
        self.assertEqual(self.control.pending_shot['text'], text)
        self.assertEqual(self.control.pending_shot['source'], 'voice')
        self.assertIsNone(self.bus.active_ticket())

    def test_misheard_order_uses_luna_and_selects_immediately(self):
        self.client.audio.transcriptions.create.return_value.text = 'mandala a la isquierda'

        def resolve(**kwargs):
            self.assertNotEqual(threading.get_ident(), self.control.owner)
            self.assertTrue(self.worker.capture_closed.is_set())
            self.assertEqual(kwargs['model'], 'gpt-6-luna')
            self.assertEqual(kwargs['input'], 'mandala a la isquierda')
            self.assertEqual(kwargs['tool_choice'], 'required')
            self.assertFalse(kwargs['parallel_tool_calls'])
            tools = {tool['name']: tool for tool in kwargs['tools']}
            self.assertEqual(set(tools), {'patear', 'pedir_aclaracion'})
            self.assertTrue(all(tool['strict'] for tool in tools.values()))
            schema = tools['patear']['parameters']
            self.assertEqual(set(schema['properties']['action']['enum']), set(LABELS))
            return tool_response('patear', action='left_near_b060')

        self.client.responses.create.side_effect = resolve
        self.start_capture()
        self.wait_for_capture()
        self.client.responses.create.assert_called_once()
        self.assertTrue(any('mandala a la isquierda' in line and 'centro-izquierda' in line for line in self.console))
        self.assertEqual(self.control.pending_shot['action'], 'left_near_b060')

    def test_out_of_catalog_response_requests_clarification(self):
        self.client.audio.transcriptions.create.return_value.text = 'mandala al otro lado'
        self.client.responses.create.return_value = tool_response('patear', action='left_corner')
        self.start_capture()
        self.wait_for_capture()
        self.assertIsNone(self.control.pending_shot)
        self.assertIn('Necesito una aclaración', self.control.events[-1]['reason'])

    def test_alternative_destinations_leave_penalty_waiting(self):
        self.client.audio.transcriptions.create.return_value.text = 'Patea al centro o a la izquierda'
        self.client.responses.create.return_value = tool_response('pedir_aclaracion')
        self.start_capture()
        self.wait_for_capture()
        self.assertIsNone(self.control.pending_shot)
        self.assertEqual(self.bus.active_ticket(), self.ticket)
        self.assertIn('Necesito una aclaración', self.control.events[-1]['reason'])

    def test_late_interpretation_cannot_select_the_next_penalty(self):
        self.client.audio.transcriptions.create.return_value.text = 'mandala a la isquierda'
        entered, release = threading.Event(), threading.Event()

        def resolve(**kwargs):
            entered.set()
            release.wait(3)
            return tool_response('patear', action='left_near_b060')

        self.client.responses.create.side_effect = resolve
        self.start_capture()
        self.addCleanup(release.set)
        self.assertTrue(entered.wait(3))
        self.submit('Pateá al centro')
        self.assertEqual(self.control.pending_shot['action'], 'center')
        self.control.penalty = 2
        self.assertNotEqual(self.control.open_selection(), self.ticket)
        release.set()
        self.wait_for_capture()
        self.assertEqual(self.worker.metrics[0]['stage'], 'discarded')
        self.assertIsNone(self.control.pending_shot)

    def test_pause_invalidates_queued_voice_for_same_penalty(self):
        entered, release = threading.Event(), threading.Event()

        def transcribe(**kwargs):
            entered.set()
            release.wait(3)
            return SimpleNamespace(text='Patea a la izquierda')

        self.client.audio.transcriptions.create.side_effect = transcribe
        self.start_capture()
        self.addCleanup(release.set)
        self.assertTrue(entered.wait(3))
        self.bus.submit('Pausar partida')
        self.bus.submit('Reanudar partida')
        release.set()
        self.wait_for_capture()
        self.assertEqual(self.bus.active_ticket(), self.ticket)
        self.assertIsNone(self.control.pending_shot)
        self.assertIn('Orden de voz vencida', self.control.events[-1]['reason'])

    def test_missing_key_leaves_microphone_closed_and_text_usable(self):
        with (patch.dict('os.environ', {'OPENAI_API_KEY': ''}),
              patch('phase9a.whisper_api.ENV_FILE') as env_file):
            env_file.is_file.return_value = False
            self.start_capture(WhisperAPI())
            self.wait_for_capture()
        self.capture.assert_not_called()
        self.assertTrue(any('Falta OPENAI_API_KEY' in line for line in self.console))
        self.submit('Pateá al centro')
        self.assertEqual(self.control.pending_shot['action'], 'center')


class TypedSelectionTests(unittest.TestCase):
    def setup_control(self, *, exhibition=False):
        self.bus = InputBus(exhibition=exhibition)
        self.control = Control(self.bus, emit=lambda *args, **kwargs: None)
        if exhibition:
            self.control.shot_labels = EXHIBITION_LABELS
        self.control.phase = 'PREPARING'
        self.control.active = True
        self.ticket = self.control.open_selection()
        self.control.voice = Mock()
        self.client = Mock()
        self.text_input = TextInput(exhibition=exhibition, api=WhisperAPI(client=self.client))
        self.control.text_input = self.text_input
        self.text_input.start()
        self.addCleanup(lambda: self.assertTrue(self.text_input.close()))

    def submit(self, text):
        self.bus.submit(text)
        self.control.pump()

    def wait_for_text(self):
        deadline = time.monotonic() + 3
        while self.text_input.pending is not None and time.monotonic() < deadline:
            self.control.pump()
            time.sleep(.01)
        self.assertIsNone(self.text_input.pending, 'Text interpretation did not finish')

    def test_known_and_misspelled_console_shots_use_luna(self):
        self.setup_control()

        def resolve(**kwargs):
            self.assertNotEqual(threading.get_ident(), self.control.owner)
            self.assertEqual(kwargs['model'], 'gpt-6-luna')
            self.assertEqual(kwargs['tool_choice'], 'required')
            self.assertEqual({tool['name'] for tool in kwargs['tools']}, {'patear', 'pedir_aclaracion'})
            return tool_response('patear', action='left_near_b060')

        self.client.responses.create.side_effect = resolve
        for text in ('Pateá a la izquierda', 'Pateá a la isquierda'):
            with self.subTest(text=text):
                self.control.open_selection()
                self.control.voice.reset_mock()
                self.submit(text)
                self.wait_for_text()
                self.assertEqual(self.client.responses.create.call_args.kwargs['input'], text)
                self.control.voice.cancel_request.assert_called()
                self.assertEqual(self.control.pending_shot['source'], 'text')
                self.assertEqual(self.control.pending_shot['action'], 'left_near_b060')
        self.client.audio.transcriptions.create.assert_not_called()
        self.assertEqual(self.client.responses.create.call_count, 2)

    def test_exhibition_uses_its_catalog_and_can_ask_for_clarification(self):
        self.setup_control(exhibition=True)
        self.client.responses.create.side_effect = [
            tool_response('pedir_aclaracion'),
            tool_response('patear', action=LEFT_OPEN),
        ]
        self.submit('Pateá a la izquierda')
        self.wait_for_text()
        self.assertIsNone(self.control.pending_shot)
        self.assertEqual(self.bus.active_ticket(), self.ticket)
        self.assertIn('Necesito una aclaración', self.control.events[-1]['reason'])
        self.submit('Isquierda avierta')
        self.wait_for_text()
        shot_tool = self.client.responses.create.call_args.kwargs['tools'][0]
        self.assertEqual(set(shot_tool['parameters']['properties']['action']['enum']), set(EXHIBITION_LABELS))
        self.assertEqual(self.control.pending_shot['action'], LEFT_OPEN)

    def test_open_left_in_standard_match_points_to_exhibition(self):
        self.setup_control()
        self.submit('Patea abierto a la izquierda')
        self.client.responses.create.assert_not_called()
        self.assertIsNone(self.control.pending_shot)
        self.assertIn('-ArqueroLibre', self.control.events[-1]['reason'])
        self.assertEqual(self.bus.active_ticket(), self.ticket)

    def test_first_console_key_cancels_capture_and_status_preserves_input(self):
        self.setup_control()
        output = StringIO()
        console = ConsoleInput(self.bus, output, voice_enabled=True)
        console.read_key('P')
        self.control.pump()
        self.control.voice.cancel_request.assert_called_once()
        self.client.responses.create.assert_not_called()
        console.emit('[microfono] Estado', flush=True)
        self.assertEqual(output.getvalue(), 'P\r \r[microfono] Estado\nP')
        for char in 'atea abierto a la izquierda\r':
            console.read_key(char)
        self.control.pump()
        self.assertEqual(self.control.events[-1]['text'], 'Patea abierto a la izquierda')
        self.control.voice.cancel_request.assert_called_once()

        for char in '/voz\r':
            console.read_key(char)
        self.control.voice.request.return_value = True, 'Captura solicitada'
        self.control.pump()
        self.control.voice.cancel_request.assert_called_once()
        self.control.voice.request.assert_called_once_with(self.ticket)

    def test_pause_invalidates_text_and_controls_stay_responsive(self):
        self.setup_control()
        entered, release = threading.Event(), threading.Event()

        def resolve(**kwargs):
            entered.set()
            release.wait(3)
            return tool_response('patear', action='left_near_b060')

        self.client.responses.create.side_effect = resolve
        self.submit('Mandala a la isquierda')
        self.addCleanup(release.set)
        self.assertTrue(entered.wait(3))
        self.submit('Pausar partida')
        self.assertTrue(self.control.paused)
        self.assertIsNone(self.text_input.pending)
        self.submit('Reanudar partida')
        self.assertFalse(self.control.paused)
        self.assertEqual(self.bus.active_ticket(), self.ticket)
        release.set()
        self.assertTrue(self.text_input.close())
        self.control.pump()
        self.assertIsNone(self.control.pending_shot)
        self.assertEqual(self.client.responses.create.call_count, 1)

    def test_exact_text_remains_usable_when_the_api_fails(self):
        self.setup_control()
        self.client.responses.create.side_effect = TimeoutError()
        self.submit('Pateá al centro')
        self.wait_for_text()
        self.assertEqual(self.control.pending_shot['action'], 'center')
        self.assertIn('Parser local', self.control.events[-1]['reason'])


if __name__ == '__main__':
    unittest.main()
