import os
import json
import sqlite3
import base64
import requests
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "financeirozap")

# ─── BANCO DE DADOS ───────────────────────────────────────────────
def get_db():
    db = sqlite3.connect("financeiro.db")
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('receita','despesa')),
            categoria TEXT NOT NULL,
            data TEXT NOT NULL,
            fonte TEXT DEFAULT 'manual',
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            emoji TEXT DEFAULT '💰'
        );
        INSERT OR IGNORE INTO categorias (nome, tipo, emoji) VALUES
            ('Alimentação','despesa','🍔'),
            ('Transporte','despesa','🚗'),
            ('Saúde','despesa','💊'),
            ('Lazer','despesa','🎮'),
            ('Moradia','despesa','🏠'),
            ('Educação','despesa','📚'),
            ('Vestuário','despesa','👕'),
            ('Outros','despesa','📦'),
            ('Salário','receita','💼'),
            ('Freelance','receita','💻'),
            ('Investimentos','receita','📈'),
            ('Outros Recebimentos','receita','💰');
    """)
    db.commit()
    db.close()

# ─── GEMINI AI ────────────────────────────────────────────────────
def interpretar_mensagem(texto=None, imagem_base64=None, audio_texto=None):
    categorias = [
        "Alimentação","Transporte","Saúde","Lazer","Moradia",
        "Educação","Vestuário","Salário","Freelance","Investimentos",
        "Outros","Outros Recebimentos"
    ]
    hoje = date.today().isoformat()

    prompt = f"""Você é um assistente financeiro pessoal.
Hoje é {hoje}.
Analise a mensagem e extraia a transação financeira.

Categorias disponíveis: {', '.join(categorias)}

Responda SOMENTE com JSON válido, sem markdown, sem explicações:
{{
  "tipo": "despesa" ou "receita",
  "valor": número (apenas números, sem R$),
  "descricao": "descrição curta",
  "categoria": "uma das categorias acima",
  "data": "YYYY-MM-DD",
  "encontrou": true ou false,
  "resposta": "mensagem amigável para o usuário (máx 100 chars)"
}}

Se não encontrar transação financeira, retorne encontrou: false e uma resposta orientando o usuário.

Mensagem: {texto or audio_texto or 'Analise o comprovante da imagem.'}
"""

    parts = [{"text": prompt}]
    if imagem_base64:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": imagem_base64}})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 500}
    }

try:
        r = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        resposta_json = r.json()
        
        if "candidates" in resposta_json and len(resposta_json["candidates"]) > 0:
            candidate = resposta_json["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                raw = candidate["content"]["parts"][0]["text"].strip()
                raw = raw.replace("```json", "").replace("```", "").strip()
                return json.loads(raw)
        
        # Estas duas linhas agora estão alinhadas corretamente fora do IF interno
        print(f"Erro ou estrutura inesperada do Gemini: {resposta_json}")
        return {"encontrou": False, "resposta": "Desculpe, a IA não gerou uma resposta válida."}

    except Exception as e:
        # Estas duas linhas agora estão com os espaços certos para dentro do except
        print(f"Erro ao processar mensagem no Gemini: {e}")
        return {"encontrou": False, "resposta": "Estou instável no momento. Tente novamente."}
# ─── EVOLUTION API: ENVIAR MENSAGEM ──────────────────────────────
def enviar_whatsapp(numero, mensagem):
    if not EVOLUTION_API_URL or not EVOLUTION_API_KEY:
        print(f"[WhatsApp] {numero}: {mensagem}")
        return
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"number": numero, "text": mensagem}
    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar WhatsApp: {e}")

# ─── WEBHOOK EVOLUTION API ────────────────────────────────────────
@app.route("/webhook", methods=["GET"])
def webhook_verify():
    return jsonify({"status": "ok"})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        # Formato Evolution API
        event = data.get("event", "")
        if event != "messages.upsert":
            return jsonify({"status": "ok"})

        msg_data = data.get("data", {})
        key = msg_data.get("key", {})
        
        # Ignorar mensagens enviadas pelo próprio bot
        if key.get("fromMe", False):
            return jsonify({"status": "ok"})

        numero = key.get("remoteJid", "").replace("@s.whatsapp.net", "")
        message = msg_data.get("message", {})

        texto = None
        imagem_b64 = None

        # Texto simples
        if "conversation" in message:
            texto = message["conversation"]
        elif "extendedTextMessage" in message:
            texto = message["extendedTextMessage"]["text"]
        elif "imageMessage" in message:
            # Imagem - por enquanto tratar como texto
            texto = "comprovante enviado por imagem"

        if not texto:
            return jsonify({"status": "ok"})

        # Comandos especiais
        if texto.lower() in ["resumo", "relatório", "relatorio", "saldo", "r"]:
            resposta = gerar_resumo_texto()
            enviar_whatsapp(numero, resposta)
            return jsonify({"status": "ok"})

        if texto.lower() in ["ajuda", "help", "?"]:
            resposta = ("💡 *Como usar o FinanceiroZAP:*\n\n"
                       "💸 'gastei 50 no uber'\n"
                       "💰 'recebi 3000 de salário'\n"
                       "🏥 'paguei 120 na farmácia'\n"
                       "📊 'resumo' → ver saldo do mês")
            enviar_whatsapp(numero, resposta)
            return jsonify({"status": "ok"})

        # Interpretar com Gemini
        resultado = interpretar_mensagem(texto)

        if resultado.get("encontrou"):
            salvar_transacao(resultado, fonte="whatsapp")
            emoji = "💸" if resultado["tipo"] == "despesa" else "💰"
            resposta = f"{emoji} {resultado['resposta']}\n\n📊 Digite *resumo* para ver seu saldo."
        else:
            resposta = resultado.get("resposta", "Não entendi. Tente: 'gastei 50 no mercado'\nDigite *ajuda* para ver exemplos.")

        enviar_whatsapp(numero, resposta)

    except Exception as e:
        print(f"Erro webhook: {e}")

    return jsonify({"status": "ok"})

def salvar_transacao(dados, fonte="manual"):
    db = get_db()
    db.execute("""
        INSERT INTO transacoes (descricao, valor, tipo, categoria, data, fonte)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (dados["descricao"], dados["valor"], dados["tipo"],
          dados["categoria"], dados["data"], fonte))
    db.commit()
    db.close()

def gerar_resumo_texto():
    db = get_db()
    mes_atual = datetime.now().strftime("%Y-%m")
    rows = db.execute("""
        SELECT tipo, SUM(valor) as total FROM transacoes
        WHERE data LIKE ? GROUP BY tipo
    """, (f"{mes_atual}%",)).fetchall()
    
    por_cat = db.execute("""
        SELECT categoria, SUM(valor) as total FROM transacoes
        WHERE data LIKE ? AND tipo='despesa'
        GROUP BY categoria ORDER BY total DESC LIMIT 3
    """, (f"{mes_atual}%",)).fetchall()
    db.close()

    receitas = next((r["total"] for r in rows if r["tipo"] == "receita"), 0)
    despesas = next((r["total"] for r in rows if r["tipo"] == "despesa"), 0)
    saldo = receitas - despesas
    emoji = "✅" if saldo >= 0 else "⚠️"

    resumo = (f"📊 *Resumo {datetime.now().strftime('%B/%Y')}*\n\n"
              f"💰 Receitas: R$ {receitas:,.2f}\n"
              f"💸 Despesas: R$ {despesas:,.2f}\n"
              f"{emoji} Saldo: R$ {saldo:,.2f}")
    
    if por_cat:
        resumo += "\n\n🏆 *Top despesas:*"
        for c in por_cat:
            resumo += f"\n• {c['categoria']}: R$ {c['total']:,.2f}"
    
    return resumo

# ─── API DASHBOARD ────────────────────────────────────────────────
@app.route("/api/resumo")
def api_resumo():
    db = get_db()
    mes = request.args.get("mes", datetime.now().strftime("%Y-%m"))
    totais = db.execute("SELECT tipo, SUM(valor) as total FROM transacoes WHERE data LIKE ? GROUP BY tipo", (f"{mes}%",)).fetchall()
    por_categoria = db.execute("SELECT categoria, tipo, SUM(valor) as total, COUNT(*) as qtd FROM transacoes WHERE data LIKE ? GROUP BY categoria, tipo ORDER BY total DESC", (f"{mes}%",)).fetchall()
    evolucao = db.execute("SELECT substr(data,1,7) as mes, tipo, SUM(valor) as total FROM transacoes GROUP BY mes, tipo ORDER BY mes").fetchall()
    ultimas = db.execute("SELECT * FROM transacoes ORDER BY criado_em DESC LIMIT 20").fetchall()
    db.close()
    receitas = next((r["total"] for r in totais if r["tipo"] == "receita"), 0)
    despesas = next((r["total"] for r in totais if r["tipo"] == "despesa"), 0)
    return jsonify({"saldo": receitas - despesas, "receitas": receitas, "despesas": despesas, "por_categoria": [dict(r) for r in por_categoria], "evolucao": [dict(r) for r in evolucao], "ultimas": [dict(r) for r in ultimas]})

@app.route("/api/transacoes", methods=["GET"])
def api_transacoes():
    db = get_db()
    mes = request.args.get("mes", "")
    if mes:
        rows = db.execute("SELECT * FROM transacoes WHERE data LIKE ? ORDER BY data DESC", (f"{mes}%",)).fetchall()
    else:
        rows = db.execute("SELECT * FROM transacoes ORDER BY data DESC").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/transacoes", methods=["POST"])
def api_adicionar():
    dados = request.get_json()
    if "texto_livre" in dados:
        resultado = interpretar_mensagem(dados["texto_livre"])
        if resultado.get("encontrou"):
            salvar_transacao(resultado, fonte="dashboard")
            return jsonify({"ok": True, "transacao": resultado})
        return jsonify({"ok": False, "erro": resultado.get("resposta")}), 400
    salvar_transacao(dados, fonte="dashboard")
    return jsonify({"ok": True})

@app.route("/api/transacoes/<int:id>", methods=["DELETE"])
def api_deletar(id):
    db = get_db()
    db.execute("DELETE FROM transacoes WHERE id = ?", (id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})

@app.route("/")
def index():
    return render_template("dashboard.html")

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
