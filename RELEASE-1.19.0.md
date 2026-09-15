# IKUROMIMY v1.19.0 — Interface reativa e novo núcleo visual da IA

## 🚀 O que mudou

- 🌌 **Fundo topográfico vivo:** curvas geradas e animadas por código, com movimento orgânico, parallax do mouse e reação aos estados do assistente.
- ✨ **Novo núcleo visual:** anéis, contornos e partículas representam escuta, pensamento, fala, execução e conclusão das ações.
- 🎨 **Uma identidade para cada aba:** cores de destaque por seção, transições animadas e preferências salvas entre sessões.
- 🪟 **Interface redesenhada:** página inicial renovada, painéis translúcidos, sidebar retrátil e feedback visual nos botões.
- ⌨️ **Barra e central de comandos:** comandos, perguntas, voz e sugestões contextuais em todas as páginas. `Ctrl + Espaço` abre a central com o aplicativo em foco.
- 📎 **Anexos de texto:** arquivos UTF-8 de até 128 KiB podem entrar como rascunho na conversa para revisão antes do envio.
- 📊 **Telemetria:** CPU/RAM com transições suaves; GPU e temperatura aparecem quando há suporte do driver/sistema.
- 🌙 **Modo ambiente:** após 75 segundos ocioso no início, painéis secundários desaparecem gradualmente e retornam com a interação.
- ⚡ **Controle de efeitos:** níveis Alto, Médio, Baixo e Desativado, cache da geometria e pausa das animações com a janela oculta ou minimizada.
- 🎙️ **Integração com a voz:** reação à amplitude do microfone e visualização da fala sintetizada quando o áudio pode ser decodificado.
- 🧩 **Recursos preservados:** música, conversas, atalhos editáveis, modos, amigos, controle remoto, sistema, configurações e histórico continuam disponíveis.
- 🔄 **Atualização alinhada:** versão interna corrigida para 1.19.0 e atualizador direcionado ao repositório atual.

## 🧪 Qualidade e desenvolvimento

A validação local do redesign registrou **260 testes aprovados**, **73,51% de cobertura combinada** e análise estática AST de **66 arquivos sem achados**. A camada visual foi separada em estados/eventos, tema, animações, efeitos e componentes, facilitando manutenção e evolução.

Esses testes isolam efeitos externos; não substituem a validação de todos os serviços e dispositivos reais. O workflow do GitHub executa suas próprias verificações após o envio.

## ⚠️ Pré-requisitos e observações

- Aplicativo desktop destinado ao Windows; a aba IA utiliza o **Ollama** e um modelo instalado.
- O sistema de Amigos depende da configuração do **Firebase**.
- A transcrição de voz existente precisa de internet.
- Dependências em **`requirements.txt`**; testes em **`requirements-testes.txt`**.
- Sensores indisponíveis aparecem como `—`. As metas de FPS dependem do hardware e do nível de efeitos.
- A sincronização visual do TTS é aproximada com o player atual. Os painéis usam transparência, sem desfoque Acrylic/Mica.
- O executável de versões anteriores não inclui o redesign. Um EXE novo deve ser gerado para esta versão e anexado à release antes da distribuição pelo atualizador.

Veja o [CHANGELOG completo](https://github.com/JoaoPedroSouzza/Assistente-Ikuromimy/blob/v1.19.0/CHANGELOG.md) e os [detalhes do redesign](https://github.com/JoaoPedroSouzza/Assistente-Ikuromimy/blob/v1.19.0/REDESIGN.md).
