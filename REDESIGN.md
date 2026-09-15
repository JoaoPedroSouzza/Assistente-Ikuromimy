# Interface reativa da Ikuromimy

## Executar

Na raiz desta pasta, com as dependências instaladas:

```powershell
python interface.py
```

Se estiver usando o ambiente criado por `testar.bat`:

```powershell
.\.venv-testes\Scripts\python.exe interface.py
```

O executável de uma versão anterior não contém este redesign. Para gerar um novo,
use `build.bat`; este pacote entrega o código-fonte, não um EXE reconstruído.

## Direção visual e arquitetura

A imagem fornecida foi usada como referência para as curvas de nível orgânicas,
não incorporada como bitmap. O aplicativo continua em PySide6/Qt Widgets.
Antes da implementação foram mapeados a janela, sidebar, oito páginas existentes,
workers, comandos, persistência, estilos e testes. A proposta adotada foi adicionar
uma camada visual desacoplada ao núcleo, preservando as interfaces existentes.

- `core/visual_events.py`: notificações opcionais, independentes de Qt, com proteção
  entre threads e isolamento de falhas nos observadores.
- `ui/state/`: estados IDLE, LISTENING, THINKING, SPEAKING, EXECUTING, SUCCESS,
  ERROR e OFFLINE; sinais Qt fazem a ponte para a thread da interface.
- `ui/animations/`: um relógio compartilhado com delta time e orçamento por qualidade.
- `ui/theme/`: AccentColor, cores por seção, transição progressiva e personalização.
- `ui/effects/`: campo topográfico vetorial, geometria em cache e envelope de áudio.
- `ui/components/`: núcleo, barra de comandos, central de comandos, telemetria e
  resposta visual dos botões ao pressionar.
- `ui/main_window.py`: composição e conexão dos componentes; páginas antigas
  continuam responsáveis por suas funcionalidades.

## O que mudou

- Fundo escuro com dezenas de curvas procedurais, movimento orgânico, parallax do
  mouse, deformação por áudio e pulsos ligados à execução. Não depende de Internet.
- Núcleo central com respiração, contornos, anéis e partículas; reação aos estados
  reais de comando, geração de resposta, escuta e reprodução de fala.
- Ciano no início, roxo nas conversas, rosa na música, verde nos atalhos, laranja
  nos modos, violeta nos amigos e tons frios em sistema, remoto e configurações.
  As cores se propagam pelas linhas em vez de trocar instantaneamente.
- Painéis translúcidos com bordas discretas. O efeito de vidro usa transparência;
  não foi aplicado desfoque Acrylic/Mica do compositor do Windows.
- Sidebar retrátil com seleção visível. A aba Atalhos apresenta o editor que já
  existia no início, mantendo criar, editar, remover e executar atalhos.
- Barra inferior disponível em todas as páginas: comandos, perguntas, microfone,
  arquivos de texto e sugestões que mudam com o contexto.
- Ctrl + Espaço abre a central de comandos em qualquer página do aplicativo.
  Setas selecionam, Enter confirma e Esc fecha. É um atalho da janela ativa,
  não um atalho global do Windows quando outro aplicativo está em foco.
- Anexos UTF-8 de até 128 KiB entram como rascunho na conversa. Revise e clique
  Enviar. Arquivos binários, PDF e imagens não recebem interpretação neste fluxo.
- Telemetria de CPU/RAM com interpolação; GPU e temperatura NVIDIA via
  `nvidia-smi` quando disponível; temperaturas de outros sensores via psutil
  quando o sistema as expõe. Ausência de sensor aparece como `—`.
- Atividade recente limitada a quatro eventos, acesso às páginas de música,
  amigos e modos. Não foram inventados contadores nem uma nova agenda de tarefas.
- Modo ambiente após 75 segundos ocioso no início: painéis secundários desaparecem
  gradualmente, mantendo núcleo e fundo. Mouse, teclado e wake word restauram a UI.
- Personalização de cor por página e nível de efeitos persistidos em QSettings.
- Cliques têm leve contração visual; navegação muda a energia do cenário.
- A saudação da wake word passa a usar um worker, sem executar o TTS na GUI.

## Funcionalidades preservadas

Música e volume, instalação/configuração do Ollama, seleção de modelos, streaming
do chat, nome do assistente, voz e escuta contínua, confirmação de comandos
sugeridos pela IA, amigos/Firebase, modos editáveis, controle remoto, informações
do sistema, personalização do tema, inicialização com Windows e atualização.
O histórico e os atalhos existentes continuam usando suas rotinas de persistência.

## Áudio e desempenho

O microfone emite RMS real dos blocos capturados; a escuta contínua também fornece
níveis. A fala sintetizada usa PCM decodificado pelo Qt quando o codec está
 disponível. A sincronização desse envelope com `playsound` é aproximada, porque
esse backend não expõe a posição de reprodução. Se a decodificação falhar, não
se fabrica uma amplitude: permanecem as animações de estado.
A transcrição de voz já existente continua usando o serviço online do Google.

- Alto: alvo de aproximadamente 60 atualizações/s, 22 curvas por grupo.
- Médio (padrão): 30 atualizações/s, 16 curvas por grupo.
- Baixo: 20 atualizações/s, 9 curvas por grupo e menos partículas.
- Desativado: nenhum timer contínuo de animação; estado, cor e telemetria continuam
  atualizando quando chegam eventos.

A geometria do fundo é vetorizada com NumPy e atualizada no máximo a 30/20/12 Hz,
conforme qualidade; quadros intermediários reutilizam o cache. A cor continua
interpolando no relógio da animação. Animações param quando a janela é ocultada ou
minimizada e componentes invisíveis não fazem atualização de desenho.

Os limites são metas, não garantia de 60 FPS em qualquer PC. As medições de captura
incluem desenho e cópia da janela e não representam FPS real no monitor. O teste
nativo de visualização foi feito sem abrir uma janela na tela nem executar ações
externas. Algumas consultas legadas de configuração continuam síncronas.

## Validação

Resultado final: **260 testes passaram**, processo encerrou com código **0**,
cobertura combinada **73,51%**, análise AST de **66 arquivos sem achados** e
`--self-test` do código-fonte com código **0**. Ruff e Actions não foram executados
nesta etapa. Há um aviso externo da dependência `standard-aifc`.

A suíte inclui regressões existentes e testes novos de estados, cores, navegação,
comandos concorrentes, anexos, modo ambiente, pausa de animação, renderização,
amplitude PCM e contrato da telemetria. Os efeitos externos são isolados nos testes.
Veja `reports-redesign/testes.log`, `junit.xml` e `coverage/index.html`.
O teste `interface.py --self-test` valida imports e recurso QSS, não toda a GUI.
A análise AST local é complementar ao Ruff configurado no CI; não substitui auditoria.
Nenhum commit ou push foi feito automaticamente para este redesign.

## GitHub

`reports-redesign/`, ambientes, caches, logs e executáveis continuam ignorados.
Foram retirados apenas do índice do Git os 12 arquivos `.pyc` que estavam rastreados;
os arquivos locais foram preservados. O próximo commit registrará essa limpeza.
O arquivo `PIPELINE.md` documenta a etapa anterior; este documento descreve o redesign.
