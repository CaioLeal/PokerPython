from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LÓGICA DO JOGO ---
def criar_baralho_embaralhado():
    naipes = ['Copas', 'Ouros', 'Paus', 'Espadas']
    valores = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    
    # Cria uma lista de dicionários combinando cada valor com cada naipe
    baralho = [{"valor": v, "naipe": n} for n in naipes for v in valores]
    
    # Embaralha a lista aleatoriamente
    random.shuffle(baralho)
    return baralho

# --- COMUNICAÇÃO ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    fichas_jogador = 1000
    fichas_bot = 1000
    pote = 0
    
    baralho = criar_baralho_embaralhado()
    cartas_jogador = [baralho.pop(), baralho.pop()]
    cartas_bot = [baralho.pop(), baralho.pop()]
    
    # Nova variável para guardar as cartas do centro da mesa
    cartas_comunitarias = [] 
    
    estado_inicial = {
        "tipo": "boas_vindas",
        "fichas_jogador": fichas_jogador,
        "fichas_bot": fichas_bot,
        "pote": pote,
        "minhas_cartas": cartas_jogador,
        "cartas_adversario": cartas_bot 
    }
    await websocket.send_text(json.dumps(estado_inicial))
    
    try:
        while True:
            data = await websocket.receive_text()
            acao = json.loads(data)
            comando = acao.get("botao")
            
            # --- Lógica de APOSTAR (Raise) ---
            if comando == "apostar":
                valor_aposta = int(acao.get("valor", 0))
                
                if valor_aposta <= 0:
                    await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": "Aposta inválida."}))
                elif fichas_jogador >= valor_aposta:
                    fichas_jogador -= valor_aposta
                    pote += valor_aposta
                    
                    if fichas_bot >= valor_aposta:
                        fichas_bot -= valor_aposta
                        pote += valor_aposta
                        mensagem_acao = f"Você apostou {valor_aposta}. O Bot pagou."
                    else:
                        pote += fichas_bot
                        mensagem_acao = f"Você apostou {valor_aposta}. O Bot foi de All-In com {fichas_bot}!"
                        fichas_bot = 0

                    resposta = {
                        "tipo": "atualizacao_mesa",
                        "fichas_jogador": fichas_jogador,
                        "fichas_bot": fichas_bot,
                        "pote": pote,
                        "mensagem": mensagem_acao
                    }
                    await websocket.send_text(json.dumps(resposta))
                else:
                    await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": "Saldo insuficiente."}))

            # --- Lógica de PAGAR / AVANÇAR FASE ---
            elif comando == "pagar":
                # Verifica em qual fase do jogo estamos
                if len(cartas_comunitarias) == 0:
                    # FLOP: Puxa 3 cartas do baralho
                    cartas_comunitarias.extend([baralho.pop(), baralho.pop(), baralho.pop()])
                    fase = "Flop"
                elif len(cartas_comunitarias) == 3:
                    # TURN: Puxa 1 carta
                    cartas_comunitarias.append(baralho.pop())
                    fase = "Turn"
                elif len(cartas_comunitarias) == 4:
                    # RIVER: Puxa a última carta
                    cartas_comunitarias.append(baralho.pop())
                    fase = "River"
                else:
                    fase = "Showdown (Mesa Completa)"

                # Envia as cartas do centro pro JS
                resposta = {
                    "tipo": "atualizacao_cartas_mesa",
                    "cartas_mesa": cartas_comunitarias,
                    "mensagem": f"Avançamos para o {fase}!"
                }
                await websocket.send_text(json.dumps(resposta))
                    
    except WebSocketDisconnect:
        print("Jogador saiu da mesa.")