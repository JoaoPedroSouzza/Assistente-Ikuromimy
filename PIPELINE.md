# Engenharia do Ikuromimy — etapas 2 a 10

As etapas foram aplicadas na ordem solicitada ao projeto desta pasta, preservando
as APIs de `escravo.py`. Esta é uma evolução incremental do assistente, não uma
reescrita completa nem uma certificação de segurança.

| Etapa | Trabalho realizado | Evidência |
|---|---|---|
| 2. Profiling | cProfile da suíte original e benchmark de interpretação | JSON e arquivos `.prof` em `reports-pipeline/` |
| 3. Arquitetura | Núcleo puro, coordenação de execução e adaptadores Qt/Windows | `ARQUITETURA.md`, `core/` |
| 4. Refatoração | Interpretação extraída de `escravo.py`, com exports compatíveis | Suíte de regressão |
| 5. Threads/assíncrono | Comandos da Home/IA em workers; cancelamento cooperativo; prevenção de tarefas duplicadas | Testes de responsividade, serialização e cancelamento |
| 6. Segurança | Novas chaves de 128 bits, comparação segura, limites HTTP, erros remotos genéricos, remoção do shell com texto livre e confirmação de comando sugerido pela IA | Testes negativos de entrada e execução |
| 7. Logging | Logs locais rotativos, ID de operação, duração e tipo de erro; redação de credenciais | Testes do formatter e da configuração |
| 8. Otimização | Cache limitado da autocorreção, histórico sem regravar duplicata, reuso do modelo de sugestões | Benchmark e testes de persistência/modelo |
| 9. Análise estática | AST/symtable local; Ruff configurado no CI | 48 arquivos, zero achados locais |
| 10. CI/CD | Matriz de testes, análise, build após checks, smoke test e checksum do artefato | Workflow e build local validado |

## Resultados medidos

- **249 testes passaram**, sem falhas, erros ou testes ignorados.
- Cobertura de linhas: **71.38%**; ramificações: **57.38%**;
  cobertura combinada: **69.02%**. Mínimo exigido: 65%.
- Benchmark: 6.000 classificações por execução, cinco repetições, mesmas frases:
  mediana **0.444 s → 0.291 s**,
  redução de **34.5%** nesse cenário. Isso não mede velocidade de Spotify,
  microfone, rede nem o desempenho global do aplicativo.
- Build Windows gerado com PyInstaller; `--self-test` do executável retornou
  **0**, verificando imports e o recurso QSS sem iniciar janela/comandos.
- Há um aviso de compatibilidade da dependência `standard-aifc` com Python 3.14;
  a execução não apresentou os avisos anteriores de desconexão de sinais Qt.

## Como verificar

Na pasta do projeto, execute:

```powershell
.\testar.bat
.\.venv-testes\Scripts\python.exe -X utf8 scripts/analisar.py
.\.venv-testes\Scripts\python.exe -X utf8 scripts/profiling.py . reports-pipeline/benchmark-novo.json
```

Para o Ruff, em um ambiente com acesso aos pacotes:

```powershell
.\.venv-testes\Scripts\python.exe -m pip install -r requirements-quality.txt
.\.venv-testes\Scripts\python.exe -m ruff check core ui escravo.py interface.py
```

O Ruff **não foi executado localmente**, pois não estava no cache e a instalação
não funcionou neste ambiente. A análise AST/symtable verifica sintaxe compatível
com Python 3.10, nomes globais, except sem tipo, eval/exec, shell=True e ausência
de timeout HTTP. Ela não substitui um type checker, um scanner de dependências
atualizado ou uma auditoria de segurança.

Os relatórios atuais estão em `reports-pipeline/`. `RESULTADOS-TESTES.md` e
relatórios de pastas anteriores descrevem a etapa anterior, com 224 testes.

## Threads e comportamento

Foi mantido o event loop Qt. Não há um segundo loop asyncio. Comandos da Home e
da IA usam `CommandWorker`; modos e pedidos remotos passam pelo mesmo coordenador.
Ações que chegam por esse coordenador são serializadas para evitar sobreposição.
O cancelamento interrompe tarefas na espera ou entre etapas, sem usar `terminate()`.

A leitura de streaming do Ollama tem limite de inatividade de 60 s. O reconhecimento
remoto de voz tem timeout de 10 s. O encerramento solicita parada aos workers
periódicos sem bloquear a UI em seus waits, e aguarda tarefas ainda em andamento.
Um comando de automação já iniciado não é abortado à força no meio de uma ação.

Continuam existindo caminhos legados síncronos, como algumas consultas de setup,
login de amigos, WMI e controles de mídia. Eles não foram todos migrados nesta
iteração. As funções públicas de execução direta de `escravo.py` também permanecem
disponíveis; chamadas externas que as usem diretamente não passam pelo coordenador.

## Segurança e compatibilidade

- Novas chaves remotas têm 32 caracteres hexadecimais. Chaves antigas persistidas
  continuam válidas; use "Gerar nova chave" para migrar. O projeto Android não veio
  neste ZIP, portanto sua aceitação de chaves de 32 caracteres ainda precisa ser verificada.
- Pedidos remotos aceitam até 16 KiB de corpo e 4.096 caracteres no comando.
- O fallback de abertura resolve executáveis no PATH sem enviar texto livre ao shell.
  URIs de protocolo são limitadas aos esquemas conhecidos de jogos/música e HTTP(S).
- Comandos digitados diretamente mantêm execução normal. Comandos extraídos de uma
  resposta da IA pedem confirmação, com "Não" como opção padrão.
- O servidor continua sendo HTTP, com bind em todas as interfaces. O firewall e a
  rede determinam o alcance; não foi adicionado TLS. A presença de token não substitui
  proteção de transporte. Sessões/chaves locais ainda usam QSettings.
- O executável não é assinado. SHA256 identifica o artefato, mas não substitui assinatura.
  A atualização real e seu mecanismo de recuperação ainda exigem validação dedicada.

## Logging

Ao abrir o assistente, os logs ficam em `%LOCALAPPDATA%\Ikuromimy\logs\assistente.log`.
Há até três backups de 1 MiB. Os eventos da execução registram ID, duração e tipo
de erro; não registram texto do comando, mensagens de chat nem credenciais.
O formatter também remove valores de campos comuns de credenciais como defesa
adicional. Se não for possível abrir o arquivo, a configuração usa stderr.

## CI/CD e distribuição

`.github/workflows/testes.yml` executa análise e testes no Windows com Python
3.10, 3.12 e 3.14. Em uma tag `v*` ou disparo manual com `empacotar=true`, um job
dependente dos checks gera o EXE, executa `--self-test` e publica um artefato
do Actions com checksum. Isso é entrega de artefato, sem instalação automática
no computador nem publicação automática de uma GitHub Release.

O workflow não foi enviado nem executado no GitHub nesta sessão. A validação local
foi em Python 3.14.4. A versão declarada pelo aplicativo foi preservada.

O ZIP do código não inclui ambiente virtual nem o EXE de 97 MB. O executável local
está em `dist-pipeline/Assistente Virtual Ikuromimy.exe`, acompanhado de `SHA256.txt`.

Relatórios: [testes](reports-pipeline/junit.xml), [cobertura](reports-pipeline/coverage/index.html),
[análise estática](reports-pipeline/analise-estatica.json), [smoke test](reports-pipeline/build-smoke.json),
[resumo estruturado](VALIDACAO.json).
