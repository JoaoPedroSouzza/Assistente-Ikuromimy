# Changelog — Assistente Virtual Ikuromimy

Todas as mudanças notáveis do projeto, organizadas por versão.
Segue [Versionamento Semântico](https://semver.org/lang/pt-BR/):
`MAJOR.MINOR.PATCH`

- **MAJOR**: mudança grande o suficiente pra quebrar algo que já existia
- **MINOR**: funcionalidade nova, sem quebrar o que já funcionava
- **PATCH**: correção de bug, sem mudar o comportamento esperado

---
## [1.15.0] — Comandos de voz

### Adicionado
- **Comando de voz por botão** (`ui/voice_input.py`, `ui/voice_worker.py`):
  clica no 🎤 na aba IA, fala por até 6 segundos, o texto reconhecido
  (via reconhecedor gratuito do Google, sem chave de API) vira
  mensagem automaticamente.
- **Escuta contínua com palavra de ativação** (`ui/wake_word_listener.py`,
  `ui/wake_word_worker.py`): liga o "🎙 Ouvir sempre" e o app fica
  sempre escutando em segundo plano (detecção de fala por energia de
  áudio, sem motor de wake-word pago). Só age em frases que começam
  com "assistente" — dizer só "assistente" faz ele responder "Olá, o
  que deseja?" e esperar a próxima frase como comando.
- **Execução de comando mais confiável**: antes de mandar qualquer
  texto pra IA, o app checa se já bate com um comando direto conhecido
  (`escravo.eh_comando_conhecido()`) e executa na hora — sem depender
  do modelo de IA formatar uma tag de comando corretamente. A IA só é
  acionada de verdade pra conversa/comandos ambíguos.

## [1.14.0] — Assistente IA local (Jarvis)

### Adicionado
-🤖 Aba IA nova : assistente conversacional local via Ollama (gratuito, sem chave de API, sem custo).
🧭 Fluxo guiado dentro do app : detecta se o Ollama está instalado/rodando/com modelo baixado, e mostra o botão certo pra cada passo que faltar — sem necessidade de programas terceiros
🎤 Comando de voz por botão : clica no microfone, fala, o texto vira mensagem automaticamente.
🎙 Escuta contínua com palavra de ativação : liga o "Ouvir sempre" e ele te ouve o tempo todo, mas só age quando chamado pelo nome "assistente" , após dizer seu nome, diga o pedido
⚙️ A IA consegue executar comandos reais do assistente durante uma conversa (abrir programas, tocar música, etc.).

## [1.13.8] — Bugfix

### Corrigido
- **Causa raiz definitiva** do "Failed to load Python DLL" no
  atualizador: o processo filho (o `.exe` novo, lançado de dentro do
  próprio app já empacotado) herdava variáveis de ambiente
  contaminadas do processo pai (PyInstaller onefile), fazendo o
  bootloader dele falhar ao carregar a DLL do Python. Corrigido
  reconstruindo um ambiente totalmente limpo do zero pro processo
  filho (`_ambiente_limpo()`), em vez de tentar remover variáveis
  pontuais. Confirmado funcionando de ponta a ponta.


## [1.13.5] — Bugfix (tentativa)

### Corrigido
- Adicionada pausa de 5s entre copiar o `.exe` novo e abrir ele,
  suspeitando de corrida com o antivírus escaneando o arquivo. Testado
  com exclusões do Windows Defender — não resolveu sozinho (causa real
  só foi encontrada na 1.13.8).

## [1.13.5] — Bugfix (tentativa)

### Corrigido
- "Failed to load Python DLL" persistia mesmo com o `.exe` confirmado
  íntegro (abria normal manualmente, só falhava vindo do atualizador).
  Suspeita: corrida com o Windows Defender ainda escaneando o arquivo
  recém-copiado no exato momento em que o script tentava abri-lo.
  Adicionada uma pausa de 5s entre terminar a cópia e abrir o app, pra
  dar tempo do antivírus soltar o arquivo. **Diagnóstico best-effort**
  — sem confirmação ainda de que resolve 100%.

## [1.13.4] — Bugfix

### Corrigido
- O atualizador aplicava um `.exe` baixado incompleto/corrompido sem
  perceber, resultando em "Failed to load Python DLL" ao reabrir.
  Agora `baixar_atualizacao()` confere o tamanho do arquivo baixado
  contra o esperado, e tenta baixar de novo automaticamente (até 3x)
  se vier corrompido, antes de desistir e avisar que falhou — em vez
  de aplicar um arquivo quebrado silenciosamente.

## [1.13.3] — Bugfix

### Corrigido
- O `.bat` de atualização abria uma janela de console travada (presa
  no comando `find`) em vez de rodar escondido — causado pela flag
  `DETACHED_PROCESS`, que quebra o pipe entre `tasklist` e `find` e faz
  o Windows abrir um console visível do nada. Removida a checagem via
  `tasklist`/`find` (não é mais necessária, já que a cópia já tenta de
  novo sozinha) e trocada a flag pra `CREATE_NO_WINDOW`, que esconde a
  janela sem quebrar os comandos internos do script.

## [1.13.2] — Bugfix

### Corrigido
- O atualizador baixava, fechava o app, mas não reabria: a cópia do
  `.exe` novo por cima do antigo podia falhar silenciosamente numa
  corrida com o Windows/antivírus ainda segurando o arquivo travado
  logo após o processo antigo encerrar. Agora o script de atualização
  tenta de novo automaticamente (até 10 vezes) e grava um log em
  `%TEMP%\atualizar_ikuromimy.log` pra diagnóstico, caso volte a falhar.

## [1.13.1] — Bugfix

### Corrigido
- O atualizador embutido dizia "já está atualizado" mesmo quando a
  verificação tinha **falhado de verdade** (sem internet, erro na API
  do GitHub, Release sem `.exe` anexado) — as duas situações caíam na
  mesma mensagem, escondendo o problema. Agora `verificar_atualizacao()`
  distingue erro de "realmente atualizado", mostrando o motivo exato
  quando algo dá errado.

## [1.13.0] — Janela customizada

### Adicionado
- **Barra de título customizada** (`ui/title_bar.py`), substituindo a
  barra padrão do Windows — combina com o tema escolhido, com botões
  de minimizar/maximizar/fechar estilizados. Arrastar/encaixar a
  janela usa a API nativa do Qt6 (`startSystemMove`).
- **Ícone do app** aplicado corretamente na barra de tarefas e no
  canto da barra de título (antes só estava no `.exe`/atalho, não
  aparecia enquanto o app estava aberto).
- "Puxador" no canto inferior direito pra redimensionar a janela
  (necessário porque janela sem moldura não vem com isso de graça).

### Trade-offs conhecidos
- Perde a sombra nativa do Windows 11 e o menu de "snap" ao pairar
  sobre o botão de maximizar — limitações inerentes de janelas sem
  moldura no Qt/Windows.

## [1.12.0] — Atualizador embutido

### Adicionado
- Botão **"🔄 Atualizar Assistente"** na aba Sistema: verifica a versão
  mais recente nos Releases do GitHub (`ui/updater.py`), e se tiver
  uma nova, pergunta e baixa o `.exe` sozinho, substituindo o atual e
  reabrindo o app automaticamente — sem precisar procurar manualmente.
- Download e verificação rodam numa thread separada
  (`ui/updater_worker.py`), com barra de progresso, sem travar a
  interface.
- Aba Música: botões de **volume em ±10% exatos** (`ui/audio_control.py`,
  via pycaw/Core Audio do Windows — mais preciso que as teclas de
  mídia, que sobem/descem um valor fixo do driver).
- Aba Música: mostra **título, artista e capa do álbum** da música
  tocando no momento no Spotify (`ui/media_info.py`) — o título/artista
  vêm do título da janela, e a capa vem da API pública gratuita do
  iTunes (sem chave de API, sem cadastro, funciona pra qualquer pessoa
  que baixar o app, sem setup nenhum). Atualizado a cada poucos
  segundos em segundo plano (`ui/media_info_worker.py`).
- **Editar atalhos e modos**: clique direito em qualquer atalho ou
  modo — inclusive os que já vêm prontos por padrão — pra editar ou
  remover. Antes só dava pra remover os criados manualmente; agora
  tudo é um registro igual, com ID interno estável.

## [1.11.0] — Modos

### Adicionado
- Aba **Modos** nova: grupos de até 5 comandos que rodam em sequência
  com um clique só (ex: "🧑‍💻 Modo Programador" abre VSCode + Spotify
  + Claude de uma vez), executados numa thread separada
  (`ui/modes_executor.py`) pra não travar a interface.
- Botão **"+ Criar modo"** abre uma caixa (`ui/modes_dialog.py`) com
  campo de nome e campos de comando, com "+ Adicionar comando" até o
  limite de 5. Clique direito num modo existente remove ele.
- Modos salvos entre sessões (`ui/modes_manager.py`, mesmo mecanismo
  de persistência dos atalhos).

## [1.10.0] — Atalhos e autocompletar

### Adicionado
- Botões de **atalhos pré-definidos** na aba Início: um clique executa
  um comando pronto, sem digitar. Vem com 5 atalhos padrão (Spotify,
  Chrome, Pesquisar, Play/Pause, Próxima) e dá pra adicionar/remover
  os seus próprios (`ui/shortcuts_manager.py`), salvos entre sessões.
- **Autocompletar** no campo de comando (`QCompleter`): sugere com
  base no histórico de comandos já digitados, nas palavras-chave
  conhecidas e nos apps instalados indexados pelo `escravo.py`.
- **Autocorreção de comandos**: se a primeira palavra não bater com
  nenhum gatilho conhecido (ex: "abrri" em vez de "abrir"), tenta
  achar a mais parecida via `difflib` e executa o comando corrigido,
  avisando o que interpretou.
- `escravo.listar_apps_conhecidos()`: expõe a lista de apps indexados
  pra outras partes do app (interface, controle remoto) sugerirem.

## [1.9.1] — Bugfix

### Corrigido
- Tela de conexão do app Android aceitava qualquer chave (o endpoint
  `/ping` não exigia token), fazendo o app achar que tinha conectado
  mesmo com a chave errada — o erro só aparecia depois, ao tentar
  executar um comando de verdade. Agora `/ping` também exige o token
  correto.

## [1.9.0] — Controle Remoto via Android

### Adicionado
- Servidor HTTP local (`ui/remote_server.py`, Flask + werkzeug) rodando
  dentro do app, com endpoints pra receber comandos do celular
  (`/comando`, `/midia/<ação>`, `/sistema`, `/ping`), protegido por
  token de acesso.
- Aba **Controle Remoto** no PC: mostra IP:porta + chave de acesso,
  liga/desliga o servidor.
- App Android nativo (Kotlin, projeto Android Studio completo) com
  tela de conexão e tela de controle (play/pause/próxima/anterior +
  campo de comando livre).
- Inicialização automática com o Windows (checkbox em Configurações,
  `ui/startup_manager.py`).

## [1.8.2] — Bugfix

### Corrigido
- Player iniciava a música e pausava logo em seguida: o `Enter` já
  dava play sozinho no Spotify, e um `media_play_pause()` extra que eu
  tinha adicionado no passo anterior acabava desligando o play que já
  tinha começado. Removido o toggle extra.

## [1.8.1] — Bugfix

### Corrigido
- Comando "tocar" selecionava a **segunda** música do dropdown de
  busca do Spotify em vez da primeira — o código mandava um `"down"`
  extra antes do `"enter"`, pulando o item já destacado por padrão.

## [1.8.0] — Empacotamento e distribuição

### Adicionado
- Empacotamento como `.exe` standalone via PyInstaller (`ikuro.spec`,
  `build.bat`), não depende mais de VS Code/Python instalado.
- Script `criar_atalho.py`: gera atalho na Área de Trabalho.
- Ícone customizado (`icon.ico`) aplicado no `.exe` e no atalho.
- App renomeado de "Ikuro Assistant" pra **"Assistente Virtual
  Ikuromimy"** (título da janela, nome do `.exe`, atalho, configs
  salvas).

### Corrigido
- Caminho relativo do `styles/dark.qss` quebrava dentro do `.exe`
  empacotado (`FileNotFoundError`); agora resolve via `sys._MEIPASS`
  e o arquivo é incluído nos `datas` do `.spec`.
- Aba Sistema tinha sido criada mas nunca conectada no
  `main_window.py`, caindo sempre na tela de Início.

## [1.7.0] — Página Sistema

### Adicionado
- Aba **Sistema**: mostra processador, núcleos, RAM, placa(s) de
  vídeo e armazenamento (`ui/system_info.py` via WMI/psutil,
  `ui/pages/system_page.py`), com botão de atualizar.

## [1.6.0] — Tema personalizável

### Adicionado
- Aba **Configurações**: roda de cores estilo HSV (`ColorWheel` em
  `ui/widgets.py`), gera um esquema monocromático completo (fundo,
  cards, bordas, destaque) a partir de uma cor escolhida
  (`ui/theme_manager.py`), com slider de brilho, campo hex e paleta
  de 5 tons clicáveis. Tema salvo entre sessões via `QSettings`.

## [1.5.0] — Interface gráfica multi-página

### Adicionado
- Estrutura de páginas com `QStackedWidget` (`ui/main_window.py`)
  substituindo a janela única original.
- Sidebar emitindo sinal (`pagina_selecionada`) ao clicar em cada
  botão.
- Aba **Música**: botões ⏮ Anterior / ⏯ Play-Pause / ⏭ Próxima,
  ligados nas teclas de mídia do sistema.

## [1.1.0] — Comando de pesquisa

### Adicionado
- Comando `pesquisar` / `pesquisa` / `buscar` no `escravo.py`: abre o
  navegador já pesquisando o termo (Google por padrão, com suporte a
  trocar de motor no próprio comando, ex: "pesquisar no youtube ...").

## [1.0.0] — Base

### Adicionado
- `escravo.py`: assistente de comandos por voz/texto — abrir/fechar
  programas, tocar música no Spotify, controle de mídia, volume,
  index de aplicativos instalados via atalhos + registro do Windows.
