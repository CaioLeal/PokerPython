// Abre a linha direta com o Python
const socket = new WebSocket("ws://127.0.0.1:8000/ws");

// Elementos da tela que vamos atualizar
const spanMinhasFichas = document.getElementById("minhas-fichas");
const spanPote = document.getElementById("valor-pote");

// Função para mover a ficha D na tela
function atualizarDealer(quemEODealer) {
    if (quemEODealer === "jogador") {
        document.getElementById("dealer-jogador").style.display = "inline-block";
        document.getElementById("dealer-bot").style.display = "none";
    } else {
        document.getElementById("dealer-jogador").style.display = "none";
        document.getElementById("dealer-bot").style.display = "inline-block";
    }
}

// Função para desenhar a montanha de fichas
function desenharFichas(valorTotal) {
    const container = document.getElementById("fichas-pote");
    container.innerHTML = ""; // Limpa a mesa antes de jogar as novas

    if (valorTotal <= 0) return;

    // Sistema de "Troco" para usar o mínimo de fichas possível
    let restante = valorTotal;
    const valoresFichas = [500, 100, 50, 10];
    const fichasUsadas = [];

    valoresFichas.forEach(valor => {
        while (restante >= valor) {
            fichasUsadas.push(valor);
            restante -= valor;
        }
    });

    // Para ficar igual a uma mesa real, a ficha de maior valor fica embaixo
    fichasUsadas.reverse();

    // Cria os elementos HTML das fichas e empilha
    fichasUsadas.forEach((valorFicha, index) => {
        const elFicha = document.createElement("div");
        elFicha.className = `ficha-poker ficha-${valorFicha}`;
        elFicha.innerText = valorFicha;
        
        // Empilha: Cada ficha sobe 5px em relação à anterior
        const deslocamentoY = index * 5; 
        elFicha.style.bottom = `${deslocamentoY}px`;
        
        // Dá uma "bagunçadinha" milimétrica aleatória para não parecer um pilar duro
        const baguncaX = (Math.random() - 0.5) * 4; 
        elFicha.style.left = `calc(50% - 22.5px + ${baguncaX}px)`;

        container.appendChild(elFicha);
    });

    // O toque final: GSAP para fazê-las cair do céu quicando!
    gsap.from("#fichas-pote .ficha-poker", {
        y: -200,
        opacity: 0,
        duration: 0.6,
        stagger: 0.05,
        ease: "bounce.out"
    });
}

// O que fazer quando a conexão abrir
socket.onopen = () => {
    console.log("🟢 Conexão estabelecida com o backend em Python!");
};

// O que fazer quando o Python mandar dados de volta
socket.onmessage = (event) => {
    const dados = JSON.parse(event.data);
    console.log("📩 Mensagem do servidor:", dados);

    if (dados.tipo === "boas_vindas") {
        spanMinhasFichas.innerText = dados.fichas_jogador;
        spanPote.innerText = dados.pote;
        desenharFichas(dados.pote);
        desenharFichas(dados.pote);
        atualizarDealer(dados.dealer);
        
        // Pega a div onde as cartas do Caio vão ficar
        const divMinhasCartas = document.getElementById("minhas-cartas");
        divMinhasCartas.innerHTML = ""; // Limpa a mesa antes de distribuir
        
        // Para cada carta recebida, cria uma "cartinha" de texto na tela
        divMinhasCartas.innerHTML = ""; 
        
        dados.minhas_cartas.forEach(carta => {
            // Em vez de uma <div>, agora criamos uma <img>
            const elCarta = document.createElement("img");
            
            // Monta o caminho da imagem de forma dinâmica!
            // Ex: /svgs/A-Espadas.svg
            elCarta.src = `/svgs/${carta.valor}_${carta.naipe}.svg`;
            
            // Texto alternativo caso a imagem quebre
            elCarta.alt = `${carta.valor} de ${carta.naipe}`;
            
            // Estilização básica para o tamanho da carta na tela
            elCarta.style.height = "120px";
            elCarta.style.borderRadius = "8px";
            elCarta.style.boxShadow = "0 4px 8px rgba(0,0,0,0.4)";
            
            // Coloca a imagem na mesa
            divMinhasCartas.appendChild(elCarta);
        });

        gsap.from("#minhas-cartas img", { y: -300, opacity: 0, rotation: 180, duration: 0.6, stagger: 0.15, ease: "back.out(1.2)" });
    }
    else if (dados.tipo === "atualizacao_mesa") {
        spanMinhasFichas.innerText = dados.fichas_jogador;
        spanPote.innerText = dados.pote;
        desenharFichas(dados.pote);
        console.log("💰 Dinheiro movimentado:", dados.mensagem);
    }
    // Nova regra: Ouve as cartas viradas no centro da mesa
    else if (dados.tipo === "atualizacao_cartas_mesa") {
        console.log("🃏", dados.mensagem);
        
        const divCartasMesa = document.getElementById("cartas-mesa");
        divCartasMesa.innerHTML = ""; 

        dados.cartas_mesa.forEach(carta => {
            const elCarta = document.createElement("img");
            elCarta.src = `/svgs/${carta.valor}_${carta.naipe}.svg`;
            elCarta.alt = `${carta.valor} de ${carta.naipe}`;
            elCarta.style.height = "120px";
            elCarta.style.borderRadius = "8px";
            elCarta.style.boxShadow = "0 4px 8px rgba(0,0,0,0.4)";
            divCartasMesa.appendChild(elCarta);
        });

        gsap.from("#cartas-mesa img", { scale: 0, opacity: 0, rotation: 45, duration: 0.5, stagger: 0.1, ease: "power2.out" });

        // Se o Python calculou o fim da rodada
        if (dados.showdown) {
            setTimeout(() => {
                alert(dados.showdown.mensagem);

                spanMinhasFichas.innerText = dados.showdown.fichas_jogador;
                spanPote.innerText = "0"; // O pote esvaziou
                desenharFichas(0);
                const divCartasBot = document.getElementById("cartas-bot");
                divCartasBot.innerHTML = "";
                
                dados.showdown.cartas_bot.forEach(carta => {
                    const elCartaBot = document.createElement("img");
                    elCartaBot.src = `/svgs/${carta.valor}_${carta.naipe}.svg`;
                    elCartaBot.style.height = "120px";
                    elCartaBot.style.borderRadius = "8px";
                    elCartaBot.style.boxShadow = "0 4px 8px rgba(0,0,0,0.4)";
                    divCartasBot.appendChild(elCartaBot);
                });

                // Mostra o botão para iniciar a próxima mão
                document.getElementById("btn-nova-rodada").style.display = "inline-block";
            }, 500);
        }
    }
    else if (dados.tipo === "erro") {
        alert(dados.mensagem); // Um alerta simples caso acabe o saldo
    }
};

// Avisa se a conexão cair
socket.onclose = () => {
    console.log("🔴 Conexão com o servidor perdida.");
};

// --- Mapeando os botões para enviar ações ao Python ---

document.getElementById("btn-correr").addEventListener("click", () => {
    socket.send(JSON.stringify({ botao: "correr" }));
});

document.getElementById("btn-pagar").addEventListener("click", () => {
    socket.send(JSON.stringify({ botao: "pagar" }));
});

document.getElementById("btn-apostar").addEventListener("click", () => {
    // Lê o valor digitado no input e transforma em número inteiro
    const valorInput = document.getElementById("input-aposta").value;
    const valorParaApostar = parseInt(valorInput);

    // Validação básica do Texas Hold'em: aposta não pode ser negativa ou vazia
    if (valorParaApostar > 0) {
        // Agora mandamos o botão E o valor da aposta juntos
        socket.send(JSON.stringify({ 
            botao: "apostar", 
            valor: valorParaApostar 
        }));
    } else {
        alert("O valor da aposta deve ser maior que zero!");
    }
});

// Ouve o evento de nova rodada vindo do Python
socket.addEventListener("message", (event) => {
    const dados = JSON.parse(event.data);
    
    if (dados.tipo === "nova_rodada") {
        // Limpa a mesa inteira
        document.getElementById("cartas-mesa").innerHTML = "";
        document.getElementById("cartas-bot").innerHTML = "";
        atualizarDealer(dados.dealer);
        
        // Distribui suas novas cartas
        const divMinhasCartas = document.getElementById("minhas-cartas");
        divMinhasCartas.innerHTML = ""; 
        dados.minhas_cartas.forEach(carta => {
            const elCarta = document.createElement("img");
            elCarta.src = `/svgs/${carta.valor}_${carta.naipe}.svg`;
            elCarta.style.height = "120px";
            elCarta.style.borderRadius = "8px";
            elCarta.style.boxShadow = "0 4px 8px rgba(0,0,0,0.4)";
            divMinhasCartas.appendChild(elCarta);
        });

        gsap.from("#minhas-cartas img", { y: -300, opacity: 0, rotation: 180, duration: 0.6, stagger: 0.15, ease: "back.out(1.2)" });

        // Esconde o botão novamente
        document.getElementById("btn-nova-rodada").style.display = "none";
    }
});

// Envia a ação de recomeçar
document.getElementById("btn-nova-rodada").addEventListener("click", () => {
    socket.send(JSON.stringify({ botao: "nova_rodada" }));
});