# 08 — Monitor CI Release Loop (Autônomo)

Protocolo agnóstico para monitorar um workflow de CI/CD de release, aplicar fixes automáticos em plataformas experimentais e executar ações pós-sucesso (ex: atualizar fórmulas de package manager). Reutilizável para qualquer repo, workflow e estratégia de plataformas.

Invocar via `/loop` no diretório do projeto ou a partir do vault.

---

## Argumentos esperados

Ao invocar, informar os seguintes parâmetros (substituir `{...}` antes de usar):

| Arg | Exemplo | Obrigatório |
|---|---|---|
| `--repo` | `<org>/<repo>` | sim |
| `--workflow` | `release.yml` | sim |
| `--tag` | `v0.5.6` | sim — tag do release sendo monitorado |
| `--branch` | `develop` | sim — branch alvo para fixes |
| `--commit-author` | `"<Nome> <email@example.com>"` | sim |
| `--experimental-platforms` | `windows-x64` | sim — plataformas onde fix automático é permitido |
| `--stable-platforms` | `linux-x64,macos-arm64` | sim — plataformas onde falha exige intervenção humana |
| `--post-success-action` | `update-homebrew` | opcional — ação a executar ao final (`update-homebrew`, `update-npm`, `none`) |
| `--formula-repo` | `<org>/homebrew-<formula>` | condicional — obrigatório se `--post-success-action=update-homebrew` |
| `--binary-pattern` | `axon-{os}-{arch}` | condicional — padrão de nome dos binários para calcular SHA-256 |

---

## Regras absolutas

1. **Zero interação humana** para falhas em `--experimental-platforms`. Para `--stable-platforms`, sempre reportar e parar o loop.
2. **Nunca recriar tag sem antes deletar a existente** — verificar se `{tag}` existe antes de push.
3. **Fix commit sempre em `--branch`** com author exato de `--commit-author`. Sem `Co-Authored-By` ou menções a AI.
4. **PR obrigatório antes de merge** — nunca push direto em branch protegida.
5. **Loop encerra em dois casos apenas**: todos os jobs `success` OU falha em `--stable-platforms`.
6. **SHA-256 dos binários**: calcular a partir dos assets do release na GitHub API — nunca hardcodar.

---

## Protocolo de cada iteração

### Passo 1 — Verificar run mais recente

```
gh run list --repo {repo} --workflow {workflow} --limit 1 --json status,conclusion,databaseId,headBranch
```

Capturar: `status` (`in_progress` | `completed`), `conclusion` (`success` | `failure` | `cancelled`), `databaseId`.

---

### Passo 2 — Decisão por status

#### 2A — `in_progress`

Aguardar. Não agir. Emitir log: `[{timestamp}] CI em andamento — run #{id}. Próxima verificação em {delay}s.`

Ajuste de delay:
- Primeira verificação após trigger de re-run: 60s
- Verificações subsequentes: 120s (padrão), 180s se o workflow tiver jobs de compilação pesada (C/Rust/Go cross-compile)

---

#### 2B — `completed / failure`

Identificar quais jobs falharam:

```
gh run view {run_id} --repo {repo} --json jobs --jq '.jobs[] | select(.conclusion=="failure") | {name, conclusion}'
```

**2B-i — Falha em `--experimental-platforms`** (fix autônomo):

1. Ler logs do job falho:
   ```
   gh run view {run_id} --repo {repo} --log-failed
   ```
2. Identificar a causa raiz (compilação, teste, dependência, path, encoding).
3. Aplicar fix mínimo no arquivo afetado em `--branch`.
4. Commit com author `--commit-author`:
   ```
   git commit --author="{commit-author}" -m "fix({plataforma}): {descrição curta da causa}"
   ```
5. Abrir PR de `--branch` → branch principal:
   ```
   gh pr create --repo {repo} --title "fix: {plataforma} build failure {tag}" --body "Auto-fix: {causa raiz}"
   ```
6. Merge do PR (squash):
   ```
   gh pr merge {pr-number} --repo {repo} --squash --delete-branch=false
   ```
7. Re-trigger do release:
   - Deletar tag: `git tag -d {tag} && git push origin :{tag}`
   - Recriar tag no HEAD atualizado: `git tag {tag} && git push origin {tag}`
8. Voltar ao Passo 1.

**2B-ii — Falha em `--stable-platforms`**:

Reportar ao usuário:
```
[LOOP ENCERRADO] Falha em plataforma estável: {job-name}
Run: https://github.com/{repo}/actions/runs/{run_id}
Causa provável: {primeiras 10 linhas dos logs do job}
Ação requerida: intervenção manual.
```
Encerrar loop.

---

#### 2C — `completed / success` (todos os jobs passaram)

Executar `--post-success-action`:

**`update-homebrew`:**

1. Baixar assets do release via GitHub API:
   ```
   gh release view {tag} --repo {repo} --json assets --jq '.assets[].browserDownloadUrl'
   ```
2. Para cada binário matching `--binary-pattern`:
   - Download: `curl -L {url} -o {arquivo}`
   - SHA-256: `sha256sum {arquivo}` (Linux) ou `shasum -a 256 {arquivo}` (macOS)
3. Atualizar a fórmula no `--formula-repo`:
   - Editar campo `url` e `sha256` para cada plataforma/arch.
   - Commit: `"chore: update formula to {tag}"`
   - Push direto em main (se permitido) ou PR.
4. Emitir confirmação com todos os SHAs atualizados.

**`update-npm`:**

1. Verificar se `package.json` tem `version` igual a `{tag}` sem o `v`.
2. Se não: `npm version {tag-sem-v} --no-git-tag-version` + commit + push.
3. `npm publish --access public` (requer `NPM_TOKEN` em env ou `pass show npm/token`).

**`none` ou não informado:**

Apenas emitir:
```
[LOOP CONCLUÍDO] Todos os jobs de {tag} passaram com sucesso.
Run: https://github.com/{repo}/actions/runs/{run_id}
Nenhuma ação pós-sucesso configurada.
```

---

## Exemplo de invocação completo

```
/loop Monitore o CI do release.yml em {REPO}.

--repo {REPO}
--workflow release.yml
--tag {TAG}
--branch develop
--commit-author "{NOME} <{EMAIL}>"
--experimental-platforms windows-x64
--stable-platforms linux-x64,macos-arm64
--post-success-action update-homebrew
--formula-repo {FORMULA_REPO}
--binary-pattern {BINARY_PATTERN}-{os}-{arch}

A cada iteração:
1. Verifique o run mais recente do workflow (Passo 1)
2. Aplique a decisão do Passo 2 conforme status/conclusion/plataforma
3. Ajuste o delay com base no estado atual
```

---

## Saída esperada por iteração

```
[{ISO-8601}] status={status} conclusion={conclusion} run=#{id}
→ Ação: {aguardar | fix:{plataforma} | post-success:{ação} | encerrar:{motivo}}
```

Ao encerrar: emitir bloco de sumário com total de iterações, fixes aplicados, PRs abertos e ação final executada.

---

## Referência rápida de comandos

```bash
# Status do run
gh run list --repo {repo} --workflow {workflow} --limit 1 --json status,conclusion,databaseId

# Jobs falhos
gh run view {id} --repo {repo} --json jobs --jq '.jobs[] | select(.conclusion=="failure") | .name'

# Logs de falha
gh run view {id} --repo {repo} --log-failed

# Re-trigger via tag
git tag -d {tag} && git push origin :{tag} && git tag {tag} && git push origin {tag}

# Assets do release
gh release view {tag} --repo {repo} --json assets --jq '.assets[] | {name, url: .browserDownloadUrl}'
```
