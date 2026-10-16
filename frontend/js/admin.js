
const STATUS = {
    recebido: "Recebido",
    confirmado: "Confirmado",
    em_preparo: "Em preparo",
    pronto_retirada: "Pronto para retirada",
    saiu_entrega: "Saiu para entrega",
    entregue: "Entregue",
    cancelado: "Cancelado"
};

const STATUS_ABERTOS = [
    "recebido",
    "confirmado",
    "em_preparo",
    "pronto_retirada",
    "saiu_entrega"
];

const $ = (seletor) => document.querySelector(seletor);

const telaLogin = $("#tela-login");
const telaPainel = $("#tela-painel");
const formLogin = $("#form-login");
const campoSenha = $("#senha");
const erroLogin = $("#erro-login");
const mensagemPainel = $("#mensagem-painel");
const listaPedidos = $("#lista-pedidos");
const botaoSair = $("#btn-sair");
const dialogDetalhes = $("#dialog-detalhes");

let pedidos = [];
let produtos = [];
let categorias = [];
let cupons = [];

function dinheiro(valor) {
    return Number(valor || 0).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    });
}

function elemento(tag, classe, texto) {
    const el = document.createElement(tag);

    if (classe) el.className = classe;
    if (texto !== undefined) el.textContent = texto;

    return el;
}

async function requisicao(caminho, opcoes = {}) {
    const resposta = await fetch(`/api/admin${caminho}`, {
        credentials: "same-origin",
        ...opcoes,
        headers: {
            "Content-Type": "application/json",
            ...(opcoes.headers || {})
        }
    });

    const dados = await resposta.json().catch(() => ({}));

    if (!resposta.ok) {
        throw new Error(
            dados.error ||
            dados.erro ||
            dados.mensagem ||
            "Não foi possível concluir a operação."
        );
    }

    return dados;
}

function mostrarPainel() {
    telaLogin.hidden = true;
    telaPainel.hidden = false;
    botaoSair.hidden = false;
}

function mostrarLogin() {
    telaLogin.hidden = false;
    telaPainel.hidden = true;
    botaoSair.hidden = true;
}

function mostrarMensagem(texto, erro = false) {
    mensagemPainel.textContent = texto;
    mensagemPainel.classList.toggle("erro", erro);
}

/* =========================
   NAVEGAÇÃO ENTRE ABAS
========================= */

function alternarAba(nome) {
    const secoes = {
        pedidos: $("#secao-pedidos"),
        produtos: $("#secao-produtos"),
        categorias: $("#secao-categorias"),
        cupons: $("#secao-cupons"),
        configuracoes: $("#secao-configuracoes")
    };

    for (const [chave, secao] of Object.entries(secoes)) {
        if (secao) {
            secao.hidden = chave !== nome;
        }
    }

    document.querySelectorAll(".aba-admin").forEach((botao) => {
        const ativa = botao.dataset.aba === nome;

        botao.classList.toggle("ativa", ativa);
        botao.classList.toggle("btn-primary", ativa);
        botao.classList.toggle("btn-light", !ativa);
    });

    mostrarMensagem("");

    if (nome === "pedidos") carregarPedidos();
    if (nome === "produtos") carregarProdutos();
    if (nome === "categorias") carregarCategorias();
    if (nome === "cupons") carregarCupons();
    if (nome === "configuracoes") carregarConfiguracoes();
}

document.querySelectorAll(".aba-admin").forEach((botao) => {
    botao.addEventListener("click", () => {
        alternarAba(botao.dataset.aba);
    });
});

/* =========================
   LOGIN E SESSÃO
========================= */

formLogin.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    erroLogin.textContent = "Verificando acesso...";

    try {
        await requisicao("/login", {
            method: "POST",
            body: JSON.stringify({ senha: campoSenha.value })
        });

        campoSenha.value = "";
        erroLogin.textContent = "";

        mostrarPainel();
        await carregarPedidos();
    } catch (erro) {
        erroLogin.textContent = erro.message;
    }
});

async function verificarSessao() {
    try {
        const dados = await requisicao("/sessao");

        if (dados.autenticado) {
            mostrarPainel();
            await carregarPedidos();
        } else {
            mostrarLogin();
        }
    } catch {
        mostrarLogin();
    }
}

/* =========================
   PEDIDOS
========================= */

async function carregarPedidos() {
    listaPedidos.replaceChildren();

    const linha = elemento("tr");
    const celula = elemento("td", "", "Carregando pedidos...");
    celula.colSpan = 6;
    linha.append(celula);
    listaPedidos.append(linha);

    mostrarMensagem("");

    try {
        const dados = await requisicao("/pedidos");

        pedidos = Array.isArray(dados)
            ? dados
            : (dados.pedidos || dados.data || []);

        renderizarPedidos();
    } catch (erro) {
        listaPedidos.replaceChildren();

        const linhaErro = elemento("tr");
        const celulaErro = elemento("td", "", erro.message);
        celulaErro.colSpan = 6;
        linhaErro.append(celulaErro);
        listaPedidos.append(linhaErro);

        mostrarMensagem("Não foi possível carregar os pedidos.", true);
    }
}

function renderizarPedidos() {
    listaPedidos.replaceChildren();

    $("#total-pedidos").textContent = pedidos.length;

    const abertos = pedidos.filter((pedido) =>
        STATUS_ABERTOS.includes(String(pedido.status || "").toLowerCase())
    );

    $("#pedidos-abertos").textContent = abertos.length;

    const total = pedidos.reduce(
        (soma, pedido) => soma + Number(pedido.total || 0),
        0
    );

    $("#valor-pedidos").textContent = dinheiro(total);

    if (!pedidos.length) {
        const linha = elemento("tr");
        const celula = elemento("td", "", "Nenhum pedido encontrado.");
        celula.colSpan = 6;
        linha.append(celula);
        listaPedidos.append(linha);
        return;
    }

    for (const pedido of pedidos) {
        const linha = elemento("tr");
        const numero = pedido.numero || pedido.id || "—";

        const data = pedido.criado_em
            ? new Date(pedido.criado_em).toLocaleString("pt-BR")
            : "—";

        linha.append(
            elemento("td", "", `#${numero}`),
            elemento("td", "", pedido.nome_cliente || "Cliente"),
            elemento("td", "", data),
            elemento("td", "", dinheiro(pedido.total))
        );

        const celulaStatus = elemento("td");
        const seletor = document.createElement("select");

        for (const [valor, nome] of Object.entries(STATUS)) {
            const opcao = document.createElement("option");
            opcao.value = valor;
            opcao.textContent = nome;
            opcao.selected =
                String(pedido.status || "").toLowerCase() === valor;

            seletor.append(opcao);
        }

        seletor.addEventListener("change", () => {
            alterarStatus(pedido.id, seletor.value, seletor);
        });

        celulaStatus.append(seletor);

        const celulaAcoes = elemento("td");
        const botaoDetalhes = elemento("button", "btn btn-light", "Detalhes");
        botaoDetalhes.type = "button";
        botaoDetalhes.addEventListener("click", () => {
            abrirDetalhes(pedido.id);
        });

        celulaAcoes.append(botaoDetalhes);
        linha.append(celulaStatus, celulaAcoes);
        listaPedidos.append(linha);
    }
}

async function alterarStatus(id, status, seletor) {
    seletor.disabled = true;
    mostrarMensagem("Atualizando status...");

    try {
        await requisicao(`/pedidos/${id}/status`, {
            method: "PATCH",
            body: JSON.stringify({ status })
        });

        mostrarMensagem("Status atualizado.");
        await carregarPedidos();
    } catch (erro) {
        mostrarMensagem(erro.message, true);
        await carregarPedidos();
    } finally {
        seletor.disabled = false;
    }
}

function linhaDetalhe(rotulo, valor) {
    const linha = elemento("div", "detalhe-linha");

    linha.append(
        elemento("span", "", rotulo),
        elemento("strong", "", valor ?? "—")
    );

    return linha;
}

function secaoDetalhe(titulo) {
    const secao = elemento("section");
    secao.style.marginBottom = "22px";
    secao.append(elemento("h3", "", titulo));
    return secao;
}

function adicionarItemPedido(item, destino) {
    const bloco = elemento("div", "item-pedido");

    bloco.append(
        elemento(
            "strong",
            "",
            `${item.quantidade || 1} × ${item.nome_produto || "Produto"}`
        ),
        linhaDetalhe("Preço unitário", dinheiro(item.preco_unitario)),
        linhaDetalhe("Subtotal", dinheiro(item.subtotal))
    );

    if (item.observacao) {
        bloco.append(elemento("p", "", `Observação: ${item.observacao}`));
    }

    for (const opcao of item.opcoes || []) {
        bloco.append(
            elemento(
                "p",
                "",
                `${opcao.nome_grupo || "Opção"}: ${opcao.nome_opcao || ""} (+ ${dinheiro(opcao.preco_adicional)})`
            )
        );
    }

    destino.append(bloco);
}

async function abrirDetalhes(id) {
    $("#detalhe-titulo").textContent = `Pedido #${id}`;

    const conteudo = $("#detalhe-conteudo");
    conteudo.replaceChildren(elemento("p", "", "Carregando detalhes..."));

    dialogDetalhes.showModal();

    try {
        const dados = await requisicao(`/pedidos/${id}`);
        const pedido = dados.pedido || dados;

        conteudo.replaceChildren();

        const resumo = secaoDetalhe("Informações do pedido");

        resumo.append(
            linhaDetalhe("Cliente", pedido.nome_cliente),
            linhaDetalhe("Telefone", pedido.telefone_cliente),
            linhaDetalhe("Modalidade", pedido.modalidade),
            linhaDetalhe(
                "Status",
                STATUS[String(pedido.status).toLowerCase()] || pedido.status
            ),
            linhaDetalhe("Subtotal", dinheiro(pedido.subtotal)),
            linhaDetalhe("Entrega", dinheiro(pedido.taxa_entrega)),
            linhaDetalhe("Desconto", dinheiro(pedido.desconto)),
            linhaDetalhe("Total", dinheiro(pedido.total))
        );

        conteudo.append(resumo);

        const itens = secaoDetalhe("Produtos");

        if (pedido.itens?.length) {
            for (const item of pedido.itens) {
                adicionarItemPedido(item, itens);
            }
        } else {
            itens.append(elemento("p", "", "Nenhum item retornado."));
        }

        conteudo.append(itens);

        if (pedido.pagamentos?.length) {
            const pagamentos = secaoDetalhe("Pagamento");

            for (const pagamento of pedido.pagamentos) {
                pagamentos.append(
                    linhaDetalhe("Forma", pagamento.forma),
                    linhaDetalhe("Valor", dinheiro(pagamento.valor)),
                    linhaDetalhe("Status", pagamento.status)
                );

                if (pagamento.troco_para) {
                    pagamentos.append(
                        linhaDetalhe("Troco para", dinheiro(pagamento.troco_para))
                    );
                }
            }

            conteudo.append(pagamentos);
        }
    } catch (erro) {
        conteudo.replaceChildren(elemento("p", "mensagem", erro.message));
    }
}

/* =========================
   CATEGORIAS
========================= */

async function carregarCategorias() {
    const lista = $("#lista-categorias");

    if (lista) {
        lista.replaceChildren();

        const linha = elemento("tr");
        const celula = elemento("td", "", "Carregando categorias...");
        celula.colSpan = 4;
        linha.append(celula);
        lista.append(linha);
    }

    try {
        const dados = await requisicao("/categorias");

        const listaRecebida = Array.isArray(dados)
            ? dados
            : (
                dados.categorias ||
                dados.data ||
                dados.items ||
                dados.resultados ||
                dados.data?.categorias ||
                []
            );

        categorias = Array.isArray(listaRecebida)
            ? listaRecebida.map(normalizarCategoria)
            : [];

        renderizarCategorias();
        preencherSelectCategorias();

        return true;
    } catch (erro) {
        categorias = [];
        
/* =========================
   CADASTRAR CATEGORIAS
========================= */

function abrirFormularioCategoria() {
    const formulario = $("#form-categoria");
    const card = $("#formulario-categoria-card");

    if (!formulario || !card) return;

    formulario.reset();

    $("#categoria-ordem").value = "0";
    $("#categoria-ativa").checked = true;
    $("#mensagem-categoria").textContent = "";

    card.hidden = false;

    card.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    $("#categoria-nome").focus();
}

function fecharFormularioCategoria() {
    const formulario = $("#form-categoria");
    const card = $("#formulario-categoria-card");

    if (formulario) formulario.reset();
    if (card) card.hidden = true;

    const mensagem = $("#mensagem-categoria");

    if (mensagem) {
        mensagem.textContent = "";
        mensagem.classList.remove("erro");
    }
}

async function salvarCategoria(evento) {
    evento.preventDefault();

    const nome = $("#categoria-nome").value.trim();
    const descricao = $("#categoria-descricao").value.trim();
    const imagemUrl = $("#categoria-imagem").value.trim();
    const ordemTexto = $("#categoria-ordem").value.trim();
    const mensagem = $("#mensagem-categoria");
    const botao = $("#btn-salvar-categoria");

    if (!nome) {
        mensagem.textContent = "Informe o nome da categoria.";
        mensagem.classList.add("erro");
        return;
    }

    const ordem = Number(ordemTexto);

    if (
        ordemTexto === "" ||
        !Number.isInteger(ordem) ||
        ordem < 0 ||
        ordem > 65535
    ) {
        mensagem.textContent = "Informe uma ordem válida entre 0 e 65535.";
        mensagem.classList.add("erro");
        return;
    }

    const dadosCategoria = {
        name: nome,
        description: descricao,
        image_url: imagemUrl,
        order: ordem,
        active: $("#categoria-ativa").checked
    };

    botao.disabled = true;
    mensagem.classList.remove("erro");
    mensagem.textContent = "Salvando categoria...";

    try {
        await requisicao("/categorias", {
            method: "POST",
            body: JSON.stringify(dadosCategoria)
        });

        mensagem.textContent = "Categoria cadastrada com sucesso!";

        mostrarMensagem("Categoria cadastrada com sucesso.");

        await carregarCategorias();

        fecharFormularioCategoria();

    } catch (erro) {
        mensagem.textContent = erro.message;
        mensagem.classList.add("erro");
    } finally {
        botao.disabled = false;
    }
}

/* Eventos do formulário de categorias */

$("#btn-nova-categoria")?.addEventListener(
    "click",
    abrirFormularioCategoria
);

$("#btn-cancelar-categoria")?.addEventListener(
    "click",
    fecharFormularioCategoria
);

$("#form-categoria")?.addEventListener(
    "submit",
    salvarCategoria
);

        preencherSelectCategorias();

        if (lista) {
            lista.replaceChildren();

            const linhaErro = elemento("tr");
            const celulaErro = elemento("td", "", erro.message);
            celulaErro.colSpan = 4;
            linhaErro.append(celulaErro);
            lista.append(linhaErro);
        }

        mostrarMensagem(
            "Não foi possível carregar as categorias: " + erro.message,
            true
        );

        return false;
    }
}

function normalizarCategoria(categoria) {
    const valorAtivo =
        categoria.active ??
        categoria.ativo ??
        categoria.is_active ??
        categoria.ativa;

    const ativa = valorAtivo === undefined || valorAtivo === null
        ? true
        : (
            valorAtivo === true ||
            valorAtivo === 1 ||
            valorAtivo === "1" ||
            String(valorAtivo).toLowerCase() === "true" ||
            String(valorAtivo).toLowerCase() === "sim"
        );

    return {
        ...categoria,
        id: categoria.id ?? categoria.id_categoria ?? categoria.category_id,
        name: categoria.name ?? categoria.nome ?? categoria.nome_categoria ?? "",
        description: categoria.description ?? categoria.descricao ?? "",
        order: categoria.order ?? categoria.ordem ?? categoria.ordem_exibicao,
        active: ativa
    };
}

function renderizarCategorias() {
    const lista = $("#lista-categorias");
    lista.replaceChildren();

    if (!categorias.length) {
        const linha = elemento("tr");
        const celula = elemento("td", "", "Nenhuma categoria encontrada.");
        celula.colSpan = 4;
        linha.append(celula);
        lista.append(linha);
        return;
    }

    for (const categoria of categorias) {
        const linha = elemento("tr");

        linha.append(
            elemento("td", "", categoria.name || "—"),
            elemento("td", "", categoria.description || "—"),
            elemento("td", "", String(categoria.order ?? "—")),
            elemento("td", "", categoria.active ? "Sim" : "Não")
        );

        lista.append(linha);
    }
}

function preencherSelectCategorias() {
    const select = $("#produto-categoria");

    if (!select) return;

    const valorAtual = select.value;

    select.replaceChildren();

    const inicial = elemento("option", "", "Selecione uma categoria");
    inicial.value = "";
    select.append(inicial);

    for (const categoria of categorias) {
        if (
            !categoria.active ||
            categoria.id === undefined ||
            categoria.id === null
        ) {
            continue;
        }

        const nome = String(categoria.name || "").trim();

        if (!nome) continue;

        const opcao = elemento("option", "", nome);
        opcao.value = String(categoria.id);
        select.append(opcao);
    }

    if ([...select.options].some((opcao) => opcao.value === valorAtual)) {
        select.value = valorAtual;
    }
}

/* =========================
   PRODUTOS
========================= */

async function carregarProdutos() {
    const lista = $("#lista-produtos");
    lista.replaceChildren();

    const linha = elemento("tr");
    const celula = elemento("td", "", "Carregando produtos...");
    celula.colSpan = 6;
    linha.append(celula);
    lista.append(linha);

    mostrarMensagem("");

    try {
        const dados = await requisicao("/produtos");

        produtos = Array.isArray(dados)
            ? dados
            : (dados.data || dados.produtos || []);

        renderizarProdutos();
    } catch (erro) {
        lista.replaceChildren();

        const linhaErro = elemento("tr");
        const celulaErro = elemento("td", "", erro.message);
        celulaErro.colSpan = 6;
        linhaErro.append(celulaErro);
        lista.append(linhaErro);

        mostrarMensagem("Não foi possível carregar os produtos.", true);
    }
}

function renderizarProdutos() {
    const lista = $("#lista-produtos");
    lista.replaceChildren();

    if (!produtos.length) {
        const linha = elemento("tr");
        const celula = elemento("td", "", "Nenhum produto encontrado.");
        celula.colSpan = 6;
        linha.append(celula);
        lista.append(linha);
        return;
    }

    for (const produto of produtos) {
        const linha = elemento("tr");

        const temPromocao =
            produto.promo_price !== null &&
            produto.promo_price !== undefined &&
            produto.promo_price !== "";

        const precoExibido = temPromocao
            ? `${dinheiro(produto.promo_price)} (Promoção)`
            : dinheiro(produto.price);

        linha.append(
            elemento("td", "", produto.name || "—"),
            elemento("td", "", produto.category_name || "—"),
            elemento("td", "", precoExibido),
            elemento("td", "", produto.available ? "Disponível" : "Indisponível"),
            elemento("td", "", produto.active ? "Sim" : "Não")
        );

        const acoes = elemento("td");

        const editar = elemento("button", "btn btn-light", "Editar");
        editar.type = "button";

        editar.addEventListener("click", async () => {
            const carregou = await carregarCategorias();

            if (!carregou) return;

            abrirFormularioProduto(produto);
        });

        const duplicar = elemento("button", "btn btn-light", "Duplicar");
        duplicar.type = "button";
        duplicar.addEventListener("click", () => duplicarProduto(produto.id));

        const ativo = elemento(
            "button",
            "btn btn-light",
            produto.active ? "Desativar" : "Ativar"
        );

        ativo.type = "button";
        ativo.addEventListener("click", () => alterarAtivoProduto(produto));

        acoes.append(editar, duplicar, ativo);
        linha.append(acoes);
        lista.append(linha);
    }
}

function abrirFormularioProduto(produto = null) {
    $("#formulario-produto-card").hidden = false;
    $("#form-produto").reset();

    $("#produto-id").value = produto?.id || "";
    $("#titulo-form-produto").textContent = produto
        ? "Editar produto"
        : "Cadastrar produto";

    $("#produto-nome").value = produto?.name || "";
    $("#produto-descricao").value = produto?.description || "";
    $("#produto-preco").value = produto?.price ?? "";

    const campoPromocional = $("#produto-preco-promocional");

    if (campoPromocional) {
        campoPromocional.value = produto?.promo_price ?? "";
    }

    $("#produto-imagem").value = produto?.image_url || "";
    $("#produto-preparo").value = produto?.prep_minutes ?? "";

    $("#produto-disponivel").checked = produto
        ? Boolean(produto.available)
        : true;

    $("#produto-destaque").checked = Boolean(produto?.featured);

    preencherSelectCategorias();

    $("#produto-categoria").value = produto?.category_id
        ? String(produto.category_id)
        : "";

    $("#formulario-produto-card").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

function fecharFormularioProduto() {
    $("#formulario-produto-card").hidden = true;
    $("#form-produto").reset();
    $("#produto-id").value = "";
}

$("#btn-novo-produto").addEventListener("click", async () => {
    const carregou = await carregarCategorias();

    if (!carregou) return;

    abrirFormularioProduto();
});

$("#btn-cancelar-produto").addEventListener("click", fecharFormularioProduto);

$("#form-produto").addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const id = $("#produto-id").value;
    const campoPromocional = $("#produto-preco-promocional");

    const valorPromocional = campoPromocional
        ? campoPromocional.value.trim()
        : "";

    const precoNormal = Number($("#produto-preco").value);

    const precoPromocional = valorPromocional === ""
        ? null
        : Number(valorPromocional);

    if (
        precoPromocional !== null &&
        (
            !Number.isFinite(precoPromocional) ||
            precoPromocional <= 0 ||
            precoPromocional >= precoNormal
        )
    ) {
        mostrarMensagem(
            "O preço promocional deve ser maior que zero e menor que o preço normal.",
            true
        );
        return;
    }

    const produto = {
        name: $("#produto-nome").value.trim(),
        description: $("#produto-descricao").value.trim(),
        category_id: Number($("#produto-categoria").value),
        price: precoNormal,
        promo_price: precoPromocional,
        image_url: $("#produto-imagem").value.trim(),
        prep_minutes: $("#produto-preparo").value === ""
            ? null
            : Number($("#produto-preparo").value),
        available: $("#produto-disponivel").checked,
        featured: $("#produto-destaque").checked
    };

    if (!produto.category_id) {
        mostrarMensagem("Selecione uma categoria para o produto.", true);
        return;
    }

    const botaoSalvar = evento.submitter;

    if (botaoSalvar) {
        botaoSalvar.disabled = true;
    }

    try {
        if (id) {
            await requisicao(`/produtos/${id}`, {
                method: "PATCH",
                body: JSON.stringify(produto)
            });

            mostrarMensagem("Produto atualizado com sucesso.");
        } else {
            await requisicao("/produtos", {
                method: "POST",
                body: JSON.stringify(produto)
            });

            mostrarMensagem("Produto cadastrado com sucesso.");
        }

        fecharFormularioProduto();
        await carregarProdutos();
    } catch (erro) {
        mostrarMensagem(erro.message, true);
    } finally {
        if (botaoSalvar) {
            botaoSalvar.disabled = false;
        }
    }
});

async function duplicarProduto(id) {
    if (!confirm("Deseja criar uma cópia deste produto?")) return;

    try {
        await requisicao(`/produtos/${id}/duplicar`, {
            method: "POST",
            body: "{}"
        });

        mostrarMensagem("Produto duplicado com sucesso.");
        await carregarProdutos();
    } catch (erro) {
        mostrarMensagem(erro.message, true);
    }
}

async function alterarAtivoProduto(produto) {
    const novoEstado = !produto.active;
    const acao = novoEstado ? "ativar" : "desativar";

    if (!confirm(`Deseja ${acao} o produto "${produto.name}"?`)) return;

    try {
        await requisicao(`/produtos/${produto.id}/ativo`, {
            method: "PATCH",
            body: JSON.stringify({ active: novoEstado })
        });

        mostrarMensagem(
            `Produto ${novoEstado ? "ativado" : "desativado"} com sucesso.`
        );

        await carregarProdutos();
    } catch (erro) {
        mostrarMensagem(erro.message, true);
    }
}

/* =========================
   CUPONS
========================= */

async function carregarCupons() {
    const lista = $("#lista-cupons");

    if (!lista) {
        mostrarMensagem("A tabela de cupons não foi encontrada.", true);
        return;
    }

    lista.replaceChildren();

    const linha = elemento("tr");
    const celula = elemento("td", "", "Carregando cupons...");
    celula.colSpan = 7;
    linha.append(celula);
    lista.append(linha);

    mostrarMensagem("");

    try {
        const dados = await requisicao("/cupons");

        cupons = Array.isArray(dados)
            ? dados
            : (dados.data || dados.cupons || []);

        renderizarCupons();
    } catch (erro) {
        lista.replaceChildren();

        const linhaErro = elemento("tr");
        const celulaErro = elemento("td", "", erro.message);
        celulaErro.colSpan = 7;
        linhaErro.append(celulaErro);
        lista.append(linhaErro);

        mostrarMensagem("Não foi possível carregar os cupons.", true);
    }
}

function formatarValorCupom(cupom) {
    const valor = Number(cupom.valor || 0);

    if (cupom.tipo === "percentual") {
        return `${valor}%`;
    }

    return dinheiro(valor);
}

function formatarDataCupom(data) {
    if (!data) return null;

    const dataValida = new Date(data);

    if (Number.isNaN(dataValida.getTime())) {
        return "Data inválida";
    }

    return dataValida.toLocaleString("pt-BR");
}

function renderizarCupons() {
    const lista = $("#lista-cupons");
    if (!lista) return;

    lista.replaceChildren();

    if (!cupons.length) {
        const linha = elemento("tr");
        const celula = elemento("td", "", "Nenhum cupom cadastrado.");
        celula.colSpan = 7;
        linha.append(celula);
        lista.append(linha);
        return;
    }

    for (const cupom of cupons) {
        const linha = elemento("tr");

        const utilizacoes = Number(cupom.utilizacoes || 0);
        const limite = cupom.limite_total;

        const usoTexto = limite !== null && limite !== undefined && limite !== ""
            ? `${utilizacoes} / ${limite}`
            : String(utilizacoes);

        const inicio = formatarDataCupom(cupom.inicio_em);
        const fim = formatarDataCupom(cupom.fim_em);

        const validade = `${inicio || "Sem início definido"} até ${fim || "Sem vencimento"}`;

        linha.append(
            elemento("td", "", cupom.codigo || "—"),
            elemento("td", "", formatarValorCupom(cupom)),
            elemento("td", "", dinheiro(cupom.pedido_minimo)),
            elemento("td", "", usoTexto),
            elemento("td", "", validade),
            elemento("td", "", cupom.ativo ? "Ativo" : "Inativo")
        );

        const acoes = elemento("td");

        const botaoEditar = elemento("button", "btn btn-light", "Editar");
        botaoEditar.type = "button";
        botaoEditar.addEventListener("click", () => {
            editarCupom(cupom.id);
        });

        const botaoStatus = elemento(
            "button",
            "btn btn-light",
            cupom.ativo ? "Desativar" : "Ativar"
        );

        botaoStatus.type = "button";
        botaoStatus.addEventListener("click", () => {
            alternarStatusCupom(cupom);
        });

        acoes.append(botaoEditar, botaoStatus);
        linha.append(acoes);
        lista.append(linha);
    }
}

function abrirFormularioCupom() {
    const formulario = $("#form-cupom");
    const card = $("#formulario-cupom-card");

    if (!formulario || !card) return;

    formulario.reset();

    $("#cupom-id").value = "";
    $("#cupom-ativo").checked = true;

    card.hidden = false;

    atualizarLimiteValorCupom();

    card.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

function editarCupom(id) {
    const cupom = cupons.find(
        (item) => String(item.id) === String(id)
    );

    if (!cupom) return;

    $("#cupom-id").value = cupom.id;
    $("#cupom-codigo").value = cupom.codigo || "";
    $("#cupom-tipo").value = cupom.tipo;
    $("#cupom-valor").value = cupom.valor;
    $("#cupom-pedido-minimo").value = cupom.pedido_minimo ?? 0;

    $("#cupom-inicio").value = cupom.inicio_em
        ? String(cupom.inicio_em).replace(" ", "T").slice(0, 16)
        : "";

    $("#cupom-fim").value = cupom.fim_em
        ? String(cupom.fim_em).replace(" ", "T").slice(0, 16)
        : "";

    $("#cupom-limite-total").value = cupom.limite_total ?? "";
    $("#cupom-limite-cliente").value =
        cupom.limite_por_cliente ?? "";

    $("#cupom-ativo").checked = Boolean(cupom.ativo);
    $("#formulario-cupom-card").hidden = false;

    atualizarLimiteValorCupom();

    $("#formulario-cupom-card").scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

function atualizarLimiteValorCupom() {
    const tipo = $("#cupom-tipo");
    const valor = $("#cupom-valor");

    if (!tipo || !valor) return;

    if (tipo.value === "percentual") {
        valor.max = "100";
    } else {
        valor.removeAttribute("max");
    }
}

async function salvarCupom(evento) {
    evento.preventDefault();

    const id = $("#cupom-id").value;

    const dados = {
        codigo: $("#cupom-codigo").value.trim().toUpperCase(),
        tipo: $("#cupom-tipo").value,
        valor: Number($("#cupom-valor").value),
        pedido_minimo: Number($("#cupom-pedido-minimo").value || 0),
        inicio_em: $("#cupom-inicio").value || null,
        fim_em: $("#cupom-fim").value || null,
        limite_total: $("#cupom-limite-total").value || null,
        limite_por_cliente: $("#cupom-limite-cliente").value || null,
        ativo: $("#cupom-ativo").checked
    };

    if (
        dados.tipo === "percentual" &&
        (dados.valor <= 0 || dados.valor > 100)
    ) {
        mostrarMensagem(
            "O desconto percentual deve estar entre 0 e 100.",
            true
        );
        return;
    }

    if (dados.tipo === "valor_fixo" && dados.valor <= 0) {
        mostrarMensagem("O valor do desconto deve ser maior que zero.", true);
        return;
    }

    if (dados.pedido_minimo < 0) {
        mostrarMensagem("O pedido mínimo não pode ser negativo.", true);
        return;
    }

    if (
        dados.inicio_em &&
        dados.fim_em &&
        new Date(dados.fim_em) < new Date(dados.inicio_em)
    ) {
        mostrarMensagem(
            "A data de término não pode ser anterior à data de início.",
            true
        );
        return;
    }

    if (
        dados.limite_total !== null &&
        Number(dados.limite_total) < 1
    ) {
        mostrarMensagem("O limite total deve ser maior que zero.", true);
        return;
    }

    if (
        dados.limite_por_cliente !== null &&
        Number(dados.limite_por_cliente) < 1
    ) {
        mostrarMensagem(
            "O limite por cliente deve ser maior que zero.",
            true
        );
        return;
    }

    const botaoSalvar = evento.submitter;

    if (botaoSalvar) {
        botaoSalvar.disabled = true;
    }

    try {
        await requisicao(
            id ? `/cupons/${id}` : "/cupons",
            {
                method: id ? "PATCH" : "POST",
                body: JSON.stringify(dados)
            }
        );

        mostrarMensagem(
            id
                ? "Cupom atualizado com sucesso."
                : "Cupom cadastrado com sucesso."
        );

        $("#formulario-cupom-card").hidden = true;

        await carregarCupons();
    } catch (erro) {
        mostrarMensagem(erro.message, true);
    } finally {
        if (botaoSalvar) {
            botaoSalvar.disabled = false;
        }
    }
}

async function alternarStatusCupom(cupom) {
    const acao = cupom.ativo ? "desativar" : "ativar";

    if (!confirm(`Deseja ${acao} o cupom "${cupom.codigo}"?`)) {
        return;
    }

    try {
        await requisicao(`/cupons/${cupom.id}/ativo`, {
            method: "PATCH",
            body: JSON.stringify({
                ativo: !cupom.ativo
            })
        });

        mostrarMensagem(
            `Cupom ${cupom.ativo ? "desativado" : "ativado"} com sucesso.`
        );

        await carregarCupons();
    } catch (erro) {
        mostrarMensagem(erro.message, true);
    }
}

/* Eventos da tela de cupons */

$("#form-cupom")?.addEventListener("submit", salvarCupom);

$("#btn-novo-cupom")?.addEventListener(
    "click",
    abrirFormularioCupom
);

$("#btn-cancelar-cupom")?.addEventListener("click", () => {
    $("#formulario-cupom-card").hidden = true;
});

$("#btn-atualizar-cupons")?.addEventListener(
    "click",
    carregarCupons
);

$("#cupom-tipo")?.addEventListener(
    "change",
    atualizarLimiteValorCupom
);

/* =========================
   CONFIGURAÇÕES DA LOJA
========================= */

async function carregarConfiguracoes() {
    const campo = $("#taxa-entrega");
    const mensagem = $("#mensagem-taxa-entrega");

    if (!campo || !mensagem) return;

    mensagem.textContent = "Carregando configurações...";

    try {
        const dados = await requisicao("/configuracoes");

        if (dados.taxa_entrega_padrao === undefined) {
            throw new Error("O servidor não retornou a taxa de entrega.");
        }

        campo.value = dados.taxa_entrega_padrao;
        mensagem.textContent = "";
    } catch (erro) {
        mensagem.textContent =
            "Não foi possível carregar a taxa: " + erro.message;
    }
}

$("#form-taxa-entrega")?.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const campo = $("#taxa-entrega");
    const mensagem = $("#mensagem-taxa-entrega");
    const botao = $("#btn-salvar-taxa-entrega");

    const valor = Number(campo.value);

    if (
        campo.value.trim() === "" ||
        !Number.isFinite(valor) ||
        valor < 0 ||
        valor > 99999999.99
    ) {
        mensagem.textContent = "Informe um valor válido para a entrega.";
        return;
    }

    botao.disabled = true;
    mensagem.textContent = "Salvando taxa...";

    try {
        await requisicao("/configuracoes/taxa-entrega", {
            method: "PATCH",
            body: JSON.stringify({
                taxa_entrega_padrao: valor
            })
        });

        mensagem.textContent = "Taxa de entrega salva com sucesso!";
        mostrarMensagem("Configuração da entrega atualizada.");
    } catch (erro) {
        mensagem.textContent = "Erro ao salvar: " + erro.message;
    } finally {
        botao.disabled = false;
    }
});

/* =========================
   BOTÕES GERAIS
========================= */

botaoSair.addEventListener("click", async () => {
    try {
        await requisicao("/logout", {
            method: "POST",
            body: "{}"
        });
    } catch (erro) {
        console.error("Erro ao sair:", erro);
    }

    mostrarLogin();
});

$("#btn-atualizar").addEventListener("click", carregarPedidos);
$("#btn-atualizar-produtos").addEventListener("click", carregarProdutos);
$("#btn-atualizar-categorias").addEventListener("click", carregarCategorias);

$("#btn-fechar").addEventListener("click", () => {
    dialogDetalhes.close();
});

$("#btn-imprimir").addEventListener("click", () => {
    window.print();
});

/* =========================
   INICIALIZAÇÃO
========================= */

verificarSessao();
