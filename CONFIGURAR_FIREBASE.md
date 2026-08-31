# Configuração do Firebase (sistema de Amigos)

## 1. Preencher a configuração

Renomeia `ui/firebase_config_exemplo.py` pra `ui/firebase_config.py`
e preenche com os dados do seu projeto (instruções estão dentro do
próprio arquivo de exemplo).

## 2. Regras de segurança do Realtime Database

Sem isso, QUALQUER pessoa (mesmo sem estar logada) poderia ler ou
escrever qualquer dado de qualquer usuário. Cola isso em:

**Firebase Console > Build > Realtime Database > aba "Regras"**

```json
{
  "rules": {
    "perfis": {
      "$uid": {
        ".read": "auth != null",
        ".write": "auth != null && auth.uid === $uid"
      }
    }, 
    "nomes_usuario": {
      "$nome": {
        ".read": true,
        ".write": "auth != null"
      }
    },
    "amizades": {
      "$uid": {
        ".read": "auth != null && auth.uid === $uid",
        ".write": "auth != null"
      }
    },
    "presenca": {
      "$uid": {
        ".read": "auth != null",
        ".write": "auth != null && auth.uid === $uid"
      }
    },
    "mensagens": {
      "$id_conversa": {
        ".read": "auth != null && $id_conversa.contains(auth.uid)",
        ".write": "auth != null && $id_conversa.contains(auth.uid)"
      }
    }
  }
}
```

Depois de colar, clica em **"Publicar"**.

### O que cada regra faz

- **perfis**: qualquer usuário logado pode LER qualquer perfil (precisa
  pra mostrar o nome dos seus amigos), mas só pode ESCREVER o próprio.
- **nomes_usuario**: índice pra buscar usuário pelo nome (usado no
  "adicionar amigo"). Leitura/escrita liberada pra qualquer logado —
  simplificação aceitável pra um projeto desse porte.
- **amizades**: cada usuário só consegue LER a própria lista de
  amizades (não a de terceiros). A escrita é mais aberta (`auth !=
  null`) porque tanto quem manda quanto quem recebe o pedido precisam
  escrever no nó um do outro — uma regra mais restrita exigiria lógica
  de validação bem mais complexa.
- **presenca**: qualquer logado pode VER a presença de qualquer um
  (simplificação; o filtro "só amigos" acontece do lado do app, não
  do banco), mas só você pode alterar a SUA própria presença.

⚠️ **Limitação conhecida**: como "amizades" e "presenca" têm leitura/
escrita um pouco mais abertas que o ideal (por simplicidade), um
usuário logado *tecnicamente* consegue, direto pela API do Firebase
(fora do nosso app), inspecionar a presença de qualquer outro usuário,
ou escrever um pedido de amizade fingindo ser outra pessoa (não
consegue LER a lista de amizades de terceiros, só escrever em nós
específicos). Pra um projeto hobby isso é aceitável; se um dia quiser
travar mais, dá pra evoluir as regras com Cloud Functions validando
cada escrita.

## 3. Estrutura de dados (se quiser inspecionar manualmente)

```
/perfis/{uid} = {"nome_usuario": "...", "email": "..."}
/nomes_usuario/{nome_em_minusculo} = "uid_do_dono_do_nome"
/amizades/{uid}/{uid_amigo} = "pendente_enviado" | "pendente_recebido" | "aceito"
/presenca/{uid} = {"online": true/false, "status_texto": "...", "atualizado_em": timestamp}
/mensagens/{id_conversa}/{chave_auto_gerada} = {"remetente": "uid", "texto": "...", "timestamp": ...}
```

`{id_conversa}` é os dois UIDs dos participantes, ordenados e juntos
com "_" (ex: `abc123_xyz789`) — assim os dois lados sempre calculam o
mesmo caminho, sem precisar de um "ID de conversa" separado guardado
em algum lugar. A regra de `mensagens` é a mais restrita das quatro:
só quem faz parte da conversa (UID aparece no `$id_conversa`) consegue
ler ou escrever ali.
