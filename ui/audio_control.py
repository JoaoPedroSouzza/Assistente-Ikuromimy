"""
Controle preciso de volume do sistema via COM (Core Audio do Windows)
implementado direto com comtypes, sem depender de nenhuma classe
interna do pycaw — a forma como o pycaw expõe isso mudou entre
versões (GetSpeakers() e depois MMDeviceEnumerator deixaram de
funcionar do jeito esperado), então aqui declaramos as interfaces COM
do Windows nós mesmos, usando os identificadores oficiais da
Microsoft — esses NUNCA mudam, são parte do contrato do sistema
operacional, então isso não deve quebrar de novo por causa de
atualização de biblioteca.
"""

from __future__ import annotations

from ctypes import HRESULT, POINTER, c_float, c_void_p, cast
from ctypes.wintypes import DWORD

import comtypes
from comtypes import COMMETHOD, GUID, IUnknown

CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_IMMDeviceEnumerator = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
IID_IMMDevice = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
IID_IAudioEndpointVolume = GUID("{5CDF2C82-841E-4546-9722-0CF74078229A}")

EDATAFLOW_ERENDER = 0
EROLE_EMULTIMEDIA = 1


class IMMDevice(IUnknown):
    _iid_ = IID_IMMDevice
    _methods_ = [
        COMMETHOD(
            [], HRESULT, "Activate",
            (["in"], POINTER(GUID), "iid"),
            (["in"], DWORD, "dwClsCtx"),
            (["in"], c_void_p, "pActivationParams"),
            (["out"], POINTER(c_void_p), "ppInterface"),
        ),
    ]


class IMMDeviceEnumerator(IUnknown):
    _iid_ = IID_IMMDeviceEnumerator
    _methods_ = [
        COMMETHOD([], HRESULT, "EnumAudioEndpoints"),
        COMMETHOD(
            [], HRESULT, "GetDefaultAudioEndpoint",
            (["in"], DWORD, "dataFlow"),
            (["in"], DWORD, "role"),
            (["out"], POINTER(POINTER(IMMDevice)), "ppEndpoint"),
        ),
    ]


class IAudioEndpointVolume(IUnknown):
    _iid_ = IID_IAudioEndpointVolume
    _methods_ = [
        COMMETHOD([], HRESULT, "RegisterControlChangeNotify"),
        COMMETHOD([], HRESULT, "UnregisterControlChangeNotify"),
        COMMETHOD([], HRESULT, "GetChannelCount"),
        COMMETHOD([], HRESULT, "SetMasterVolumeLevel"),
        COMMETHOD(
            [], HRESULT, "SetMasterVolumeLevelScalar",
            (["in"], c_float, "fLevel"),
            (["in"], POINTER(GUID), "pguidEventContext"),
        ),
        COMMETHOD([], HRESULT, "GetMasterVolumeLevel"),
        COMMETHOD(
            [], HRESULT, "GetMasterVolumeLevelScalar",
            (["out"], POINTER(c_float), "pfLevel"),
        ),
    ]


def _obter_interface_volume():
    comtypes.CoInitialize()

    enumerador = comtypes.CoCreateInstance(
        CLSID_MMDeviceEnumerator,
        IMMDeviceEnumerator,
        comtypes.CLSCTX_INPROC_SERVER,
    )

    dispositivo = enumerador.GetDefaultAudioEndpoint(EDATAFLOW_ERENDER, EROLE_EMULTIMEDIA)

    ponteiro_bruto = dispositivo.Activate(
        IID_IAudioEndpointVolume, comtypes.CLSCTX_INPROC_SERVER, None
    )
    return cast(ponteiro_bruto, POINTER(IAudioEndpointVolume))


def obter_volume_percentual() -> int:
    volume = _obter_interface_volume()
    return round(volume.GetMasterVolumeLevelScalar() * 100)


def definir_volume_percentual(percentual: int) -> int:
    percentual = max(0, min(100, percentual))
    volume = _obter_interface_volume()
    volume.SetMasterVolumeLevelScalar(percentual / 100, None)
    return percentual


def alterar_volume(delta: int) -> int:
    """Soma (ou subtrai, se delta for negativo) pontos percentuais do
    volume atual. Devolve o volume resultante, já limitado a 0-100."""
    atual = obter_volume_percentual()
    return definir_volume_percentual(atual + delta)
