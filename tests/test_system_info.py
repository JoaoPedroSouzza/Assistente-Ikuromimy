from unittest.mock import MagicMock

from ui import system_info


def test_ram_converte_para_gb(monkeypatch):
    memoria = MagicMock(total=16 * 1024**3, used=10 * 1024**3, percent=62.5)
    monkeypatch.setattr(system_info.psutil, "virtual_memory", lambda: memoria)
    r = system_info.obter_ram()
    assert r == {"total": "16.0 GB", "uso": "62% em uso (10.0 GB)"}


def test_armazenamento_ignora_particoes_inacessiveis(monkeypatch):
    p1 = MagicMock(device="C:", mountpoint="/"); p2 = MagicMock(device="X:", mountpoint="/x")
    monkeypatch.setattr(system_info.psutil, "disk_partitions", lambda all=False: [p1,p2])
    uso = MagicMock(total=100*1024**3, used=50*1024**3, free=50*1024**3, percent=50)
    def disk(path):
        if path == "/x": raise PermissionError
        return uso
    monkeypatch.setattr(system_info.psutil, "disk_usage", disk)
    discos = system_info.obter_armazenamento()
    assert len(discos) == 1 and discos[0]["usado"] == "50% em uso"
