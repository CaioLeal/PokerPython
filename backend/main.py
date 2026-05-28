from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import random
import itertools  # Nativo do Python, sem necessidade de pip install!

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SISTEMA DE PONTUAÇÃO DO POKER ---
VALORES_MAP = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
NOMES_MAOS = {
    8: "Straight Flush", 7: "Quadra", 6: "Full House", 5: "Flush",
    4: "Sequência (Straight)", 3: "Trinca", 2: "Dois Pares", 1: "Um Par", 0: "Carta Alta"
}

def classificar_mao_5_cartas(cartas):
    """Calcula a força de uma combinação exata de 5 cartas"""
    v_ints = sorted([VALORES_MAP[c['valor']] for c in cartas], reverse=True)
    naipes = [c['naipe'] for c in cartas]
    
    is_flush = len(set(naipes)) == 1
    
    # Validação de Sequência (Straight)
    if v_ints == [14, 5, 4, 3, 2]:  # Caso especial do Ás como carta mais baixa (A-2-3-4-5)
        is_straight = True
        v_ints_ranking = [5, 4, 3, 2, 1]
    else:
        is_straight = all(v_ints[i] - v_ints[i+1] == 1 for i in range(4))
        v_ints_ranking = v_ints

    # Contagem de valores repetidos (Pares, Trincas, etc.)
    contagem = {v: v_ints.count(v) for v in set(v_ints)}
    # Ordena por frequência (ex: trinca primeiro) e depois pelo valor da carta
    freq_ordenada = sorted(contagem.items(), key=lambda x: (x[1], x[0]), reverse=True)
    
    padrao_freq = [item[1] for item in freq_ordenada]
    valores_freq = [item[0] for item in freq_ordenada]
    
    # Retorna uma tupla (Rank da Mão, Critérios de Desempate ordenados)
    if is_straight and is_flush: return (8, v_ints_ranking)
    if padrao_freq == [4, 1]:    return (7, valores_freq)
    if padrao_freq == [3, 2]:    return (6, valores_freq)
    if is_flush:                 return (5, v_ints)
    if is_straight:              return (4, v_ints_ranking)
    if padrao_freq == [3, 1, 1]: return (3, valores_freq)
    if padrao_freq == [2, 2, 1]: return (2, valores_freq)
    if padrao_freq == [2, 1, 1, 1]: return (1, valores_freq)
    return (0, v_ints)

def obter_melhor_mao(cartas_totais):
    """Gera as 21 combinações possíveis de 5 cartas e escolhe a maior"""
    todas_combinacoes = itertools.combinations(cartas_totais, 5)
    melhor_pontuacao = (-1, [])
    
    for comb in todas_combinacoes:
        pontuacao = classificar_mao_5_cartas(comb)
        # O Python compara tuplas elemento por elemento nativamente! 
        # Se o Rank for igual, ele olha a lista de valores de desempate automaticamente.
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            
    return melhor_pontuacao

# --- LÓGICA DO DECK ---
def criar_baralho_embaralhado():
    naipes = ['Copas', 'Ouros', 'Paus', 'Espadas']
    valores = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    baralho = [{"valor": v, "naipe": n} for n in naipes for v in valores]
    random.shuffle(baralho)
    return baralho

def tomar_decisao_bot(cartas_bot, cartas_comunitarias):
    """Avalia a força da mão do bot para decidir se ele Paga ou Corre (Fold)"""
    
    # Pré-flop (sem cartas na mesa)
    if len(cartas_comunitarias) == 0:
        valores = [VALORES_MAP[c['valor']] for c in cartas_bot]
        # Se ele tem um par na mão ou cartas altas (J, Q, K, A)
        if valores[0] == valores[1] or max(valores) >= 11:
            chance_pagar = 85 # 85% de chance de aceitar sua aposta
        else:
            chance_pagar = 30 # Mão fraca, foge na maioria das vezes
            
    # Pós-flop (com cartas na mesa)
    else:
        # Reutiliza a nossa função de avaliar mão para ver o que o bot tem!
        rank_atual, _ = obter_melhor_mao(cartas_bot + cartas_comunitarias)
        
        if rank_atual >= 1: # Tem pelo menos um Par
            chance_pagar = 90
        else: # Só tem carta alta
            chance_pagar = 15 # Quase sempre corre, a menos que decida pagar pra ver (blefe)

    # Rola um "dado" de 1 a 100 para dar imprevisibilidade humana
    sorteio = random.randint(1, 100)
    
    if sorteio <= chance_pagar:
        return "pagar"
    else:
        return "correr"
    
# --- SESSÃO WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    fichas_jogador = 1000
    fichas_bot = 1000
    
    # Define o Caio como o primeiro Dealer
    dealer_atual = "jogador" 
    
    # Regra de Heads-Up: Dealer paga Small Blind (10), o outro paga Big Blind (20)
    fichas_jogador -= 10
    fichas_bot -= 20
    pote = 30
    
    baralho = criar_baralho_embaralhado()
    cartas_jogador = [baralho.pop(), baralho.pop()]
    cartas_bot = [baralho.pop(), baralho.pop()]
    cartas_comunitarias = [] 
    
    estado_inicial = {
        "tipo": "boas_vindas",
        "fichas_jogador": fichas_jogador,
        "fichas_bot": fichas_bot,
        "pote": pote,
        "minhas_cartas": cartas_jogador,
        "cartas_adversario": cartas_bot,
        "dealer": dealer_atual # Avisa o frontend quem é o Dealer
    }
    await websocket.send_text(json.dumps(estado_inicial))
    
    try:
        while True:
            data = await websocket.receive_text()
            acao = json.loads(data)
            comando = acao.get("botao")
            
            # --- LÓGICA DE APOSTAR (Raise) ---
            if comando == "apostar":
                valor_aposta = int(acao.get("valor", 0))
                if valor_aposta <= 0:
                    await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": "Aposta inválida."}))
                elif fichas_jogador >= valor_aposta:
                    
                    # Tira suas fichas e põe no pote
                    fichas_jogador -= valor_aposta
                    pote += valor_aposta
                    
                    # --- INTELIGÊNCIA DO BOT AQUI ---
                    decisao_bot = tomar_decisao_bot(cartas_bot, cartas_comunitarias)
                    
                    if decisao_bot == "pagar":
                        # O bot teve coragem e pagou
                        if fichas_bot >= valor_aposta:
                            fichas_bot -= valor_aposta
                            pote += valor_aposta
                            mensagem_acao = f"Você apostou ${valor_aposta}. O Bot analisou e PAGOU."
                        else:
                            pote += fichas_bot
                            mensagem_acao = f"Você apostou ${valor_aposta}. O Bot foi de ALL-IN!"
                            fichas_bot = 0

                        await websocket.send_text(json.dumps({
                            "tipo": "atualizacao_mesa",
                            "fichas_jogador": fichas_jogador,
                            "fichas_bot": fichas_bot,
                            "pote": pote,
                            "mensagem": mensagem_acao
                        }))
                        
                    elif decisao_bot == "correr":
                        # O Bot ficou com medo da sua aposta e fugiu! Você leva o Pote.
                        fichas_jogador += pote
                        mensagem_fim = f"Você apostou ${valor_aposta} e o Bot CORREU! Você puxou o pote."
                        pote = 0
                        
                        # Reutilizamos a estrutura de fim de jogo para o JS mostrar a tela de vitória
                        resultado_fold_bot = {
                            "mensagem": mensagem_fim,
                            "cartas_bot": cartas_bot,
                            "fichas_jogador": fichas_jogador,
                            "fichas_bot": fichas_bot
                        }
                        
                        # Manda o evento disfarçado de cartas de mesa para acionar o fim do jogo no Frontend
                        await websocket.send_text(json.dumps({
                            "tipo": "atualizacao_cartas_mesa",
                            "cartas_mesa": cartas_comunitarias,
                            "mensagem": "O Bot arregou.",
                            "showdown": resultado_fold_bot
                        }))
                        
                else:
                    await websocket.send_text(json.dumps({"tipo": "erro", "mensagem": "Saldo insuficiente."}))

            # --- LÓGICA DE PAGAR / AVANÇAR FASE ---
            elif comando == "pagar":
                resultado_showdown = None
                
                if len(cartas_comunitarias) == 0:
                    cartas_comunitarias.extend([baralho.pop(), baralho.pop(), baralho.pop()])
                    fase = "Flop"
                elif len(cartas_comunitarias) == 3:
                    cartas_comunitarias.append(baralho.pop())
                    fase = "Turn"
                elif len(cartas_comunitarias) == 4:
                    cartas_comunitarias.append(baralho.pop())
                    fase = "River"
                    
                    # --- INTERSEÇÃO DO SHOWDOWN ---
                    rank_j, val_j = obter_melhor_mao(cartas_jogador + cartas_comunitarias)
                    rank_b, val_b = obter_melhor_mao(cartas_bot + cartas_comunitarias)
                    
                    if (rank_j, val_j) > (rank_b, val_b):
                        fichas_jogador += pote
                        mensagem_fim = f"Você ganhou com {NOMES_MAOS[rank_j]} e puxou ${pote}!"
                    elif (rank_b, val_b) > (rank_j, val_j):
                        fichas_bot += pote
                        mensagem_fim = f"O Bot ganhou com {NOMES_MAOS[rank_b]} e puxou ${pote}!"
                    else:
                        fichas_jogador += pote // 2
                        fichas_bot += pote // 2
                        mensagem_fim = f"Empate! Ambos com {NOMES_MAOS[rank_j]}. Pote dividido."
                    
                    pote = 0
                    resultado_showdown = {
                        "mensagem": mensagem_fim,
                        "cartas_bot": cartas_bot,
                        "fichas_jogador": fichas_jogador,
                        "fichas_bot": fichas_bot
                    }
                else:
                    fase = "Mesa Completa"

                await websocket.send_text(json.dumps({
                    "tipo": "atualizacao_cartas_mesa",
                    "cartas_mesa": cartas_comunitarias,
                    "mensagem": f"Avançamos para o {fase}!",
                    "showdown": resultado_showdown
                }))
            
            # --- LÓGICA DE CORRER (Fold) ---
            elif comando == "correr":
                fichas_bot += pote
                mensagem_fim = f"Você correu (Fold). O Bot levou os ${pote} do pote!"
                pote = 0
                
                # Reutilizamos a estrutura do showdown para acionar o fim de jogo no JS
                resultado_fold = {
                    "mensagem": mensagem_fim,
                    "cartas_bot": cartas_bot,
                    "fichas_jogador": fichas_jogador,
                    "fichas_bot": fichas_bot
                }
                
                await websocket.send_text(json.dumps({
                    "tipo": "atualizacao_cartas_mesa",
                    "cartas_mesa": cartas_comunitarias,
                    "mensagem": "Você desistiu da mão.",
                    "showdown": resultado_fold
                }))

            # --- LÓGICA DE INICIAR NOVA RODADA ---
            elif comando == "nova_rodada":
                baralho = criar_baralho_embaralhado()
                cartas_jogador = [baralho.pop(), baralho.pop()]
                cartas_bot = [baralho.pop(), baralho.pop()]
                cartas_comunitarias = []
                
                # Revezamento do Dealer
                dealer_atual = "bot" if dealer_atual == "jogador" else "jogador"
                
                # Cobrança das Blinds baseada em quem é o Dealer
                if dealer_atual == "jogador":
                    fichas_jogador -= 10 # Caio é Dealer (Paga SB)
                    fichas_bot -= 20     # Bot paga BB
                else:
                    fichas_bot -= 10     # Bot é Dealer (Paga SB)
                    fichas_jogador -= 20 # Caio paga BB
                    
                pote = 30
                
                await websocket.send_text(json.dumps({
                    "tipo": "nova_rodada",
                    "minhas_cartas": cartas_jogador,
                    "fichas_jogador": fichas_jogador,
                    "fichas_bot": fichas_bot,
                    "pote": pote,
                    "dealer": dealer_atual # Envia a nova posição
                }))
                    
    except WebSocketDisconnect:
        print("Jogador saiu da mesa.")