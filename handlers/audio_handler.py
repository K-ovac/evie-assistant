# audio_handler.py — постоянное прослушивание микрофона (Silero VAD) + воспроизведение
# Нужны: pip install sounddevice soundfile numpy torchaudio   (torchaudio — версия под твой torch)
import collections
import logging
import queue
import time

import numpy as np
import sounddevice as sd
import soundfile as sf
import torch

from data.config import (
    INPUT_DEVICE, VAD_THRESHOLD, SILENCE_END_SEC, MIN_SPEECH_SEC,
    MAX_UTTERANCE_SEC, PRE_ROLL_SEC, BARGE_IN_THRESHOLD,
)

logger = logging.getLogger(__name__)

SR = 16000                 # частота для VAD и Whisper
CHUNK = 512                # размер окна Silero VAD при 16 кГц
CHUNK_SEC = CHUNK / SR     # ~32 мс
SETTLE_SEC = 0.25          # пауза после воспроизведения, чтобы не поймать «хвост» эха


def list_devices():
    """Вывести устройства, чтобы подобрать INPUT_DEVICE в config."""
    print(sd.query_devices())


class Listener:
    def __init__(self):
        logger.info("Загрузка Silero VAD...")
        self.vad, _ = torch.hub.load("snakers4/silero-vad", "silero_vad", trust_repo=True)
        self.q = queue.Queue(maxsize=400)
        self.recent = collections.deque(maxlen=int(PRE_ROLL_SEC / CHUNK_SEC))
        self.native_rate = SR
        self.stream = self._open_stream()

    # ── микрофон ──
    def _open_stream(self):
        def callback(indata, frames, time_info, status):
            try:
                self.q.put_nowait(indata[:, 0].copy())
            except queue.Full:
                pass

        try:  # пробуем сразу 16 кГц
            stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                                    blocksize=CHUNK, device=INPUT_DEVICE, callback=callback)
            stream.start()
            self.native_rate = SR
        except sd.PortAudioError:  # устройство не умеет 16 кГц — пишем в родной и ресемплим
            rate = int(sd.query_devices(INPUT_DEVICE, "input")["default_samplerate"])
            logger.info(f"Микрофон не поддерживает 16 кГц, использую {rate} Гц с ресемплингом")
            stream = sd.InputStream(samplerate=rate, channels=1, dtype="float32",
                                    blocksize=int(CHUNK * rate / SR), device=INPUT_DEVICE, callback=callback)
            stream.start()
            self.native_rate = rate
        return stream

    def _read(self, timeout=0.5):
        try:
            block = self.q.get(timeout=timeout)
        except queue.Empty:
            return None
        self.recent.append(block)
        return block

    def flush(self):
        with self.q.mutex:
            self.q.queue.clear()
        self.recent.clear()

    def _prob(self, block):
        """Вероятность речи в блоке (0..1)."""
        if len(block) != CHUNK:  # грубый ресемплинг только для VAD
            block = np.interp(np.linspace(0, len(block) - 1, CHUNK),
                              np.arange(len(block)), block).astype(np.float32)
        with torch.no_grad():
            return self.vad(torch.from_numpy(block), SR).item()

    # ── запись фразы ──
    def listen(self, wait_timeout=None, use_recent=False):
        """
        Ждёт начала речи и пишет до паузы. Возвращает float32-массив 16 кГц
        или None, если за wait_timeout секунд никто не заговорил.
        use_recent=True — продолжить фразу, начатую во время перебивания (barge-in).
        """
        if use_recent:
            frames, started, speech_time = list(self.recent), True, 0.2
        else:
            time.sleep(SETTLE_SEC)
            self.flush()
            frames, started, speech_time = [], False, 0.0

        ring = collections.deque(maxlen=self.recent.maxlen)  # pre-roll, чтобы не обрезать начало слова
        self.vad.reset_states()
        speech_run, silence = 0, 0.0
        t0 = time.time()

        while True:
            block = self._read()
            if block is None:
                if not started and wait_timeout is not None and time.time() - t0 > wait_timeout:
                    return None
                continue

            is_speech = self._prob(block) > VAD_THRESHOLD

            if not started:
                ring.append(block)
                speech_run = speech_run + 1 if is_speech else 0
                if speech_run >= 3:  # ~100 мс непрерывной речи
                    started, frames = True, list(ring)
                    speech_time, silence = speech_run * CHUNK_SEC, 0.0
                elif wait_timeout is not None and time.time() - t0 > wait_timeout:
                    return None
                continue

            frames.append(block)
            if is_speech:
                silence, speech_time = 0.0, speech_time + CHUNK_SEC
            else:
                silence += CHUNK_SEC

            if silence >= SILENCE_END_SEC or len(frames) * CHUNK_SEC >= MAX_UTTERANCE_SEC:
                if speech_time < MIN_SPEECH_SEC:  # щелчок или шум — начинаем заново
                    started, frames, speech_run = False, [], 0
                    ring.clear()
                    self.vad.reset_states()
                    continue
                break

        audio = np.concatenate(frames)
        if self.native_rate != SR:
            import torchaudio
            audio = torchaudio.functional.resample(torch.from_numpy(audio), self.native_rate, SR).numpy()
        return audio

    # ── перебивание ──
    def wait_playback_or_interrupt(self):
        """Ждёт конца воспроизведения. Если пользователь заговорил — глушит звук и возвращает True."""
        self.flush()
        self.vad.reset_states()
        run = 0
        while sd.get_stream().active:
            block = self._read(timeout=0.1)
            if block is None:
                continue
            run = run + 1 if self._prob(block) > BARGE_IN_THRESHOLD else 0
            if run >= 6:  # ~200 мс речи
                sd.stop()
                return True
        return False


_listener = None


def get_listener() -> Listener:
    global _listener
    if _listener is None:
        _listener = Listener()
    return _listener


def play_audio(filename, interruptible=False):
    """Возвращает True, если воспроизведение было прервано голосом пользователя."""
    data, fs = sf.read(filename)
    sd.play(data, fs)
    if interruptible:
        return get_listener().wait_playback_or_interrupt()
    sd.wait()
    return False