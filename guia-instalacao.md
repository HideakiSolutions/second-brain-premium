# Guia de Instalação

Do zero ao vault funcionando. Siga na ordem.

---

## 1. Instalar o Obsidian

O Obsidian é o app que você usa para visualizar e navegar pelas notas do vault. É gratuito.

1. Acesse [obsidian.md/download](https://obsidian.md/download)
2. Baixe a versão para seu sistema (Windows, Mac ou Linux)
3. Instale normalmente

---

## 2. Abrir o vault no Obsidian

1. Descompacte o arquivo .zip do kit numa pasta de fácil acesso (ex: `Documentos/segundo-cerebro/`)
2. Abra o Obsidian
3. Clique em **"Abrir pasta como vault"** (ou "Open folder as vault")
4. Selecione a pasta `segundo-cerebro/` que você descompactou
5. O Obsidian vai abrir com todas as notas visíveis na barra lateral

**Você deve ver na barra lateral:** `_knowledge/`, `_memory/`, `_pipeline/`, `_decisions/`, `_learnings/`, `_prompts/`, `_sessions/`

---

## 3. Instalar o Claude Code

O Claude Code é a ferramenta de linha de comando que roda os slash commands do cérebro. Ele precisa do Node.js.

### 3a. Instalar o Node.js (se não tiver)

1. Acesse [nodejs.org](https://nodejs.org)
2. Baixe a versão **LTS** (recomendada)
3. Instale normalmente
4. Verifique a instalação abrindo o terminal e digitando:
   ```
   node --version
   ```
   Deve mostrar algo como `v20.x.x` ou superior.

### 3b. Instalar o Claude Code

No terminal, digite:
```
npm install -g @anthropic-ai/claude-code
```

Verifique a instalação:
```
claude --version
```

### 3c. Autenticar

No terminal, digite:
```
claude login
```

Siga as instruções para conectar sua conta da Anthropic. Você precisa de uma assinatura ativa do Claude (Pro, Max ou API).

---

## 4. Abrir o Claude Code no vault

Navegue até a pasta do vault no terminal e inicie o Claude Code:

```
cd ~/Documentos/segundo-cerebro
claude
```

**No Windows:**
```
cd C:\Users\SeuUsuario\Documentos\segundo-cerebro
claude
```

Quando o Claude Code abrir, ele vai ler automaticamente o `CLAUDE.md` e já estará configurado com as regras do segundo cérebro.

---

## 5. Verificar que funciona

Rode o comando de teste:

```
/daily-briefing
```

Se tudo estiver certo, o cérebro vai gerar um briefing (mesmo que ainda com placeholders, ele funciona). Se der erro, veja a seção de Troubleshooting abaixo.

---

## 6. Próximo passo

Vá para o [[guia-personalizacao]] e preencha sua identidade e knowledge base. É o que transforma o template genérico no **seu** segundo cérebro.

---

## Opcional: Sincronizar com Git

Se quiser manter backup e histórico do vault, você pode sincronizar com o GitHub.

### Opção A: Via terminal (recomendado para devs)

```
cd ~/Documentos/segundo-cerebro
git init
git add .
git commit -m "setup inicial do segundo cérebro"
```

Crie um repositório **privado** no GitHub e conecte:
```
git remote add origin https://github.com/seu-usuario/segundo-cerebro.git
git push -u origin main
```

### Opção B: Via plugin do Obsidian

1. No Obsidian, vá em **Configurações → Plugins da comunidade**
2. Desative o **Modo restrito**
3. Busque e instale o plugin **Obsidian Git**
4. Configure o plugin com seu repositório GitHub
5. O plugin faz commit e push automáticos a cada X minutos

**Importante:** Se for usar Git, garanta que o repositório é **privado**. Seu vault contém informações pessoais.

---

## Troubleshooting

### "claude: command not found"
O Claude Code não foi instalado globalmente. Tente:
```
npm install -g @anthropic-ai/claude-code
```
Se persistir, verifique se o npm global está no PATH do sistema.

### "Error: CLAUDE.md not found"
Você abriu o Claude Code numa pasta errada. Verifique se está dentro da pasta `segundo-cerebro/`:
```
ls CLAUDE.md
```
Se não aparecer, navegue até a pasta correta com `cd`.

### "Erro de autenticação"
Rode `claude login` novamente. Verifique se sua assinatura está ativa em [console.anthropic.com](https://console.anthropic.com).

### O Obsidian não mostra as pastas
Verifique se você abriu a pasta `segundo-cerebro/` como vault, não uma pasta acima ou abaixo. A pasta raiz do vault deve conter o `CLAUDE.md`.

### Os slash commands não aparecem
Os commands ficam em `.claude/commands/`. A pasta `.claude` é oculta por padrão. No Obsidian, vá em **Configurações → Arquivos e links** e ative **Mostrar arquivos ocultos**. No terminal, use `ls -la` para ver a pasta.

### "Preciso do Claude Max/Pro?"
O kit funciona com qualquer plano do Claude Code (Pro, Max ou API). Ele não requer nenhum plano específico - é um acelerador para quem já usa Claude Code.
