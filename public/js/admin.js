

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
let pagamentosFaturamento = [];
let clientes = [];
let regioesEntrega = [];
 
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
        if (
            resposta.status === 401 &&
            !["/login", "/sessao"].includes(caminho)
        ) {
            mostrarLogin();
        }
 
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

    const botaoMenu = $("#btn-menu");
    if (botaoMenu) botaoMenu.hidden = false;

    fecharMenuAdmin();
}

function mostrarLogin() {
    telaLogin.hidden = false;
    telaPainel.hidden = true;
    botaoSair.hidden = true;

    const botaoMenu = $("#btn-menu");
    if (botaoMenu) botaoMenu.hidden = true;

    fecharMenuAdmin();
}

function mostrarMensagem(texto, erro = false) {
    mensagemPainel.textContent = texto;
    mensagemPainel.classList.toggle("erro", erro);
}

function abrirMenuAdmin() {
    const menu = $(".admin-nav");
    const botaoMenu = $("#btn-menu");
    const fundo = $("#fundo-menu-admin");

    if (!menu || !botaoMenu || !fundo) return;

    menu.classList.add("menu-aberto");
    fundo.hidden = false;
    botaoMenu.setAttribute("aria-expanded", "true");
    botaoMenu.setAttribute("aria-label", "Fechar menu de navegação");
}

function fecharMenuAdmin() {
    const menu = $(".admin-nav");
    const botaoMenu = $("#btn-menu");
    const fundo = $("#fundo-menu-admin");

    if (menu) menu.classList.remove("menu-aberto");
    if (fundo) fundo.hidden = true;

    if (botaoMenu) {
        botaoMenu.setAttribute("aria-expanded", "false");
        botaoMenu.setAttribute("aria-label", "Abrir menu de navegação");
    }
}

$("#btn-menu")?.addEventListener("click", () => {
    const menu = $(".admin-nav");

    if (menu?.classList.contains("menu-aberto")) {
        fecharMenuAdmin();
    } else {
        abrirMenuAdmin();
    }
});

$("#fundo-menu-admin")?.addEventListener("click", fecharMenuAdmin);

document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") {
        fecharMenuAdmin();
    }
});

 

/* =========================
   NAVEGAÇÃO ENTRE ABAS
========================= */
 
function alternarAba(nome) {
    const secoes = {
        pedidos: $("#secao-pedidos"),
        produtos: $("#secao-produtos"),
        categorias: $("#secao-categorias"),
        cupons: $("#secao-cupons"),
        clientes: $("#secao-clientes"),
        configuracoes: $("#secao-configuracoes"),
        faturamento: $("#secao-faturamento")
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
    if (nome === "clientes") carregarClientes();
    if (nome === "configuracoes") carregarConfiguracoes();
    if (nome === "faturamento") carregarFaturamento();

    fecharMenuAdmin();
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
        alternarAba("pedidos");
    } catch (erro) {
        erroLogin.textContent = erro.message;
    }
});
 
async function verificarSessao() {
    try {
        const dados = await requisicao("/sessao");
 
        if (dados.autenticado) {
            mostrarPainel();
            alternarAba("pedidos");
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
 
function pedidosFiltrados() {
    const busca = ($("#filtro-busca-pedido")?.value || "")
        .trim()
        .toLowerCase();
 
    const status = $("#filtro-status-pedido")?.value || "";
 
    return pedidos.filter((pedido) => {
        if (
            status &&
            String(pedido.status || "").toLowerCase() !== status
        ) {
            return false;
        }
 
        if (!busca) return true;
 
        const texto = [
            pedido.numero,
            pedido.id,
            pedido.nome_cliente,
            pedido.telefone_cliente
        ].join(" ").toLowerCase();
 
        return texto.includes(busca);
    });
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
 
    const visiveis = pedidosFiltrados();
 
    if (!visiveis.length) {
        const linha = elemento("tr");
        const celula = elemento("td", "", "Nenhum pedido encontrado.");
        celula.colSpan = 6;
        linha.append(celula);
        listaPedidos.append(linha);
        return;
    }
 
    for (const pedido of visiveis) {
        const linha = elemento("tr");
        const numero = pedido.numero || pedido.id || "—";
 
        const data = pedido.criado_em
            ? formatarDataHora(pedido.criado_em)
            : "—";
 
        linha.append(
            elemento("td", "", `#${numero}`),
            elemento("td", "", pedido.nome_cliente || "Cliente"),
            elemento("td", "", data),
            elemento("td", "", dinheiro(pedido.total))
        );
 

        const celulaStatus = elemento("td");
        const seletor = document.createElement("select");
        const statusOriginal = String(pedido.status || "").toLowerCase();

        for (const [valor, nome] of Object.entries(STATUS)) {
            const opcao = document.createElement("option");
            opcao.value = valor;
            opcao.textContent = nome;
            opcao.selected = statusOriginal === valor;
            seletor.append(opcao);
        }

        const botaoSalvar = elemento("button", "btn btn-primary", "Salvar");
        botaoSalvar.type = "button";
        botaoSalvar.disabled = true;
        botaoSalvar.style.marginTop = "6px";

        seletor.addEventListener("change", () => {
            botaoSalvar.disabled = seletor.value === statusOriginal;
        });

        botaoSalvar.addEventListener("click", async () => {
            if (seletor.value === statusOriginal) return;

            const novoStatus = seletor.value;
            botaoSalvar.disabled = true;
            seletor.disabled = true;
            botaoSalvar.textContent = "Salvando...";

            try {
                await requisicao(`/pedidos/${pedido.id}/status`, {
                    method: "PATCH",
                    body: JSON.stringify({ status: novoStatus })
                });

                mostrarMensagem("Status atualizado com sucesso.");
                await carregarPedidos();
            } catch (erro) {
                mostrarMensagem(erro.message, true);
                botaoSalvar.textContent = "Tentar novamente";
                botaoSalvar.disabled = false;
                seletor.disabled = false;
            }
        });

        celulaStatus.append(seletor, document.createElement("br"), botaoSalvar);

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
    conteudo.classList.add("comprovante");
    conteudo.replaceChildren(elemento("p", "", "Carregando detalhes..."));

    if (!dialogDetalhes.open) dialogDetalhes.showModal();

    try {
        const dados = await requisicao(`/pedidos/${id}`);
        const pedido = dados.pedido || dados;

        conteudo.replaceChildren();

        const cabecalho = elemento("header", "comprovante-cabecalho");
        cabecalho.append(
            elemento("h2", "comprovante-marca", "SALTY"),
            elemento("p", "comprovante-subtitulo", "COMPROVANTE DO PEDIDO"),
            elemento(
                "p",
                "comprovante-numero",
                `Pedido nº ${pedido.numero || pedido.id || id}`
            )
        );

        if (pedido.criado_em) {
            cabecalho.append(
                elemento("p", "comprovante-data", formatarDataHora(pedido.criado_em))
            );
        }

        conteudo.append(cabecalho);

        const cliente = secaoDetalhe("Dados do cliente");
        cliente.classList.add("comprovante-secao");

        cliente.append(
            linhaDetalhe("Nome", pedido.nome_cliente),
            linhaDetalhe("Telefone", pedido.telefone_cliente),
            linhaDetalhe(
                "Modalidade",
                pedido.modalidade === "entrega" ? "Entrega" :
                pedido.modalidade === "retirada" ? "Retirada" :
                pedido.modalidade
            ),
            linhaDetalhe(
                "Status",
                STATUS[String(pedido.status || "").toLowerCase()] || pedido.status
            )
        );

        if (pedido.modalidade === "entrega") {
            const endereco = [
                pedido.entrega_rua,
                pedido.entrega_numero
            ].filter(Boolean).join(", ");

            const complemento = pedido.entrega_complemento;
            const bairro = pedido.entrega_bairro;
            const cidadeUF = [pedido.entrega_cidade, pedido.entrega_uf]
                .filter(Boolean)
                .join(" - ");

            const cep = pedido.entrega_cep;
            const referencia = pedido.entrega_referencia;

            if (endereco) {
                cliente.append(linhaDetalhe("Endereço", endereco));
            }

            if (complemento) {
                cliente.append(linhaDetalhe("Complemento", complemento));
            }

            if (bairro) {
                cliente.append(linhaDetalhe("Bairro", bairro));
            }

            if (cidadeUF) {
                cliente.append(linhaDetalhe("Cidade/UF", cidadeUF));
            }

            if (cep) {
                cliente.append(linhaDetalhe("CEP", cep));
            }

            if (referencia) {
                cliente.append(linhaDetalhe("Referência", referencia));
            }
        }

        if (pedido.observacoes) {
            cliente.append(
                elemento("p", "comprovante-observacoes",
                    `Observações do pedido: ${pedido.observacoes}`)
            );
        }

        conteudo.append(cliente);

        const itens = secaoDetalhe("Produtos");
        itens.classList.add("comprovante-secao");

        if (pedido.itens?.length) {
            for (const item of pedido.itens) {
                adicionarItemPedido(item, itens);
            }
        } else {
            itens.append(elemento("p", "", "Nenhum item retornado."));
        }

        conteudo.append(itens);

        const totais = secaoDetalhe("Resumo dos valores");
        totais.classList.add("comprovante-secao", "comprovante-totais");

        totais.append(
            linhaDetalhe("Subtotal", dinheiro(pedido.subtotal)),
            linhaDetalhe("Entrega", dinheiro(pedido.taxa_entrega)),
            linhaDetalhe("Desconto", dinheiro(pedido.desconto)),
            linhaDetalhe("TOTAL", dinheiro(pedido.total))
        );

        conteudo.append(totais);

        if (pedido.pagamentos?.length) {
            const pagamentos = secaoDetalhe("Pagamento");
            pagamentos.classList.add("comprovante-secao");

            for (const pagamento of pedido.pagamentos) {
                const blocoPagamento = elemento("div", "item-pedido");

                blocoPagamento.append(
                    linhaDetalhe("Forma", formatarFormaPagamento(pagamento.forma)),
                    linhaDetalhe("Valor", dinheiro(pagamento.valor)),
                    linhaDetalhe("Status", pagamento.status)
                );

                if (
                    pagamento.troco_para !== null &&
                    pagamento.troco_para !== undefined &&
                    pagamento.troco_para !== ""
                ) {
                    blocoPagamento.append(
                        linhaDetalhe("Troco para", dinheiro(pagamento.troco_para))
                    );
                }

                pagamentos.append(blocoPagamento);
            }

            conteudo.append(pagamentos);
        }

        conteudo.append(
            elemento("p", "comprovante-rodape", "Obrigado pela preferência!")
        );
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
        celula.colSpan = 5;
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
 
        preencherSelectCategorias();
 
        if (lista) {
            lista.replaceChildren();
 
            const linhaErro = elemento("tr");
            const celulaErro = elemento("td", "", erro.message);
            celulaErro.colSpan = 5;
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
 
/* Compatibilidade com o botão adicional do HTML atualizado */
$("#btn-adicionar-categoria")?.addEventListener(
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
    if (!lista) return;
 
    lista.replaceChildren();
 
    if (!categorias.length) {
        const linha = elemento("tr");
        const celula = elemento("td", "", "Nenhuma categoria encontrada.");
        celula.colSpan = 5;
        linha.append(celula);
        lista.append(linha);
        return;
    }
 
    categorias.forEach((categoria, indice) => {
        const linha = elemento("tr");
 
        linha.append(
            elemento("td", "", categoria.name || "—"),
            elemento("td", "", categoria.description || "—"),
            elemento("td", "", String(categoria.order ?? "—")),
            elemento("td", "", categoria.active ? "Sim" : "Não")
        );
 
        const acoes = elemento("td");
 
        const subir = elemento("button", "btn btn-light", "↑ Subir");
        subir.type = "button";
        subir.disabled = indice === 0;
        subir.addEventListener("click", () => moverCategoria(indice, -1));
 
        const descer = elemento("button", "btn btn-light", "↓ Descer");
        descer.type = "button";
        descer.disabled = indice === categorias.length - 1;
        descer.addEventListener("click", () => moverCategoria(indice, 1));
 
        const excluir = elemento("button", "btn btn-light btn-perigo", "Excluir");
        excluir.type = "button";
        excluir.addEventListener("click", () => excluirCategoria(categoria));
 
        acoes.append(subir, descer, excluir);
        linha.append(acoes);
        lista.append(linha);
    });
}
 
async function moverCategoria(indice, deslocamento) {
    const destino = indice + deslocamento;
 
    if (destino < 0 || destino >= categorias.length) return;
 
    const ids = categorias.map((categoria) => categoria.id);
    [ids[indice], ids[destino]] = [ids[destino], ids[indice]];
 
    try {
        await requisicao("/categorias/ordem", {
            method: "PUT",
            body: JSON.stringify({ ids })
        });
 
        await carregarCategorias();
        mostrarMensagem("Ordem das categorias salva.");
    } catch (erro) {
        await carregarCategorias();
        mostrarMensagem(erro.message, true);
    }
}
 
async function excluirCategoria(categoria) {
    if (
        !confirm(
            `Excluir a categoria "${categoria.name}"?\n\n` +
            "Categorias com produtos não podem ser excluídas. " +
            "Mova os produtos para outra categoria antes."
        )
    ) {
        return;
    }
 
    try {
        await requisicao(`/categorias/${categoria.id}`, { method: "DELETE" });
 
        await carregarCategorias();
        mostrarMensagem("Categoria excluída com sucesso.");
    } catch (erro) {
        mostrarMensagem(erro.message, true);
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
    if (!lista) return;
 
    lista.replaceChildren();
 
    const linha = elemento("tr");
    const celula = elemento("td", "", "Carregando produtos...");
    celula.colSpan = 7;
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
        celulaErro.colSpan = 7;
        linhaErro.append(celulaErro);
        lista.append(linhaErro);
 
        mostrarMensagem("Não foi possível carregar os produtos.", true);
    }
}
 
function renderizarProdutos() {
    const lista = $("#lista-produtos");
    if (!lista) return;
 
    lista.replaceChildren();
 
    if (!produtos.length) {
        const linha = elemento("tr");
        const celula = elemento("td", "", "Nenhum produto encontrado.");
        celula.colSpan = 7;
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
 
        const celulaDestaque = elemento("td");
 
        if (produto.featured) {
            celulaDestaque.append(elemento("span", "badge-destaque", "Em destaque"));
        } else {
            celulaDestaque.textContent = "—";
        }
 
        linha.append(
            elemento("td", "", produto.name || "—"),
            elemento("td", "", produto.category_name || "—"),
            elemento("td", "", precoExibido),
            elemento("td", "", produto.available ? "Disponível" : "Indisponível"),
            celulaDestaque,
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
 
        const destaque = elemento(
            "button",
            "btn btn-light",
            produto.featured ? "Remover destaque" : "Destacar"
        );
 
        destaque.type = "button";
        destaque.addEventListener("click", () => alterarDestaqueProduto(produto));
 
        const excluir = elemento("button", "btn btn-light btn-perigo", "Excluir");
        excluir.type = "button";
        excluir.addEventListener("click", () => excluirProduto(produto));
 
        acoes.append(editar, duplicar, destaque, ativo, excluir);
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
 
$("#btn-novo-produto")?.addEventListener("click", async () => {
    const carregou = await carregarCategorias();
 
    if (!carregou) return;
 
    abrirFormularioProduto();
});
 
$("#btn-cancelar-produto")?.addEventListener("click", fecharFormularioProduto);
 
$("#form-produto")?.addEventListener("submit", async (evento) => {
    evento.preventDefault();
 
    const id = $("#produto-id").value;
    const campoPromocional = $("#produto-preco-promocional");
 
    const valorPromocional = campoPromocional
        ? campoPromocional.value.trim()
        : "";
 
    const precoNormal = Number($("#produto-preco").value);
 
    if (!Number.isFinite(precoNormal) || precoNormal <= 0) {
        mostrarMensagem("Informe um preço válido para o produto.", true);
        return;
    }
 
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
 
async function alterarDestaqueProduto(produto) {
    const novoEstado = !produto.featured;
 
    try {
        await requisicao(`/produtos/${produto.id}/destaque`, {
            method: "PATCH",
            body: JSON.stringify({ featured: novoEstado })
        });
 
        await carregarProdutos();
 
        mostrarMensagem(
            novoEstado
                ? `"${produto.name}" agora está em destaque.`
                : `"${produto.name}" saiu do destaque.`
        );
    } catch (erro) {
        mostrarMensagem(erro.message, true);
    }
}
 
async function excluirProduto(produto) {
    if (
        !confirm(
            `Excluir o produto "${produto.name}"?\n\n` +
            "Essa ação não pode ser desfeita. Produtos que já foram vendidos " +
            "não podem ser excluídos (use Desativar)."
        )
    ) {
        return;
    }
 
    try {
        await requisicao(`/produtos/${produto.id}`, { method: "DELETE" });
 
        await carregarProdutos();
        mostrarMensagem("Produto excluído com sucesso.");
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
 
    const dataValida = new Date(String(data).replace(" ", "T"));
 
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
 
    const limiteTotalTexto = $("#cupom-limite-total").value.trim();
    const limiteClienteTexto = $("#cupom-limite-cliente").value.trim();
 
    const dados = {
        codigo: $("#cupom-codigo").value.trim().toUpperCase(),
        tipo: $("#cupom-tipo").value,
        valor: Number($("#cupom-valor").value),
        pedido_minimo: Number($("#cupom-pedido-minimo").value || 0),
        inicio_em: $("#cupom-inicio").value || null,
        fim_em: $("#cupom-fim").value || null,
        limite_total: limiteTotalTexto === "" ? null : Number(limiteTotalTexto),
        limite_por_cliente: limiteClienteTexto === "" ? null : Number(limiteClienteTexto),
        ativo: $("#cupom-ativo").checked
    };
 
    if (!dados.codigo) {
        mostrarMensagem("Informe o código do cupom.", true);
        return;
    }
 
    if (!Number.isFinite(dados.valor)) {
        mostrarMensagem("Informe um valor de desconto válido.", true);
        return;
    }
 
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
 
    if (!Number.isFinite(dados.pedido_minimo) || dados.pedido_minimo < 0) {
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
        (!Number.isFinite(dados.limite_total) || dados.limite_total < 1)
    ) {
        mostrarMensagem("O limite total deve ser maior que zero.", true);
        return;
    }
 
    if (
        dados.limite_por_cliente !== null &&
        (!Number.isFinite(dados.limite_por_cliente) || dados.limite_por_cliente < 1)
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
   CLIENTES
========================= */
 
function garantirInterfaceClientes() {
    const secao = $("#secao-clientes");
    if (!secao) return null;
 
    let painel = secao.querySelector("[data-clientes-painel]");
    if (painel) return painel;
 
    painel = elemento("div", "clientes-painel");
    painel.dataset.clientesPainel = "true";
 
    const cabecalho = elemento("div", "cabecalho-secao");
    cabecalho.append(
        elemento("h2", "", "Clientes"),
        elemento("p", "", "Veja os clientes que já fizeram pedidos na SALTY.")
    );
 
    const controles = elemento("div", "filtros-clientes");
    controles.style.display = "flex";
    controles.style.flexWrap = "wrap";
    controles.style.gap = "10px";
    controles.style.margin = "16px 0";
 
    const busca = document.createElement("input");
    busca.type = "search";
    busca.id = "filtro-busca-cliente";
    busca.placeholder = "Buscar por nome ou telefone";
    busca.setAttribute("aria-label", "Buscar clientes por nome ou telefone");
    busca.style.flex = "1";
    busca.style.minWidth = "220px";
 
    const atualizar = elemento("button", "btn btn-light", "Atualizar clientes");
    atualizar.id = "btn-atualizar-clientes";
    atualizar.type = "button";
    atualizar.addEventListener("click", carregarClientes);
 
    controles.append(busca, atualizar);
 
    const resumo = elemento("p", "resumo-clientes", "Carregando clientes...");
    resumo.id = "resumo-clientes";
 
    const tabela = elemento("div", "tabela-responsiva");
    const table = document.createElement("table");
    table.className = "tabela-admin";
 
    const thead = document.createElement("thead");
    const linhaCabecalho = document.createElement("tr");
 
    for (const titulo of [
        "Cliente",
        "Telefone",
        "Pedidos",
        "Pedidos válidos",
        "Total gasto",
        "Última compra"
    ]) {
        linhaCabecalho.append(elemento("th", "", titulo));
    }
 
    thead.append(linhaCabecalho);
 
    const tbody = document.createElement("tbody");
    tbody.id = "lista-clientes";
 
    table.append(thead, tbody);
    tabela.append(table);
 
    painel.append(cabecalho, controles, resumo, tabela);
    secao.replaceChildren(painel);
 
    busca.addEventListener("input", renderizarClientes);
 
    return painel;
}
 
async function carregarClientes() {
    const painel = garantirInterfaceClientes();
    const lista = $("#lista-clientes");
    const resumo = $("#resumo-clientes");
    const botao = $("#btn-atualizar-clientes");
 
    if (!painel || !lista) {
        mostrarMensagem("A seção de clientes não foi encontrada no HTML.", true);
        return;
    }
 
    lista.replaceChildren();
 
    const linhaCarregando = elemento("tr");
    const celulaCarregando = elemento("td", "", "Carregando clientes...");
    celulaCarregando.colSpan = 6;
    linhaCarregando.append(celulaCarregando);
    lista.append(linhaCarregando);
 
    if (resumo) resumo.textContent = "Buscando clientes...";
    if (botao) botao.disabled = true;
 
    mostrarMensagem("");
 
    try {
        const dados = await requisicao("/clientes");
 
        const listaRecebida = Array.isArray(dados)
            ? dados
            : (dados.clientes || dados.data || dados.items || []);
 
        clientes = Array.isArray(listaRecebida) ? listaRecebida : [];
 
        renderizarClientes();
    } catch (erro) {
        clientes = [];
        lista.replaceChildren();
 
        const linhaErro = elemento("tr");
        const celulaErro = elemento("td", "", erro.message);
        celulaErro.colSpan = 6;
        linhaErro.append(celulaErro);
        lista.append(linhaErro);
 
        if (resumo) {
            resumo.textContent = "Não foi possível carregar os clientes.";
        }
 
        mostrarMensagem(
            "Não foi possível carregar os clientes: " + erro.message,
            true
        );
    } finally {
        if (botao) botao.disabled = false;
    }
}
 
function renderizarClientes() {
    const lista = $("#lista-clientes");
    if (!lista) return;
 
    lista.replaceChildren();
 
    const busca = ($("#filtro-busca-cliente")?.value || "")
        .trim()
        .toLowerCase();
 
    const filtrados = clientes.filter((cliente) => {
        const texto = [
            cliente.nome,
            cliente.nome_cliente,
            cliente.telefone,
            cliente.telefone_cliente
        ].join(" ").toLowerCase();
 
        return texto.includes(busca);
    });
 
    const resumo = $("#resumo-clientes");
 
    if (resumo) {
        resumo.textContent =
            `${filtrados.length} cliente(s) encontrado(s) de ${clientes.length} cadastrado(s).`;
    }
 
    if (!filtrados.length) {
        const linha = elemento("tr");
 
        const celula = elemento(
            "td",
            "",
            clientes.length
                ? "Nenhum cliente corresponde à busca."
                : "Nenhum cliente encontrado."
        );
 
        celula.colSpan = 6;
        linha.append(celula);
        lista.append(linha);
        return;
    }
 
    for (const cliente of filtrados) {
        const linha = elemento("tr");
 
        const nome = cliente.nome || cliente.nome_cliente || "Cliente";
        const telefone = cliente.telefone || cliente.telefone_cliente || "—";
        const totalPedidos = Number(cliente.total_pedidos || 0);
        const pedidosValidos = Number(cliente.pedidos_validos || 0);
        const totalGasto = Number(cliente.total_gasto || 0);
 
        const ultimaCompra = cliente.ultima_compra
            ? formatarDataHora(cliente.ultima_compra)
            : "—";
 
        linha.append(
            elemento("td", "", nome),
            elemento("td", "", telefone),
            elemento("td", "", String(totalPedidos)),
            elemento("td", "", String(pedidosValidos)),
            elemento("td", "", dinheiro(totalGasto)),
            elemento("td", "", ultimaCompra)
        );
 
        lista.append(linha);
    }
}
 
/* =========================
   CONFIGURAÇÕES DA LOJA
========================= */
 
async function carregarConfiguracoes() {
    carregarFuncionamento();
    carregarRegioesEntrega();
 
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
   REGIÕES DE ENTREGA
========================= */

async function carregarRegioesEntrega() {
    const lista = $("#lista-regioes-entrega");
    const mensagem = $("#mensagem-regiao-entrega");

    if (!lista) return;

    lista.replaceChildren();

    const linha = elemento("tr");
    const celula = elemento("td", "", "Carregando regiões...");
    celula.colSpan = 5;
    linha.append(celula);
    lista.append(linha);

    try {
        const dados = await requisicao("/regioes-entrega");

        regioesEntrega = Array.isArray(dados)
            ? dados
            : (dados.data || dados.regioes || []);

        renderizarRegioesEntrega();

        if (mensagem) {
            mensagem.textContent = "";
            mensagem.classList.remove("erro");
        }
    } catch (erro) {
        lista.replaceChildren();

        const linhaErro = elemento("tr");
        const celulaErro = elemento("td", "", erro.message);
        celulaErro.colSpan = 5;
        linhaErro.append(celulaErro);
        lista.append(linhaErro);

        if (mensagem) {
            mensagem.textContent =
                "Não foi possível carregar as regiões: " + erro.message;
            mensagem.classList.add("erro");
        }
    }
}

function renderizarRegioesEntrega() {
    const lista = $("#lista-regioes-entrega");
    if (!lista) return;

    lista.replaceChildren();

    if (!regioesEntrega.length) {
        const linha = elemento("tr");
        const celula = elemento(
            "td",
            "",
            "Nenhuma região de entrega cadastrada."
        );

        celula.colSpan = 5;
        linha.append(celula);
        lista.append(linha);
        return;
    }

    for (const regiao of regioesEntrega) {
        const linha = elemento("tr");

        const ativa =
            regiao.ativo === true ||
            regiao.ativo === 1 ||
            regiao.ativo === "1";

        linha.append(
            elemento("td", "", regiao.cidade || "—"),
            elemento("td", "", regiao.bairro || "—"),
            elemento("td", "", dinheiro(regiao.taxa)),
            elemento(
                "td",
                "",
                regiao.prazo_estimado_min
                    ? `${regiao.prazo_estimado_min} min`
                    : "Não definido"
            ),
            elemento("td", "", ativa ? "Ativa" : "Inativa")
        );

        const acoes = elemento("td");

        const botaoEditar = elemento(
            "button",
            "btn btn-light",
            "Editar"
        );
        botaoEditar.type = "button";
        botaoEditar.addEventListener("click", () => {
            editarRegiaoEntrega(regiao);
        });

        const botaoStatus = elemento(
            "button",
            "btn btn-light",
            ativa ? "Desativar" : "Ativar"
        );
        botaoStatus.type = "button";
        botaoStatus.addEventListener("click", () => {
            alterarStatusRegiaoEntrega(regiao, ativa);
        });

        acoes.append(botaoEditar, botaoStatus);
        linha.append(acoes);
        lista.append(linha);
    }
}

function editarRegiaoEntrega(regiao) {
    const formulario = $("#form-regiao-entrega");
    if (!formulario) return;

    $("#regiao-entrega-id").value = regiao.id;
    $("#regiao-cidade").value = regiao.cidade || "";
    $("#regiao-bairro").value = regiao.bairro || "";
    $("#regiao-taxa").value = regiao.taxa ?? 0;
    $("#regiao-prazo").value = regiao.prazo_estimado_min ?? "";
    $("#regiao-ativo").checked =
        regiao.ativo === true ||
        regiao.ativo === 1 ||
        regiao.ativo === "1";

    const botao = $("#btn-salvar-regiao");
    if (botao) botao.textContent = "Salvar alterações";

    formulario.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    $("#regiao-cidade").focus();
}

function limparFormularioRegiaoEntrega() {
    const formulario = $("#form-regiao-entrega");
    if (formulario) formulario.reset();

    const id = $("#regiao-entrega-id");
    if (id) id.value = "";

    const ativo = $("#regiao-ativo");
    if (ativo) ativo.checked = true;

    const botao = $("#btn-salvar-regiao");
    if (botao) botao.textContent = "Cadastrar região";

    const mensagem = $("#mensagem-regiao-entrega");
    if (mensagem) {
        mensagem.textContent = "";
        mensagem.classList.remove("erro");
    }
}

$("#form-regiao-entrega")?.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const id = $("#regiao-entrega-id").value.trim();
    const cidade = $("#regiao-cidade").value.trim();
    const bairro = $("#regiao-bairro").value.trim();
    const taxaTexto = $("#regiao-taxa").value.trim();
    const prazoTexto = $("#regiao-prazo").value.trim();
    const mensagem = $("#mensagem-regiao-entrega");
    const botao = $("#btn-salvar-regiao");

    const taxa = Number(taxaTexto);
    const prazo = prazoTexto === "" ? null : Number(prazoTexto);

    if (!cidade || !bairro) {
        mensagem.textContent = "Informe a cidade e o bairro.";
        mensagem.classList.add("erro");
        return;
    }

    if (
        taxaTexto === "" ||
        !Number.isFinite(taxa) ||
        taxa < 0 ||
        taxa > 99999999.99
    ) {
        mensagem.textContent = "Informe uma taxa de entrega válida.";
        mensagem.classList.add("erro");
        return;
    }

    if (
        prazo !== null &&
        (!Number.isInteger(prazo) || prazo < 1 || prazo > 65535)
    ) {
        mensagem.textContent =
            "O prazo deve ser um número inteiro de minutos maior que zero.";
        mensagem.classList.add("erro");
        return;
    }

    const dados = {
        cidade,
        bairro,
        taxa,
        prazo_estimado_min: prazo,
        ativo: $("#regiao-ativo").checked
    };

    botao.disabled = true;
    mensagem.classList.remove("erro");
    mensagem.textContent = "Salvando região...";

    try {
        await requisicao(
            id ? `/regioes-entrega/${id}` : "/regioes-entrega",
            {
                method: id ? "PATCH" : "POST",
                body: JSON.stringify(dados)
            }
        );

        mensagem.textContent = id
            ? "Região atualizada com sucesso."
            : "Região cadastrada com sucesso.";

        limparFormularioRegiaoEntrega();
        await carregarRegioesEntrega();
    } catch (erro) {
        mensagem.textContent = erro.message;
        mensagem.classList.add("erro");
    } finally {
        botao.disabled = false;
    }
});

$("#btn-cancelar-regiao")?.addEventListener(
    "click",
    limparFormularioRegiaoEntrega
);

$("#btn-atualizar-regioes")?.addEventListener(
    "click",
    carregarRegioesEntrega
);

async function alterarStatusRegiaoEntrega(regiao, ativa) {
    const acao = ativa ? "desativar" : "ativar";

    if (
        !confirm(
            `Deseja ${acao} a entrega para ${regiao.bairro}, ${regiao.cidade}?`
        )
    ) {
        return;
    }

    const mensagem = $("#mensagem-regiao-entrega");

    try {
        await requisicao(`/regioes-entrega/${regiao.id}/ativo`, {
            method: "PATCH",
            body: JSON.stringify({ ativo: !ativa })
        });

        if (mensagem) {
            mensagem.textContent = `Região ${ativa ? "desativada" : "ativada"} com sucesso.`;
            mensagem.classList.remove("erro");
        }

        await carregarRegioesEntrega();
    } catch (erro) {
        if (mensagem) {
            mensagem.textContent = erro.message;
            mensagem.classList.add("erro");
        }
    }
}

 
/* =========================
   FUNCIONAMENTO DA LOJA
========================= */
 
const TEXTO_MODO_LOJA = {
    automatico: "Modo automático: a loja abre e fecha conforme os horários cadastrados.",
    aberta: "Aberta manualmente: recebe pedidos mesmo fora do horário.",
    fechada: "Fechada manualmente: novos pedidos bloqueados, mesmo no horário normal."
};
 
function mostrarMensagemFuncionamento(texto, erro = false) {
    const el = $("#mensagem-funcionamento");
 
    if (!el) return;
 
    el.textContent = texto || "";
    el.classList.toggle("erro", erro);
}
 
function renderizarStatusLoja(dados) {
    const badge = $("#loja-status-badge");
 
    if (!badge) return;
 
    badge.textContent = dados.aberta ? "Loja aberta" : "Loja fechada";
    badge.classList.toggle("loja-aberta", Boolean(dados.aberta));
    badge.classList.toggle("loja-fechada", !dados.aberta);
 
    const detalhe = $("#loja-status-detalhe");
 
    if (detalhe) {
        detalhe.textContent =
            (TEXTO_MODO_LOJA[dados.modo] || "") +
            (dados.modo === "automatico" ? ` ${dados.mensagem || ""}` : "");
    }
 
    const botoes = {
        aberta: "#btn-loja-abrir",
        fechada: "#btn-loja-fechar",
        automatico: "#btn-loja-automatico"
    };
 
    for (const [modo, seletor] of Object.entries(botoes)) {
        const botao = $(seletor);
 
        if (!botao) continue;
 
        botao.classList.toggle("btn-primary", dados.modo === modo);
        botao.classList.toggle("btn-light", dados.modo !== modo);
    }
}
 
function criarCampoHora(valor, rotulo) {
    const campo = document.createElement("input");
 
    campo.type = "time";
    campo.value = valor || "";
    campo.setAttribute("aria-label", rotulo);
 
    return campo;
}
 
function renderizarDiasFuncionamento(dias) {
    const container = $("#funcionamento-dias");
 
    if (!container) return;
 
    container.replaceChildren();
 
    for (const dia of dias) {
        const linha = elemento("div", "dia-funcionamento");
        linha.dataset.dia = String(dia.dia);
 
        const rotulo = elemento("label", "dia-nome");
        const marcador = document.createElement("input");
 
        marcador.type = "checkbox";
        marcador.className = "dia-aberto";
        marcador.checked = Boolean(dia.aberto);
 
        rotulo.append(marcador, document.createTextNode(dia.nome));
 
        const periodos = elemento("div", "periodos-dia");
        const campos = [];
 
        for (let i = 0; i < 2; i++) {
            const periodo = dia.periodos?.[i] || {};
            const bloco = elemento("div", "periodo");
 
            const abre = criarCampoHora(
                periodo.abre,
                `${dia.nome}: abertura do período ${i + 1}`
            );
 
            const fecha = criarCampoHora(
                periodo.fecha,
                `${dia.nome}: fechamento do período ${i + 1}`
            );
 
            bloco.append(
                elemento("span", "", i === 0 ? "Das" : "e das"),
                abre,
                elemento("span", "", "às"),
                fecha
            );
 
            periodos.append(bloco);
            campos.push(abre, fecha);
        }
 
        const atualizar = () => {
            campos.forEach((campo) => {
                campo.disabled = !marcador.checked;
            });
        };
 
        marcador.addEventListener("change", atualizar);
        atualizar();
 
        linha.append(rotulo, periodos);
        container.append(linha);
    }
}
 
function coletarDiasFuncionamento() {
    return [...document.querySelectorAll(".dia-funcionamento")].map((linha) => {
        const horas = [...linha.querySelectorAll("input[type=time]")]
            .map((campo) => campo.value);
 
        const periodos = [];
 
        if (horas[0] || horas[1]) {
            periodos.push({ abre: horas[0], fecha: horas[1] });
        }
 
        if (horas[2] || horas[3]) {
            periodos.push({ abre: horas[2], fecha: horas[3] });
        }
 
        return {
            dia: Number(linha.dataset.dia),
            aberto: linha.querySelector(".dia-aberto").checked,
            periodos
        };
    });
}
 
async function carregarFuncionamento() {
    if (!$("#funcionamento-dias")) return;
 
    try {
        const dados = await requisicao("/configuracoes/funcionamento");
 
        renderizarStatusLoja(dados);
        renderizarDiasFuncionamento(dados.dias || []);
        mostrarMensagemFuncionamento("");
    } catch (erro) {
        mostrarMensagemFuncionamento(
            "Não foi possível carregar o funcionamento: " + erro.message,
            true
        );
    }
}
 
async function salvarFuncionamento(evento) {
    evento.preventDefault();
 
    const botao = evento.submitter;
    if (botao) botao.disabled = true;
 
    mostrarMensagemFuncionamento("Salvando horários...");
 
    try {
        const dados = await requisicao("/configuracoes/funcionamento", {
            method: "PUT",
            body: JSON.stringify({ dias: coletarDiasFuncionamento() })
        });
 
        renderizarStatusLoja(dados);
        renderizarDiasFuncionamento(dados.dias || []);
        mostrarMensagemFuncionamento("Horários salvos com sucesso.");
    } catch (erro) {
        mostrarMensagemFuncionamento(erro.message, true);
    } finally {
        if (botao) botao.disabled = false;
    }
}
 
async function definirModoLoja(modo) {
    if (
        modo === "fechada" &&
        !confirm("Fechar a loja agora? Novos pedidos serão bloqueados.")
    ) {
        return;
    }
 
    try {
        const dados = await requisicao("/configuracoes/loja-modo", {
            method: "PATCH",
            body: JSON.stringify({ modo })
        });
 
        renderizarStatusLoja(dados);
        mostrarMensagemFuncionamento("Estado da loja atualizado.");
    } catch (erro) {
        mostrarMensagemFuncionamento(erro.message, true);
    }
}
 
$("#form-funcionamento")?.addEventListener("submit", salvarFuncionamento);
$("#btn-loja-abrir")?.addEventListener("click", () => definirModoLoja("aberta"));
$("#btn-loja-fechar")?.addEventListener("click", () => definirModoLoja("fechada"));
$("#btn-loja-automatico")?.addEventListener("click", () => definirModoLoja("automatico"));
 
/* =========================
   FATURAMENTO
========================= */
 
function formatarDataHora(data) {
    if (!data) return "—";
 
    const valor = String(data).replace(" ", "T");
    const dataValida = new Date(valor);
 
    if (Number.isNaN(dataValida.getTime())) {
        return String(data);
    }
 
    return dataValida.toLocaleString("pt-BR");
}
 
function mostrarCamposPeriodoPersonalizado() {
    const filtro = $("#filtro-periodo-faturamento");
    const campos = $("#campos-periodo-personalizado");
 
    if (!filtro || !campos) return;
 
    campos.hidden = filtro.value !== "personalizado";
}
 
function montarParametrosFaturamento() {
    const filtro = $("#filtro-periodo-faturamento");
    const dataInicial = $("#faturamento-data-inicial");
    const dataFinal = $("#faturamento-data-final");
 
    const parametros = new URLSearchParams();
    parametros.set("periodo", filtro?.value || "todo_periodo");
 
    if (filtro?.value === "personalizado") {
        if (!dataInicial?.value || !dataFinal?.value) {
            throw new Error(
                "Selecione a data inicial e a data final do período."
            );
        }
 
        if (dataInicial.value > dataFinal.value) {
            throw new Error(
                "A data inicial não pode ser posterior à data final."
            );
        }
 
        parametros.set("data_inicial", dataInicial.value);
        parametros.set("data_final", dataFinal.value);
    }
 
    return parametros.toString();
}
 
async function carregarFaturamento() {
    const lista = $("#lista-faturamento");
    const mensagem = $("#mensagem-filtro-faturamento");
 
    if (!lista) {
        mostrarMensagem(
            "A tabela de faturamento não foi encontrada no HTML.",
            true
        );
        return;
    }
 
    lista.replaceChildren();
 
    const linhaCarregando = elemento("tr");
    const celulaCarregando = elemento("td", "", "Carregando faturamento...");
    celulaCarregando.colSpan = 6;
    linhaCarregando.append(celulaCarregando);
    lista.append(linhaCarregando);
 
    if (mensagem) mensagem.textContent = "";
 
    try {
        const query = montarParametrosFaturamento();
        const dados = await requisicao(`/faturamento?${query}`);
 
        pagamentosFaturamento = Array.isArray(dados.pagamentos)
            ? dados.pagamentos
            : [];
 
        renderizarFaturamento(dados);
 
        if (mensagem) {
            mensagem.textContent = dados.periodo_descricao
                ? `Período: ${dados.periodo_descricao}`
                : "Faturamento atualizado.";
        }
    } catch (erro) {
        lista.replaceChildren();
 
        const linhaErro = elemento("tr");
        const celulaErro = elemento("td", "", erro.message);
        celulaErro.colSpan = 6;
        linhaErro.append(celulaErro);
        lista.append(linhaErro);
 
        if ($("#faturamento-total")) {
            $("#faturamento-total").textContent = dinheiro(0);
        }
 
        if ($("#faturamento-quantidade")) {
            $("#faturamento-quantidade").textContent = "0";
        }
 
        if ($("#faturamento-ticket-medio")) {
            $("#faturamento-ticket-medio").textContent = dinheiro(0);
        }
 
        if (mensagem) {
            mensagem.textContent =
                "Não foi possível carregar o faturamento: " + erro.message;
        }
    }
}
 

function renderizarFaturamento(dados) {
    const lista = $("#lista-faturamento");
    if (!lista) return;

    lista.replaceChildren();

    const filtroForma = $("#filtro-forma-faturamento");
    const formaSelecionada = filtroForma?.value || "todos";

    const pagamentosFiltrados = pagamentosFaturamento.filter((pagamento) => {
        if (formaSelecionada === "todos") return true;

        return String(pagamento.forma || "").toLowerCase() === formaSelecionada;
    });

    const total = pagamentosFiltrados.reduce(
        (soma, pagamento) => soma + Number(pagamento.valor || 0),
        0
    );

    const quantidade = pagamentosFiltrados.length;
    const ticketMedio = quantidade > 0 ? total / quantidade : 0;

    if ($("#faturamento-total")) {
        $("#faturamento-total").textContent = dinheiro(total);
    }

    if ($("#faturamento-quantidade")) {
        $("#faturamento-quantidade").textContent =
            quantidade.toLocaleString("pt-BR");
    }

    if ($("#faturamento-ticket-medio")) {
        $("#faturamento-ticket-medio").textContent = dinheiro(ticketMedio);
    }

    if (!pagamentosFiltrados.length) {
        const linha = elemento("tr");
        const celula = elemento(
            "td",
            "",
            "Nenhum pagamento encontrado para este filtro."
        );

        celula.colSpan = 6;
        linha.append(celula);
        lista.append(linha);
        return;
    }

    for (const pagamento of pagamentosFiltrados) {
        const linha = elemento("tr");

        const numeroPedido =
            pagamento.numero_pedido ??
            pagamento.numero ??
            pagamento.pedido_id ??
            "—";

        const dataPagamento = pagamento.pago_em
            ? formatarDataHora(pagamento.pago_em)
            : "—";

        const forma = formatarFormaPagamento(pagamento.forma);
        const valor = dinheiro(pagamento.valor);

        const status =
            String(pagamento.status || "").toLowerCase() === "pago"
                ? "Pago"
                : (pagamento.status || "—");

        linha.append(
            elemento("td", "", `#${numeroPedido}`),
            elemento("td", "", pagamento.nome_cliente || "Cliente"),
            elemento("td", "", forma),
            elemento("td", "", valor),
            elemento("td", "", dataPagamento),
            elemento("td", "", status)
        );

        lista.append(linha);
    }
}

 
function formatarFormaPagamento(forma) {
    const formas = {
        pix: "Pix",
        dinheiro: "Dinheiro",
        cartao_entrega: "Cartão na entrega",
        cartao: "Cartão",
        credito: "Cartão de crédito",
        debito: "Cartão de débito"
    };
 
    const valor = String(forma || "").toLowerCase();
 
    return formas[valor] || forma || "—";
}
 
$("#filtro-periodo-faturamento")?.addEventListener("change", () => {
    mostrarCamposPeriodoPersonalizado();
 
    if ($("#filtro-periodo-faturamento").value !== "personalizado") {
        carregarFaturamento();
    }
});

$("#filtro-forma-faturamento")?.addEventListener("change", () => {
    renderizarFaturamento();
});
 
$("#btn-aplicar-filtro-faturamento")?.addEventListener("click", () => {
    carregarFaturamento();
});
 
$("#btn-atualizar-faturamento")?.addEventListener("click", () => {
    carregarFaturamento();
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
 
$("#btn-atualizar")?.addEventListener("click", carregarPedidos);
 
$("#filtro-busca-pedido")?.addEventListener("input", renderizarPedidos);
$("#filtro-status-pedido")?.addEventListener("change", renderizarPedidos);
$("#btn-atualizar-produtos")?.addEventListener("click", carregarProdutos);
$("#btn-atualizar-categorias")?.addEventListener("click", carregarCategorias);
 
$("#btn-fechar")?.addEventListener("click", () => {
    dialogDetalhes.close();
});
 
$("#btn-imprimir")?.addEventListener("click", () => {
    window.print();
});
 
/* =========================
   INICIALIZAÇÃO
========================= */
 
mostrarCamposPeriodoPersonalizado();
verificarSessao();
 

