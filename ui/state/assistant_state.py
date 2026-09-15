from enum import Enum
class AssistantState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    EXECUTING = "executing"
    SUCCESS = "success"
    ERROR = "error"
    OFFLINE = "offline"

LABELS = {
    AssistantState.IDLE: "Aguardando você",
    AssistantState.LISTENING: "Estou ouvindo...",
    AssistantState.THINKING: "Pensando...",
    AssistantState.SPEAKING: "Falando...",
    AssistantState.EXECUTING: "Executando",
    AssistantState.SUCCESS: "Concluído",
    AssistantState.ERROR: "Algo precisa de atenção",
    AssistantState.OFFLINE: "Modelo local indisponível",
}
