# Testes do Ikuromimy

## Executar no Windows

Requer Python 3.10 ou superior com o comando `py`. Na pasta do projeto:

```powershell
.\testar.bat
```

O script prepara `.venv-testes`, instala `requirements-testes.txt` e executa a
suíte contra os arquivos `escravo.py` e `ui/` desta pasta. A instalação requer
internet ou pacotes em cache. O assistente não precisa estar aberto.

Depois da instalação, para repetir sem acessar o instalador de pacotes:

```powershell
.\.venv-testes\Scripts\python.exe -X utf8 -m pytest
```

Para uma área específica:

```powershell
.\.venv-testes\Scripts\python.exe -X utf8 -m pytest tests/test_interface_fluxos.py
.\.venv-testes\Scripts\python.exe -X utf8 -m pytest tests/test_voz_audio_midia.py
```

## Relatórios e cobertura mínima

`testar.bat` gera:

- `reports-pipeline/coverage/index.html`: relatório visual de cobertura.
- `reports-pipeline/coverage.xml`: cobertura para ferramentas de CI.
- `reports-pipeline/junit.xml`: quantidade de testes, duração e detalhes de falhas.

Os relatórios antigos em `reports/`, caso existam na pasta de trabalho, pertencem
à execução anterior. Consulte `reports-pipeline/` para esta ampliação.

A configuração mede todos os módulos do assistente e exige **65% de cobertura
combinada** (linhas e ramificações). A execução validada chegou a cerca de 69%.
A exigência se aplica quando a medição está ativa; rode testes individuais sem
`--cov` para não comparar um subconjunto com o mínimo da suíte inteira.

O workflow do GitHub executa em Windows/Python 3.10, 3.12 e 3.14 e publica os
relatórios mesmo quando há falhas. Ele só passa a rodar após enviar os arquivos
ao repositório. A validação local desta entrega foi em Python 3.14.4.

## Isolamento

Qt, widgets, threads, lógica do assistente, NumPy e persistência INI são reais.
Um adaptador de QSettings força arquivos temporários para não usar o registro
do Windows. Cada teste recebe configurações e cache próprios.

Teclado, áudio físico e sounddevice são substituídos antes de importar o app.
As fronteiras de rede, criação/encerramento de processos, navegador, COM e
reconhecimento remoto ficam bloqueadas até o teste instalar uma simulação
explícita. Essas barreiras previnem acidentes; não são uma sandbox de segurança.

Os testes não precisam de conta Firebase, Ollama instalado, Spotify, microfone
ou permissão para atualizar o executável. Para iniciar o aplicativo de verdade,
instale suas dependências separadas em `requirements.txt`.

Veja [RESULTADOS-TESTES.md](RESULTADOS-TESTES.md) para comparação, correções,
limitações e avisos da execução validada.

## Atualização de engenharia

A validação atual tem 249 testes. Consulte [PIPELINE.md](PIPELINE.md); os resultados anteriores foram preservados como histórico.
