// Abre a linha direta com o Python
const socket = new WebSocket("ws://127.0.0.1:8000/ws");

// Elementos da tela que vamos atualizar
const spanMinhasFichas = document.getElementById("minhas-fichas");
const spanPote = document.getElementById("valor-pote");

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
    }
    else if (dados.tipo === "atualizacao_mesa") {
        spanMinhasFichas.innerText = dados.fichas_jogador;
        spanPote.innerText = dados.pote;
        
        console.log("💰 Dinheiro movimentado:", dados.mensagem);
    }
    // Nova regra: Ouve as cartas viradas no centro da mesa
    else if (dados.tipo === "atualizacao_cartas_mesa") {
        console.log("🃏", dados.mensagem);
        
        const divCartasMesa = document.getElementById("cartas-mesa");
        divCartasMesa.innerHTML = ""; // Limpa para não duplicar

        // Renderiza cada carta comunitária exatamente como fez na sua mão
        dados.cartas_mesa.forEach(carta => {
            const elCarta = document.createElement("img");
            elCarta.src = `/svgs/${carta.valor}_${carta.naipe}.svg`;
            elCarta.alt = `${carta.valor} de ${carta.naipe}`;
            
            elCarta.style.height = "120px";
            elCarta.style.borderRadius = "8px";
            elCarta.style.boxShadow = "0 4px 8px rgba(0,0,0,0.4)";
            
            divCartasMesa.appendChild(elCarta);
        });
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