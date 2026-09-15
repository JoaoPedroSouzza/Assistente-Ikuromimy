# Arquitetura e ordem de trabalho

## 2. Profiling

Baseline: 224 testes passaram. cProfile registrou 7,09 s para o processo de teste
(incluindo pytest/importações). A persistência do histórico foi o maior custo
de teste observado: 0,53 s para inserir 60 comandos. Isso não mede serviços reais.
O benchmark isolado de interpretação fez 6.000 classificações em mediana de
0,444 s, cinco repetições com o mesmo conjunto de frases.

## 3. Decisão de arquitetura

- `core/comandos.py`: interpretação pura, sem Qt, rede ou Windows.
- `core/execucao.py`: entrada compartilhada para execução, serializada para evitar
  automações de teclado concorrentes. Usa o adaptador legado `escravo.py`.
- `ui/*_worker.py`: tarefas fora da thread da interface; sinais transportam resultados.
- `ui/pages/`: widgets e apresentação; persistência da UI fica na thread principal.
- `ui/*_manager.py` e clientes existentes: adaptadores de arquivos, Qt e serviços.
- `core/logging_config.py`: configuração central de logs locais rotativos.

`escravo.py` mantém suas funções públicas para compatibilidade. A extração gradual
evita reescrever automação Windows sem um ambiente real de validação. Qt continua
sendo o único event loop da interface; não será adicionado um segundo loop asyncio.

## 4–10. Aplicação e verificação

Refatorar primeiro sem mudar interpretação; mover execução da UI para workers;
limitar esperas e impedir tarefas duplicadas; validar entradas remotas e remover
o uso de shell com texto livre; adicionar logging sem conteúdo de comandos ou
credenciais; otimizar somente o caminho medido; executar análise estática e testes;
configurar integração contínua e empacotamento de artefato Windows.

O CI/CD prepara artefatos e checks. Publicação de release e instalação no computador
não fazem parte da execução local. Resultados e limitações ficam no relatório final.


## Camada visual reativa

A UI ganhou estados/eventos, motor de animação, tema reativo, efeitos e componentes separados. Veja [REDESIGN.md](REDESIGN.md) para a composição e os contratos. O núcleo emite notificações opcionais por `core/visual_events.py` sem importar Qt.
