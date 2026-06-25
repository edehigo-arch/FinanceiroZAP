# 💚 FinanceiroZap — Controle Financeiro com WhatsApp + IA

Sistema completo de controle financeiro pessoal integrado ao WhatsApp usando Claude AI.

---

## 🚀 O QUE ELE FAZ

- **WhatsApp**: Envie gastos por texto, áudio ou foto de comprovante
- **IA**: Claude interpreta linguagem natural e categoriza automaticamente
- **Dashboard**: Gráficos, tabelas e resumos em tempo real
- **Grátis**: Custo ~R$ 0/mês para uso pessoal

---

## 📋 PASSO A PASSO — DO ZERO AO AR

### PASSO 1: Criar conta na Anthropic (Claude API)

1. Acesse: https://console.anthropic.com
2. Crie sua conta gratuita
3. Vá em **API Keys** → **Create Key**
4. Copie a chave: `sk-ant-...`

---

### PASSO 2: Configurar WhatsApp (Meta)

1. Acesse: https://developers.facebook.com
2. Crie um **App** → escolha "Business"
3. Adicione o produto **WhatsApp**
4. Em **WhatsApp > Getting Started**:
   - Anote o **Phone Number ID**
   - Clique em **Generate Token** e copie o token
5. Adicione seu número como número de teste

---

### PASSO 3: Subir no Railway (hospedagem gratuita)

1. Crie conta em: https://railway.app (login com GitHub)
2. Clique em **New Project** → **Deploy from GitHub repo**
3. Faça upload deste projeto ou conecte ao GitHub
4. Vá em **Variables** e adicione:

```
ANTHROPIC_API_KEY = sk-ant-SUA_CHAVE_AQUI
WHATSAPP_TOKEN = SEU_TOKEN_AQUI
WHATSAPP_PHONE_ID = SEU_PHONE_ID_AQUI
WEBHOOK_VERIFY_TOKEN = financeiro_token_2024
```

5. Railway vai dar uma URL como: `https://seu-app.railway.app`

---

### PASSO 4: Configurar Webhook no Meta

1. Volte em https://developers.facebook.com
2. **WhatsApp > Configuration > Webhook**
3. Clique em **Edit**:
   - **URL**: `https://seu-app.railway.app/webhook`
   - **Verify Token**: `financeiro_token_2024`
4. Clique em **Verify and Save**
5. Em **Webhook fields**, ative: `messages`

---

### PASSO 5: Testar!

No WhatsApp, envie para o número de teste:
- `gastei 45 no uber`
- `recebi 3000 de salário`
- `paguei 120 na farmácia`
- `resumo` (para ver o saldo)

---

## 💻 RODAR LOCALMENTE

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis
cp .env.example .env
# Edite o .env com suas chaves

# Iniciar servidor
python app.py
```

Acesse: http://localhost:5000

Para testar o webhook localmente, use [ngrok](https://ngrok.com):
```bash
ngrok http 5000
# Use a URL do ngrok como webhook no Meta
```

---

## 📱 COMANDOS NO WHATSAPP

| Mensagem | Ação |
|----------|------|
| `gastei 50 no mercado` | Registra despesa |
| `recebi 2000 de freela` | Registra receita |
| `paguei conta de luz 180` | Registra despesa |
| `resumo` ou `saldo` | Mostra resumo do mês |
| [foto de comprovante] | Lê e registra automaticamente |
| [áudio] | Transcreve e registra |

---

## 🗂️ ESTRUTURA DO PROJETO

```
financeiro/
├── app.py              # Backend Flask + API + Webhook
├── templates/
│   └── dashboard.html  # Dashboard web completo
├── requirements.txt    # Dependências Python
├── Procfile           # Configuração Railway
├── railway.toml       # Configuração de deploy
├── .env.example       # Template de variáveis
└── README.md          # Este arquivo
```

---

## 💰 CUSTOS REAIS

| Serviço | Plano | Custo |
|---------|-------|-------|
| Railway | Starter | Grátis (500h/mês) |
| Meta WhatsApp API | Cloud | Grátis (1k conv/mês) |
| Anthropic Claude | Pay-as-you-go | ~R$0,50/mês |
| **TOTAL** | | **~R$ 0,50/mês** |

---

## 🆘 PROBLEMAS COMUNS

**Webhook não verifica:**
- Confira se `WEBHOOK_VERIFY_TOKEN` é o mesmo no `.env` e no Meta

**Mensagens não chegam:**
- No Meta Developer, confirme que ativou o campo `messages` no webhook

**IA não entende:**
- Seja mais específico: "gastei R$ 45,00 no iFood" funciona melhor que "ifood"
