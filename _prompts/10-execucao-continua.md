# Execucao Continua Assistida

Use quando o plano ja estiver aceito e o agente puder continuar sem nova confirmacao.

## Prompt

Continue o plano ativo ate concluir, validar ou encontrar um bloqueio real. Preserve mudancas existentes que nao sejam suas, mantenha o escopo fechado, rode validacoes proporcionais e reporte apenas quando houver decisao, bloqueio ou resultado verificavel.

## Regras

- Nao parar para pedir confirmacao se o proximo passo ja esta claro.
- Nao fazer merge, tag, release ou escrita duravel no vault sem autorizacao ou workflow explicito.
- Se surgir risco de secret, dado destrutivo ou mudanca fora do escopo, pare e explique.
