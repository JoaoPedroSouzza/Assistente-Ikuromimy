# Assistente Virtual Ikuromimy

Assistente virtual para Windows com comandos por voz/texto, interface
gráfica em PySide6, controle remoto via app Android, e automações do
dia a dia: tocar música no Spotify, abrir/fechar programas, pesquisar
na web, controlar mídia e volume, entre outros.

## Funcionalidades
- 🤖 **Assistente IA local (Jarvis)**: chat conversacional via [Ollama](https://ollama.com), gratuito e local, sem chave de API.
- 🎤 **Comandos de voz**: botão de microfone (grava e transcreve) ou escuta contínua com palavra de ativação — diga o nome do assistente antes do comando pra ele reagir.
- ✏️ **Nome do assistente configurável**: troque a palavra de ativação pra qualquer nome (ex: "Jarvis").
- 📐 **Sidebar retrátil**: menu lateral recolhe automaticamente e expande com animação ao passar o mouse.
- 🎙 **Comandos por texto**: digite comandos livres como `abrir spotify`, `tocar bohemian rhapsody`, `pesquisar receita de bolo`, `fechar chrome`.
- 🔘 **Atalhos pré-definidos**: botões na tela que executam um comando pronto com um clique só. Vem com atalhos padrão e dá pra criar, **editar** e remover os seus próprios — inclusive os padrão.
- 🧩 **Modos**: grupos de até 5 comandos que executam em sequência com um clique (ex: "Modo Programador" abre VSCode + Spotify + Chrome de uma vez). Editáveis e removíveis pelo clique direito.
- 💬 **Autocompletar**: sugestões enquanto você digita, baseadas no histórico de comandos, nas palavras-chave conhecidas e nos apps já instalados no PC.
- 🔧 **Autocorreção**: erros de digitação no comando (ex: "abrri" em vez de "abrir") são detectados e corrigidos automaticamente.
- 🎵 **Controle de música**: toca qualquer música pesquisando direto no Spotify, com play/pause, próxima/anterior faixa, e **volume em ±10% exatos** (via Core Audio do Windows, mais preciso que as teclas de mídia).
- 🖼 **Música tocando agora**: título, artista e capa do álbum aparecem automaticamente na aba Música (capa via API pública do iTunes, sem cadastro nem chave de API).
- 🚀 **Abertura de qualquer app instalado**: indexa automaticamente os atalhos do Menu Iniciar e o registro do Windows (`App Paths`).
- 🎮 **Jogos via protocolo** (Steam, extensível pra outros launchers).
- 🌐 **Pesquisa no navegador**: com suporte a escolher o motor de busca no próprio comando (`pesquisar no youtube ...`).
- 💻 **Painel de Sistema**: mostra processador, RAM, placa de vídeo e armazenamento do PC.
- 📱 **Controle remoto via Android**: app nativo separado que manda comandos pro PC pela rede Wi-Fi (play/pause, comando livre, etc.), com autenticação por chave de acesso.
- 🎨 **Tema personalizável**: roda de cores (estilo HSV) gera um esquema monocromático completo pro app, salvo entre sessões.
- 🔊 **Fala (text-to-speech)**: o assistente responde em voz alta usando gTTS.
- ▶ **Inicialização automática com o Windows** (opcional, configurável na interface).
- 🔄 **Atualizador embutido**: botão "Atualizar Assistente" na aba Sistema verifica, baixa e instala a versão mais recente sozinho, direto pelos Releases do GitHub.

## Instalação

### Pré-requisitos

- Windows 10/11
- [Python 3.10+](https://python.org) (marcar "Add to PATH" no instalador)

### Rodando a partir do código

```powershell
git clone https://github.com/sankaito/Assistente-Ikuromimy.git
cd Assistente-Ikuromimy

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python interface.py
```

### Gerando o executável (.exe)

```powershell
build.bat
```

Isso gera `dist\Assistente Virtual Ikuromimy.exe` — standalone, não
depende de Python instalado pra rodar.

```powershell
python criar_atalho.py
```

Cria um atalho na Área de Trabalho apontando pro `.exe`.

## Como usar

Digite comandos no campo de texto, clique num atalho pré-definido, ou
crie um Modo pra disparar vários comandos de uma vez. Alguns exemplos:

| Comando                          | O que faz                                  |
|-----------------------------------|---------------------------------------------|
| `abrir spotify`                   | Abre o Spotify (ou qualquer outro app)      |
| `tocar bohemian rhapsody`         | Pesquisa e toca a música no Spotify         |
| `fechar chrome`                   | Fecha o processo do Chrome                  |
| `pesquisar receita de bolo`       | Abre o navegador já pesquisando             |
| `pesquisar no youtube lofi`       | Pesquisa direto no YouTube                  |
| `play` / `pause`                  | Play/pause da faixa atual                   |
| `próxima` / `anterior`            | Pula/volta faixa                            |
| `aumentar volume` / `diminuir volume` | Ajusta o volume do sistema (tecla de mídia) |
| `atualizar apps`                  | Reindexação dos apps instalados             |
| `sair`                            | Encerra o assistente                        |

## Estrutura do projeto

projeto/
├── interface.py # ponto de entrada da interface gráfica
├── escravo.py # lógica de processamento de comandos
├── requirements.txt # dependências Python
├── ikuro.spec # receita de empacotamento (PyInstaller)
├── build.bat # gera o .exe
├── criar_atalho.py # cria atalho na Área de Trabalho
├── CHANGELOG.md # histórico de versões
│
└── ui/
├── main_window.py # janela principal
├── sidebar.py # menu lateral
├── theme_manager.py # geração/persistência de tema
├── shortcuts_manager.py # atalhos (criar/editar/remover)
├── modes_manager.py # modos (criar/editar/remover)
├── modes_dialog.py # caixa de criação/edição de modos
├── modes_executor.py # roda os comandos de um modo
├── command_history.py # histórico p/ autocompletar
├── system_info.py # coleta info de hardware
├── audio_control.py # volume preciso (COM/comtypes)
├── media_info.py # música tocando + capa (iTunes)
├── media_info_worker.py # poller em thread separada
├── updater.py # verifica/baixa atualização
├── updater_worker.py # roda em thread separada
├── remote_server.py # servidor do controle remoto
├── remote_config.py # token do controle remoto
├── startup_manager.py # inicialização com o Windows
│
└── pages/
├── home_page.py # comando livre + atalhos
├── music_page.py # controle de mídia + capa
├── modes_page.py # aba de Modos
├── settings_page.py # tema + inicialização
├── system_page.py # painel de hardware + updater
└── remote_page.py # controle remoto (IP/token)


## App Android (Controle Remoto)

Dentro da pasta `IkuromimyRemoto/` está o projeto completo do Android
Studio (Kotlin) do app de controle remoto. Abra a pasta no Android
Studio, deixe sincronizar o Gradle, e rode ou gere o `.apk`. Na aba
"Controle Remoto" do app no PC aparece o endereço e a chave de acesso
que o app Android precisa pra conectar.

## Versionamento

O projeto segue [Versionamento Semântico](https://semver.org/lang/pt-BR/).
Veja o histórico completo de mudanças no [CHANGELOG.md](CHANGELOG.md).

Versão atual: **1.12.0**

## Aviso

Esse assistente automatiza o teclado/mouse do sistema (via
`pyautogui`) pra algumas funções, como buscar músicas no app do
Spotify. Use por sua conta e risco, e evite mexer no PC enquanto um
comando estiver em execução.

Versão atual: **1.17.1**

## Testes automáticos

Execute `testar.bat`. Veja [TESTES.md](TESTES.md) para instalação, isolamento, relatórios e CI.

## Engenharia e validação atual

Veja [PIPELINE.md](PIPELINE.md) para as etapas 2 a 10, resultados, logging e CI/CD.
