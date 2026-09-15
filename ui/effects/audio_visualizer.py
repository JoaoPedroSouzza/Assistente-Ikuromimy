"""Decode real TTS PCM for the visual envelope, without changing playback.

The visualization clock is approximate: playsound does not expose its position.
If the platform cannot decode the source, no synthetic audio levels are emitted.
"""
import time
import numpy as np
from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtMultimedia import QAudioDecoder, QAudioFormat

class AudioVisualizer(QObject):
    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.bus = bus
        self.decoder = None
        self.envelope = []
        self.index = 0
        self.started = None
        self.timer = QTimer(self); self.timer.setInterval(40); self.timer.timeout.connect(self.sample)
        bus.incoming.connect(self.receive_event)

    @Slot(str, object)
    def receive_event(self, event, value):
        if event == "speech_source":
            self.stop(); self.envelope = []; self.index = 0
            if self.decoder is None:
                self.decoder = QAudioDecoder(self)
                self.decoder.bufferReady.connect(self.read_buffer)
                self.decoder.error.connect(self.stop)
            self.decoder.setSource(QUrl.fromLocalFile(str(value))); self.decoder.start()
        elif event == "speaking":
            if value:
                self.started = time.monotonic(); self.timer.start()
            else: self.stop()

    def read_buffer(self):
        buffer = self.decoder.read(); fmt = buffer.format()
        types = {QAudioFormat.Int16: (np.int16,32768.), QAudioFormat.Int32: (np.int32,2147483648.),
                 QAudioFormat.Float: (np.float32,1.), QAudioFormat.UInt8: (np.uint8,128.)}
        if fmt.sampleFormat() not in types: return
        dtype, divisor = types[fmt.sampleFormat()]
        values = np.frombuffer(buffer.data(),dtype=dtype).astype(np.float64)
        if dtype == np.uint8: values -= 128
        values /= divisor
        step = max(1,int(fmt.sampleRate()*.04)*fmt.channelCount())
        for offset in range(0,len(values),step):
            chunk = values[offset:offset+step]
            level = min(1.,float(np.sqrt(np.mean(chunk*chunk)))*4)
            timestamp = buffer.startTime()/1_000_000 + offset/max(1,fmt.sampleRate()*fmt.channelCount())
            self.envelope.append((timestamp,level))

    def sample(self):
        if self.started is None or not self.envelope: return
        elapsed = time.monotonic()-self.started
        while self.index+1 < len(self.envelope) and self.envelope[self.index+1][0] <= elapsed:
            self.index += 1
        timestamp, level = self.envelope[self.index]
        self.bus.audio_level_changed.emit(level if abs(timestamp-elapsed) < .15 else 0.)

    def stop(self, *_):
        self.timer.stop(); self.started = None
        if self.decoder is not None: self.decoder.stop()
        self.bus.audio_level_changed.emit(0.)
