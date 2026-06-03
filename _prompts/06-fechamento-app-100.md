# 06 — Fechamento de App ao 100%

Protocolo agnóstico para mapear, planejar e corrigir todas as lacunas funcionais de um app até que ele esteja operando completamente (caminho feliz + estados de erro + completude de dados + imagens populadas). Serve para apps móveis (Expo/React Native/Detox/UIAutomator), web (Next.js/Vite/Playwright), admin panels, ou qualquer front consumindo APIs.

---

## Argumentos esperados

Ao invocar, informar:

| Arg | Exemplo | Obrigatório |
|---|---|---|
| `--app` | `customer`, `provider`, `admin-web` | sim |
| `--repo` | caminho absoluto do repo (default: `<projects-root>/<projeto>`) | sim |
| `--app-path` | path relativo do app dentro do repo (ex: `src/Frontend/apps/customer`) | sim |
| `--platform` | `mobile-android`, `mobile-ios`, `web` | sim |
| `--env` | `dev`, `hmg`, `stg` | sim |
| `--api-base` | URL pública do BFF/API do ambiente (ex: `https://bff-customer.example.com`) | sim |
| `--credentials` | email/senha ou token para autenticar fluxos protegidos | opcional — registrar se ausente |

---

## Regras absolutas (herda do CLAUDE.md do repo)

1. **Governance de commits**: task/* saindo de feature/*; sem `Co-Authored-By`; sem menção a AI; nunca merge sem aprovação humana.
2. **GitOps**: se o ambiente tem ArgoCD/Flux, mudanças de config vão pelo repo gitops; `kubectl set env` é revertido.
3. **Nunca mexer em `.gitignore`** do repo (mods podem ser do dev local).
4. **Contratos de wire (proto/graphql/openapi)**: client é cópia byte-a-byte do server. Drift silencioso é caro.
5. **Axon obrigatório** em repos indexados (hook bloqueia Grep/Glob).

---

## As 3 fases

### Fase 1 — MAPEAMENTO (read-only)

Entregar uma matriz cobrindo TODO o app. Uma linha por fluxo/tela.

**Passo 1.1 — Enumerar rotas/telas**
- Expo/React Native: `ls <app-path>/app/**` (expo-router) ou `ls src/screens/*` (RN clássico)
- Next.js: `ls <app-path>/app/**/page.tsx` + `ls <app-path>/pages/**/*.tsx`
- Vite SPA: ler `router` / arquivo de rotas
- Para cada arquivo, extrair: rota, nome, tipo (auth/tab/detail/modal), endpoints consumidos (grep por `fetch`, `useQuery`, cliente HTTP do projeto).

**Passo 1.2 — Rodar o app de verdade**
- Mobile Android: build APK release, instalar em emulator/device, adb UIAutomator para navegar e screencap
- Web: `pnpm dev` ou APK deployed; Playwright (preferir) para percorrer fluxos e snapshot
- NÃO aceitar inspeção estática como validação — rodar.

**Passo 1.3 — Validar APIs em paralelo**
- Para cada endpoint descoberto: curl com credenciais, verificar status, payload, completude de campos.
- Gotcha comum: API retorna `totalCount=N` mas `items=[]` → drift de contrato, query broken, seed vazio.

**Passo 1.4 — Auditar seeds**
- Listar entidades no seed vs. tabelas do DB (via kubectl exec se permitido, ou `grep -c` em arquivos de seed).
- Para cada entidade, conferir campos não-críticos (bio, description, address, imagens, metadados) — o seed passar não basta, tem que estar COMPLETO.
- Imagens: toda entidade que suporta imagem no schema deve ter imagem real no seed.

**Passo 1.5 — Matriz final**
Arquivo: `.logs/summaries/<app>-mapping-<YYYY-MM-DD>.md`

```markdown
| Fluxo | Tela(s) | Endpoints | Status | Gap | Severidade |
|---|---|---|---|---|---|
| Auth / Register | register.tsx | POST /api/v1/auth/register | OK | Sem confirmação de email | P2 |
| Discovery / Map | search.tsx (map) | GET /api/discovery/nearby | OK | — | — |
| Booking / New | booking/new.tsx | POST /api/bookings | BROKEN | 500 em provider sem availability | P0 |
...
```

Severidade:
- **P0** impede MVP (fluxo principal quebra)
- **P1** funciona parcialmente (bug visual, estado errado)
- **P2** completude (seed incompleto, imagem faltando, texto hardcoded)

**Passo 1.6 — STOP e reportar**
Enviar matriz ao usuário. Não prosseguir sem aprovação.

---

### Fase 2 — PLANO DE CORREÇÃO

Para cada gap da Fase 1, registrar em `.logs/summaries/<app>-fix-plan-<YYYY-MM-DD>.md`:

```markdown
## FIX-001 — <descrição>
- **Severidade**: P0/P1/P2
- **Fluxo afetado**: <da matriz>
- **Tipo**: backend / gitops / frontend / seed / assets
- **Arquivos a tocar**: <lista>
- **Dependências**: <outras FIXes que devem passar antes>
- **Branch**: task/<slug-curto>
- **Estratégia de teste**: <como validar depois>
- **Estimativa**: XS / S / M / L
```

Agrupar em ondas:
- **Onda 1 — Infra/Seed**: fixes de dados (seeds completos + imagens) + config backend. Tudo que destrava testes subsequentes.
- **Onda 2 — Bugs P0**: caminho feliz do MVP funcionando end-to-end.
- **Onda 3 — P1 + P2**: polimento.

**STOP e aguardar aprovação antes da Fase 3.**

---

### Fase 3 — EXECUÇÃO

Para cada FIX aprovado:

1. `git checkout -b task/<slug>` saindo da feature branch ativa
2. Implementar
3. Rodar o harness automatizado (ver seção "Harness") — deve fazer o fluxo afetado passar
4. Commit com mensagem conventional + push
5. Abrir PR com corpo contendo: root cause, links pra gotchas, evidência do harness (screenshot + output)
6. Se for config gitops: commit no repo gitops, esperar ArgoCD
7. Atualizar a matriz de status

Ao final, re-executar o harness completo no app. Todas as linhas da matriz devem estar OK ou ter exceção explicitamente documentada.

---

## Harness automatizado (re-executável)

**Objetivo**: qualquer fluxo validado na Fase 1 deve ter um teste automatizado na Fase 3 que pode ser rodado a qualquer momento (`./scripts/app-closure/run.sh --app customer --env dev`) sem intervenção humana.

### Layout proposto no repo

```
scripts/app-closure/
├── run.sh                           # entry agnóstico; recebe --app, --env, --suite
├── config/
│   ├── customer.yaml                # rotas, endpoints, credentials ref, emulator id
│   ├── provider.yaml
│   └── admin-web.yaml
├── suites/
│   ├── api/                         # curl-based; por app
│   │   ├── customer.auth.sh
│   │   ├── customer.discovery.sh
│   │   └── customer.booking.sh
│   ├── mobile/                      # adb + uiautomator OR Detox
│   │   └── customer.ui.spec.ts
│   └── web/                         # Playwright
│       └── admin.ui.spec.ts
├── fixtures/
│   ├── images/                      # imagens de seed (provider logos, offerings, etc.)
│   └── payloads/                    # JSON de register, booking, etc.
└── lib/
    ├── assert.sh                    # expectJsonField, expectStatus, expectNonEmpty
    └── report.sh                    # gera .logs/summaries/harness-run-<ts>.md
```

### `run.sh` — interface agnóstica

```bash
#!/usr/bin/env bash
set -euo pipefail

APP=""
ENV="dev"
SUITE="all"   # all | api | mobile | web | <single-suite>

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app) APP="$2"; shift 2 ;;
    --env) ENV="$2"; shift 2 ;;
    --suite) SUITE="$2"; shift 2 ;;
    *) echo "Unknown: $1"; exit 2 ;;
  esac
done

[[ -z "$APP" ]] && { echo "--app required"; exit 2; }

CONFIG="scripts/app-closure/config/${APP}.yaml"
[[ -f "$CONFIG" ]] || { echo "Missing $CONFIG"; exit 1; }

source scripts/app-closure/lib/report.sh
report_init "$APP" "$ENV" "$SUITE"

case "$SUITE" in
  all|api) run_api_suite "$APP" "$ENV" ;;&
  all|mobile) [[ $(yq '.platform' "$CONFIG") == "mobile-android" ]] && run_mobile_suite "$APP" "$ENV" ;;&
  all|web) [[ $(yq '.platform' "$CONFIG") == "web" ]] && run_web_suite "$APP" "$ENV" ;;&
esac

report_finalize
```

### `config/<app>.yaml` — contrato por app

```yaml
app: customer
platform: mobile-android
app_path: src/Frontend/apps/customer  # exemplo
package_id: com.example.customer          # mobile
url: https://customer.example.com   # web
api_base:
  dev: https://bff-customer.example.com
  hmg: https://bff-customer-hmg.example.com
credentials:
  dev:
    email: customer@example.com
    password_ref: pass:example/customer-dev    # lookup no `pass`
auth_flow: bearer                        # bearer | cookie | session
emulator:
  adb_device: emulator-5554
  geo_fix: { lat: -23.5385, lng: -46.5618 }  # para app com GPS
flows:                                   # lista alinhada com rotas do app
  - id: auth.register
    type: api
    method: POST
    path: /api/v1/auth/register
    expect_status: 201
  - id: discovery.nearby
    type: api
    method: GET
    path: /api/discovery/nearby?lat=-23.54&lng=-46.55&radiusKm=5
    auth: bearer
    assert:
      - jsonPath: $.categories[0].offerings
        minLength: 3
      - jsonPath: $.categories[0].offerings[0].provider.businessName
        nonEmpty: true
  - id: search.map.render
    type: mobile
    steps:
      - launch
      - tap: { text: "Buscar" }
      - wait: 2s
      - tap: { text: "Map View" }
      - wait: 3s
      - screenshot: customer-MAP.png
      - assert_visible: { text: "São Paulo" }
```

### Suite API (`suites/api/<app>.<flow>.sh`)

Cada arquivo tem 1 função por flow. Usa curl + jq. Reporta via `lib/assert.sh`. Fácil de estender.

### Suite Mobile (`suites/mobile/<app>.ui.spec.ts`)

Opções (escolher por projeto):
- **Detox** (RN/Expo native): mais idiomático, já no stack se app usa
- **maestro** (YAML-based, agnóstico, zero código): melhor para cobertura rápida
- **adb + uiautomator dump parse**: último recurso, frágil mas universal

Priorizar maestro quando possível — suites são `.yaml` declarativos, versionáveis, CI-friendly.

### Suite Web (`suites/web/<app>.ui.spec.ts`)

Playwright com fixtures por ambiente. Screenshots automáticos em falha.

### Re-execução em CI

Adicionar workflow `.github/workflows/app-closure-<app>.yml` disparado manualmente (`workflow_dispatch`) ou no merge de PRs que toquem o app. Publicar relatório como artifact.

---

## Requisitos obrigatórios de completude

Padrão aplicado a todo app:

### Seeds realistas
- Toda entidade com ≥20 linhas diversificadas (nomes, regiões, valores representativos)
- Todos os campos não-nullable preenchidos com valor verossímil (não "test test test")
- Estados variados: para entidades com workflow (bookings, jobs, orders), ter seeds em CADA estado possível

### Imagens
- Toda entidade com coluna `avatar_url`/`logo_url`/`image_url`/`photo_url`/`banner_url` deve ter imagem real
- Estratégia aceita:
  - (A) PNGs pequenos em `scripts/seed/assets/` — commitáveis, offline-friendly
  - (B) URLs determinísticas (Unsplash com seed, Lorem Picsum, `https://i.pravatar.cc/300?u=<id>`)
  - (C) Bucket S3/MinIO populado no setup
- Definir estratégia na Fase 2; implementar na Fase 3 Onda 1

### Strings
- Sem "Lorem ipsum", "TODO", "Placeholder" em seed ou label
- Textos em pt-BR (idioma default do domínio) se não for app internacionalizado

### Validações de erro
- Todo form mostra erro específico (não "erro genérico")
- Todo fluxo de rede tem loading state + empty state + error state com retry

---

## Output esperado ao final do protocolo

Ao concluir Fase 3:

1. `.logs/summaries/<app>-mapping-<date>.md` — matriz da Fase 1
2. `.logs/summaries/<app>-fix-plan-<date>.md` — plano da Fase 2
3. `.logs/summaries/<app>-closure-<date>.md` — relatório final com status de cada FIX, commits/PRs, resultado do harness
4. PRs abertos para cada branch `task/*` (humano aprova e merge)
5. Harness passando 100% em `scripts/app-closure/`
6. `_knowledge/projects/<projeto>/work-log.md` atualizado via `/end-session`

---

## Checklist de guardrail

Antes de começar:
- [ ] `--app` + `--env` + `--api-base` definidos
- [ ] Credenciais acessíveis (via `pass` ou env)
- [ ] Emulador/browser disponível para Fase 1.2
- [ ] kubectl apontando para o cluster certo se app depende de backend
- [ ] `CLAUDE.md` do repo lido (governance + gotchas específicos)

Antes de cada fase:
- [ ] Fase anterior aprovada pelo usuário
- [ ] Tasks criadas via `TaskCreate` (uma por sub-etapa)
- [ ] `.logs/validation/` limpo de resíduos da sessão anterior

Antes de commit:
- [ ] Mudança testada executando o app (não só teste unitário)
- [ ] Screenshot/output anexado como evidência
- [ ] Governance respeitado (branch, mensagem, sem AI trailer)

Antes de merge (pedir ao humano):
- [ ] CI verde
- [ ] Harness passando
- [ ] Matriz atualizada

---

## Quando NÃO usar este protocolo

- App é um greenfield ainda em design (use `01-onboarding-novo-projeto.md`)
- Trabalho é 1 feature isolada (use `02-onboarding-nova-feature.md`)
- Troubleshooting pontual sem escopo de "fechar 100%" (use `/debug` ou sessão técnica direta)

Este protocolo pressupõe que o app está em estado "funciona parcialmente, falta polimento e cobertura". Ideal para pré-lançamento de MVP ou hardening de release.
