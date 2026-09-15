import math
import psutil
import shutil
import subprocess
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar

class HardwareWorker(QThread):
    updated = Signal(dict)
    def run(self):
        psutil.cpu_percent(None)
        nvidia = shutil.which("nvidia-smi")
        while not self.isInterruptionRequested():
            try:
                data = {"CPU": psutil.cpu_percent(None), "RAM": psutil.virtual_memory().percent, "GPU": None, "TEMP": None}
                if nvidia:
                    try:
                        result = subprocess.run([nvidia,"--query-gpu=utilization.gpu,temperature.gpu","--format=csv,noheader,nounits"],
                            capture_output=True, text=True, timeout=1.5,
                            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                        if result.returncode == 0:
                            gpu, temp = result.stdout.splitlines()[0].split(",")
                            data["GPU"], data["TEMP"] = float(gpu), float(temp)
                    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
                        pass
                sensors = getattr(psutil, "sensors_temperatures", lambda: {})()
                readings = [s.current for group in sensors.values() for s in group if s.current is not None]
                if readings and data["TEMP"] is None: data["TEMP"] = max(readings)
                self.updated.emit(data)
            except Exception:
                self.updated.emit({"CPU":None,"RAM":None,"GPU":None,"TEMP":None})
            for _ in range(20):
                if self.isInterruptionRequested(): return
                self.msleep(100)

class SystemMonitor(QFrame):
    def __init__(self, engine, bus, parent=None):
        super().__init__(parent)
        self.setObjectName("glass")
        self.setMinimumHeight(256)
        self.engine = engine
        self.values, self.targets, self.labels, self.bars = {}, {}, {}, {}
        area = QVBoxLayout(self); area.setContentsMargins(18,18,18,18); area.setSpacing(8)
        title = QLabel("TELEMETRIA"); title.setObjectName("eyebrow"); title.setMinimumHeight(20); area.addWidget(title)
        for key in ("CPU", "RAM", "GPU", "TEMP"):
            row = QHBoxLayout(); row.addWidget(QLabel(key)); row.addStretch()
            value = QLabel("—"); value.setMinimumHeight(20); self.labels[key] = value; row.addWidget(value); area.addLayout(row)
            bar = QProgressBar(); bar.setTextVisible(False); bar.setRange(0,100)
            bar.setValue(0); self.bars[key] = bar; area.addWidget(bar)
        note = QLabel("— sensor indisponível"); note.setObjectName("muted"); area.addWidget(note)
        bus.hardware_updated.connect(self.receive)
        engine.frame.connect(self.advance)

    def receive(self, data):
        self.targets = data
        for key, value in data.items():
            if value is None: self.labels[key].setText("—"); self.bars[key].setValue(0)
            elif key not in self.values: self.values[key] = float(value)
        if self.engine.quality == "Desativado": self.advance(1.)

    def advance(self, dt):
        if not self.isVisible(): return
        for key, target in self.targets.items():
            if target is None: continue
            self.values[key] += (target-self.values[key])*(1-math.exp(-dt*5))
            value = round(self.values[key])
            self.labels[key].setText(f"{value}" + (" °C" if key == "TEMP" else "%"))
            self.bars[key].setValue(max(0,min(100,value)))
