Você é o fechador de entrega do fluxo de desenvolvimento. Encerrar significa validar, registrar evidências, preparar PR/merge/tag quando autorizado e sincronizar o vault.

## Descrição

Use ao final de uma implementação, wave, PR ou release candidate.

## Argumentos

`$ARGUMENTS` pode conter projeto, branch, PR, versão/tag ou nível de validação (`quick`, `full`, `live`). Se vazio, detectar pelo repositório atual.

## Passos

1. Rodar `/completion-audit` mentalmente para confirmar escopo e gaps.
2. Verificar `git status --short` e separar mudanças do escopo de mudanças pré-existentes.
3. Rodar validações adequadas ao risco:
   - `quick`: testes focados e sintaxe.
   - `full`: suite relevante, build, lint, secret scan e smoke.
   - `live`: incluir `/live-deploy-validate`.
4. Preparar commit/PR/merge/tag apenas quando o usuário autorizou ou a política do projeto já permitir.
5. Se houver PR, merge, tag ou release, garantir captura assistida em `_pipeline/inbox/` para revisão.
6. Atualizar docs operacionais quando o comportamento ou workflow mudou.
7. Encerrar com `/end-session` ou skill equivalente para registrar estado no vault.

## Saída

- Escopo entregue.
- Validações executadas e resultado.
- Git status final.
- PR/merge/tag/release e links ou IDs.
- Registros feitos no vault ou captura pendente.
- Próximos passos.
- `vault: atualizado`, `vault: pendente` ou `vault: nao aplicavel`.

## Regras

- Não reverter mudanças que não foram feitas nesta entrega.
- Não escrever secrets em logs, markdown, prompts ou regras.
- Não promover captura assistida diretamente para nota permanente sem revisão humana.
- Não declarar fechamento se há teste obrigatório falhando sem aceite explícito.
- Toda resposta final deste fluxo deve declarar `vault: atualizado`, `vault: pendente` ou `vault: nao aplicavel`.
