
/* SALTY — Painel administrativo */
"use strict";

/* =========================
   STATUS E VARIÁVEIS
========================= */

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

const $ = (seletor, raiz = document) => raiz.querySelector(seletor);
const $$ = (seletor, raiz = document) =>
  [...raiz.querySelectorAll(seletor)];

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
let clientes = [];
let faturamento = null;
let uploadImagemEmAndamento = false;

/* =========================
   FUNÇÕES AUXILIARES
========================= */

function dinheiro(valor) {
  const numero = Number(valor ?? 0);

  return (Number.isFinite(numero) ? numero : 0).toLocaleString(
    "pt-BR",
    {
      style: "currency",
      currency: "BRL"
    }
  );
}

function numeroBR(texto) {
  return Number(String(texto ?? "").trim().replace(",", "."));
}

function elemento(tag, classe = "", texto = "") {
  const el = document.createElement(tag);

  if (classe) el.className = classe;

  if (texto !== undefined && texto !== null) {
    el.textContent = texto;
  }

  return el;
}

function definirTexto(seletor, texto) {
  const el = $(seletor);
  if (el) el.textContent = texto ?? "";
}

function mostrarMensagem(texto, erro = false) {
  if (!mensagemPainel) return;

  mensagemPainel.textContent = texto || "";
  mensagemPainel.classList.toggle("erro", Boolean(erro));
}

function mostrarMensagemElemento(el, texto, erro = false) {
  if (!el) return;

  el.textContent = texto || "";
  el.classList.toggle("erro", Boolean(erro));
}

function arrayDaResposta(dados, chaves = []) {
  if (Array.isArray(dados)) return dados;

  for (const chave of chaves) {
    if (Array.isArray(dados?.[chave])) {
      return dados[chave];
    }
  }

  return [];
}

function boolValor(valor, padrao = false) {
  if (valor == null) return padrao;

  if (typeof valor === "string") {
    return ["1", "true", "sim", "ativo", "yes"].includes(
      valor.toLowerCase()
    );
  }

  return valor === true || valor === 1;
}

function mostrarErroTabela(seletor, mensagem, colSpan = 6) {
  const lista = $(seletor);
  if (!lista) return;

  lista.replaceChildren();

  const tr = elemento("tr");
  const td = elemento("td", "", mensagem);

  td.colSpan = colSpan;
  tr.append(td);
  lista.append(tr);
}

function dataHoraBR(valor) {
  if (!valor) return "—";

  const data = new Date(valor);

  return Number.isNaN(data.getTime())
    ? String(valor)
    : data.toLocaleString("pt-BR");
}

function formatarDataCupom(valor) {
  if (!valor) return "";

  const data = new Date(valor);

  return Number.isNaN(data.getTime())
    ? String(valor)
    : data.toLocaleString("pt-BR");
}

function valorParaInputDataHora(valor) {
  if (!valor) return "";

  const texto = String(valor);

  const semFuso =
    /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/.test(texto) &&
    !/(Z|[+-]\d{2}:?\d{2})$/.test(texto);

  if (semFuso) {
    return texto.replace(" ", "T").slice(0, 16);
  }

  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "";

  const p = n => String(n).padStart(2, "0");

  return (
    `${data.getFullYear()}-${p(data.getMonth() + 1)}-${p(data.getDate())}` +
    `T${p(data.getHours())}:${p(data.getMinutes())}`
  );
}

/* =========================
   REQUISIÇÕES À API
========================= */

async function requisicao(caminho, opcoes = {}) {
  const cabecalhos = {
    ...(opcoes.body ? { "Content-Type": "application/json" } : {}),
    ...(opcoes.headers || {})
  };

  const resposta = await fetch(`/api/admin${caminho}`, {
    credentials: "same-origin",
    ...opcoes,
    headers: cabecalhos
  });

  const texto = await resposta.text();
  let dados = {};

  if (texto) {
    try {
      dados = JSON.parse(texto);
    } catch {
      dados = { mensagem: texto };
    }
  }

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
      `Erro na requisição: ${resposta.status}.`
    );
  }

  return dados;
}

/* =========================
   LOGIN E SESSÃO
========================= */

function mostrarPainel() {
  if (telaLogin) telaLogin.hidden = true;
  if (telaPainel) telaPainel.hidden = false;
  if (botaoSair) botaoSair.hidden = false;
}

function mostrarLogin() {
  if (telaLogin) telaLogin.hidden = false;
  if (telaPainel) telaPainel.hidden = true;
  if (botaoSair) botaoSair.hidden = true;
}

if (formLogin) {
  formLogin.addEventListener("submit", async evento => {
    evento.preventDefault();

    mostrarMensagemElemento(
      erroLogin,
      "Verificando acesso..."
    );

    try {
      await requisicao("/login", {
        method: "POST",
        body: JSON.stringify({
          senha: campoSenha?.value || ""
        })
      });

      if (campoSenha) campoSenha.value = "";

      mostrarMensagemElemento(erroLogin, "");
      mostrarPainel();

      alternarAba("pedidos");
    } catch (erro) {
      mostrarMensagemElemento(erroLogin, erro.message, true);
    }
  });
}

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

if (botaoSair) {
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
}

/* =========================
   NAVEGAÇÃO
========================= */

const SECOES = {
  pedidos: "#secao-pedidos",
  produtos: "#secao-produtos",
  categorias: "#secao-categorias",
  cupons: "#secao-cupons",
  faturamento: "#secao-faturamento",
  configuracoes: "#secao-configuracoes",
  clientes: "#secao-clientes"
};

const CARREGADORES = {
  pedidos: carregarPedidos,
  produtos: carregarProdutos,
  categorias: carregarCategorias,
  cupons: carregarCupons,
  faturamento: carregarFaturamento,
  configuracoes: carregarConfiguracoes,
  clientes: carregarClientes
};

function alternarAba(nome) {
  for (const [chave, seletor] of Object.entries(SECOES)) {
    const secao = $(seletor);

    if (secao) {
      secao.hidden = chave !== nome;
    }
  }

  $$(".aba-admin").forEach(botao => {
    const ativa = botao.dataset.aba === nome;

    botao.classList.toggle("ativa", ativa);
    botao.classList.toggle("btn-primary", ativa);
    botao.classList.toggle("btn-light", !ativa);
  });

  mostrarMensagem("");

  if (CARREGADORES[nome]) {
    CARREGADORES[nome]();
  }
}

$$(".aba-admin").forEach(botao => {
  botao.addEventListener("click", () => {
    alternarAba(botao.dataset.aba);
  });
});

/* =========================
   PEDIDOS
========================= */

async function carregarPedidos() {
  if (!listaPedidos) return;

  mostrarErroTabela(
    "#lista-pedidos",
    "Carregando pedidos...",
    6
  );

  mostrarMensagem("");

  try {
    const dados = await requisicao("/pedidos");

    pedidos = arrayDaResposta(dados, ["pedidos", "data", "items"]);
    renderizarPedidos();
  } catch (erro) {
    mostrarErroTabela("#lista-pedidos", erro.message, 6);
    mostrarMensagem("Não foi possível carregar os pedidos.", true);
  }
}

function renderizarPedidos() {
  if (!listaPedidos) return;

  listaPedidos.replaceChildren();

  definirTexto("#total-pedidos", pedidos.length);

  definirTexto(
    "#pedidos-abertos",
    pedidos.filter(p =>
      STATUS_ABERTOS.includes(
        String(p.status || "").toLowerCase()
      )
    ).length
  );

  definirTexto(
    "#valor-pedidos",
    dinheiro(
      pedidos.reduce(
        (soma, pedido) => soma + Number(pedido.total || 0),
        0
      )
    )
  );

  if (!pedidos.length) {
    mostrarErroTabela(
      "#lista-pedidos",
      "Nenhum pedido encontrado.",
      6
    );
    return;
  }

  pedidos.forEach(pedido => {
    const tr = elemento("tr");

    const numero =
      pedido.numero ||
      pedido.numero_pedido ||
      pedido.id ||
      "—";

    const data = pedido.criado_em
      ? dataHoraBR(pedido.criado_em)
      : "—";

    tr.append(
      elemento("td", "", `#${numero}`),
      elemento("td", "", pedido.nome_cliente || "Cliente"),
      elemento("td", "", data),
      elemento("td", "", dinheiro(pedido.total))
    );

    const tdStatus = elemento("td");
    const select = document.createElement("select");

    Object.entries(STATUS).forEach(([valor, nome]) => {
      const opcao = elemento("option", "", nome);

      opcao.value = valor;
      opcao.selected =
        String(pedido.status || "").toLowerCase() === valor;

      select.append(opcao);
    });

    select.addEventListener("change", () => {
      alterarStatus(pedido.id, select.value, select);
    });

    tdStatus.append(select);

    const tdAcoes = elemento("td");
    const botaoDetalhes = elemento(
      "button",
      "btn btn-light",
      "Detalhes"
    );

    botaoDetalhes.type = "button";
    botaoDetalhes.addEventListener("click", () => {
      abrirDetalhes(pedido.id);
    });

    tdAcoes.append(botaoDetalhes);
    tr.append(tdStatus, tdAcoes);

    listaPedidos.append(tr);
  });
}

async function alterarStatus(id, status, select) {
  if (select) select.disabled = true;

  mostrarMensagem("Atualizando status...");

  try {
    await requisicao(
      `/pedidos/${encodeURIComponent(id)}/status`,
      {
        method: "PATCH",
        body: JSON.stringify({ status })
      }
    );

    mostrarMensagem("Status atualizado com sucesso.");
    await carregarPedidos();
  } catch (erro) {
    mostrarMensagem(erro.message, true);
    await carregarPedidos();
  } finally {
    if (select) select.disabled = false;
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

  const quantidade = Number(item.quantidade || 1);
  const precoUnitario = item.preco_unitario ?? item.preco;

  const subtotal =
    item.subtotal ??
    (precoUnitario != null
      ? quantidade * Number(precoUnitario)
      : 0);

  bloco.append(
    elemento(
      "strong",
      "",
      `${quantidade} × ${item.nome_produto || item.nome || "Produto"}`
    ),
    linhaDetalhe("Preço unitário", dinheiro(precoUnitario)),
    linhaDetalhe("Subtotal", dinheiro(subtotal))
  );

  if (item.observacao) {
    bloco.append(
      elemento("p", "", `Observação: ${item.observacao}`)
    );
  }

  (item.opcoes || []).forEach(opcao => {
    bloco.append(
      elemento(
        "p",
        "",
        `${opcao.nome_grupo || "Opção"}: ${
          opcao.nome_opcao || ""
        } (+ ${dinheiro(opcao.preco_adicional)})`
      )
    );
  });

  destino.append(bloco);
}

async function abrirDetalhes(id) {
  const titulo = $("#detalhe-titulo");
  const conteudo = $("#detalhe-conteudo");

  if (!conteudo) return;

  if (titulo) titulo.textContent = `Pedido #${id}`;

  conteudo.replaceChildren(
    elemento("p", "", "Carregando detalhes...")
  );

  if (dialogDetalhes?.showModal && !dialogDetalhes.open) {
    dialogDetalhes.showModal();
  }

  try {
    const dados = await requisicao(
      `/pedidos/${encodeURIComponent(id)}`
    );

    const pedido = dados.pedido || dados;

    if (titulo) {
      titulo.textContent =
        `Pedido #${pedido.numero || pedido.numero_pedido || id}`;
    }

    conteudo.replaceChildren();

    const resumo = secaoDetalhe("Informações do pedido");

    resumo.append(
      linhaDetalhe("Cliente", pedido.nome_cliente),
      linhaDetalhe(
        "Telefone",
        pedido.telefone_cliente || pedido.telefone
      ),
      linhaDetalhe("Modalidade", pedido.modalidade),
      linhaDetalhe(
        "Status",
        STATUS[String(pedido.status || "").toLowerCase()] ||
          pedido.status
      ),
      linhaDetalhe("Subtotal", dinheiro(pedido.subtotal)),
      linhaDetalhe("Entrega", dinheiro(pedido.taxa_entrega)),
      linhaDetalhe("Desconto", dinheiro(pedido.desconto)),
      linhaDetalhe("Total", dinheiro(pedido.total))
    );

    conteudo.append(resumo);

    const secaoItens = secaoDetalhe("Produtos");

    if (Array.isArray(pedido.itens) && pedido.itens.length) {
      pedido.itens.forEach(item => {
        adicionarItemPedido(item, secaoItens);
      });
    } else {
      secaoItens.append(
        elemento("p", "", "Nenhum item retornado.")
      );
    }

    conteudo.append(secaoItens);

    if (
      Array.isArray(pedido.pagamentos) &&
      pedido.pagamentos.length
    ) {
      const secaoPagamentos = secaoDetalhe("Pagamento");

      pedido.pagamentos.forEach(pagamento => {
        const bloco = elemento("div", "item-pedido");

        bloco.append(
          linhaDetalhe("Forma", pagamento.forma),
          linhaDetalhe("Valor", dinheiro(pagamento.valor)),
          linhaDetalhe("Status", pagamento.status)
        );

        if (pagamento.troco_para != null) {
          bloco.append(
            linhaDetalhe(
              "Troco para",
              dinheiro(pagamento.troco_para)
            )
          );
        }

        secaoPagamentos.append(bloco);
      });

      conteudo.append(secaoPagamentos);
    }
  } catch (erro) {
    conteudo.replaceChildren(
      elemento("p", "mensagem", erro.message)
    );
  }
}

/* =========================
   CATEGORIAS
========================= */

function normalizarCategoria(c) {
  const ativo =
    c.active ??
    c.ativo ??
    c.is_active ??
    c.ativa;

  return {
    ...c,
    id: c.id ?? c.id_categoria ?? c.category_id,
    name: c.name ?? c.nome ?? c.nome_categoria ?? "",
    description: c.description ?? c.descricao ?? "",
    image_url: c.image_url ?? c.imagem_url ?? c.imagem ?? "",
    order: c.order ?? c.ordem ?? c.ordem_exibicao,
    active: boolValor(ativo, true)
  };
}

async function carregarCategorias() {
  const lista = $("#lista-categorias");

  if (lista) {
    mostrarErroTabela(
      "#lista-categorias",
      "Carregando categorias...",
      4
    );
  }

  try {
    const dados = await requisicao("/categorias");

    categorias = arrayDaResposta(
      dados,
      ["categorias", "data", "items", "resultados"]
    ).map(normalizarCategoria);

    renderizarCategorias();
    preencherSelectCategorias();

    return true;
  } catch (erro) {
    categorias = [];
    preencherSelectCategorias();

    if (lista) {
      mostrarErroTabela(
        "#lista-categorias",
        erro.message,
        4
      );
    }

    mostrarMensagem(
      `Não foi possível carregar as categorias: ${erro.message}`,
      true
    );

    return false;
  }
}

function renderizarCategorias() {
  const lista = $("#lista-categorias");
  if (!lista) return;

  lista.replaceChildren();

  if (!categorias.length) {
    mostrarErroTabela(
      "#lista-categorias",
      "Nenhuma categoria encontrada.",
      4
    );
    return;
  }

  categorias.forEach(categoria => {
    const tr = elemento("tr");

    tr.append(
      elemento("td", "", categoria.name || "—"),
      elemento("td", "", categoria.description || "—"),
      elemento("td", "", String(categoria.order ?? "—")),
      elemento("td", "", categoria.active ? "Sim" : "Não")
    );

    lista.append(tr);
  });
}

function preencherSelectCategorias(categoriaAtualId = null) {
  const select = $("#produto-categoria");
  if (!select) return;

  const atual = select.value;
  select.replaceChildren();

  const inicial = elemento(
    "option",
    "",
    "Selecione uma categoria"
  );

  inicial.value = "";
  select.append(inicial);

  categorias
    .filter(c =>
      c.id != null &&
      String(c.name || "").trim() &&
      (
        c.active ||
        (
          categoriaAtualId != null &&
          String(c.id) === String(categoriaAtualId)
        )
      )
    )
    .forEach(categoria => {
      const nome = categoria.active
        ? categoria.name
        : `${categoria.name} (inativa)`;

      const opcao = elemento("option", "", nome);
      opcao.value = String(categoria.id);
      select.append(opcao);
    });

  if ([...select.options].some(opcao => opcao.value === atual)) {
    select.value = atual;
  }
}

function abrirFormularioCategoria() {
  const form = $("#form-categoria");
  const card = $("#formulario-categoria-card");

  if (!form || !card) {
    mostrarMensagem(
      "Não foi encontrado o formulário de categorias.",
      true
    );
    return;
  }

  form.reset();

  if ($("#categoria-ordem")) {
    $("#categoria-ordem").value = "0";
  }

  if ($("#categoria-ativa")) {
    $("#categoria-ativa").checked = true;
  }

  mostrarMensagemElemento($("#mensagem-categoria"), "");

  card.hidden = false;
  card.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });

  $("#categoria-nome")?.focus();
}

function fecharFormularioCategoria() {
  $("#form-categoria")?.reset();

  const card = $("#formulario-categoria-card");
  if (card) card.hidden = true;

  mostrarMensagemElemento($("#mensagem-categoria"), "");
}

async function salvarCategoria(evento) {
  evento.preventDefault();

  const nome = $("#categoria-nome")?.value.trim() || "";
  const msg = $("#mensagem-categoria");
  const botao = $("#btn-salvar-categoria");

  if (!nome) {
    mostrarMensagemElemento(
      msg,
      "Informe o nome da categoria.",
      true
    );
    return;
  }

  const ordemTexto = $("#categoria-ordem")?.value.trim() ?? "0";
  const ordem = Number(ordemTexto);

  if (
    ordemTexto === "" ||
    !Number.isInteger(ordem) ||
    ordem < 0 ||
    ordem > 65535
  ) {
    mostrarMensagemElemento(
      msg,
      "Informe uma ordem válida entre 0 e 65535.",
      true
    );
    return;
  }

  const dados = {
    name: nome,
    description: $("#categoria-descricao")?.value.trim() || "",
    image_url: $("#categoria-imagem")?.value.trim() || "",
    order: ordem,
    active: $("#categoria-ativa")?.checked ?? true
  };

  if (botao) botao.disabled = true;

  mostrarMensagemElemento(msg, "Salvando categoria...");

  try {
    await requisicao("/categorias", {
      method: "POST",
      body: JSON.stringify(dados)
    });

    await carregarCategorias();
    fecharFormularioCategoria();
    mostrarMensagem("Categoria cadastrada com sucesso.");
  } catch (erro) {
    mostrarMensagemElemento(msg, erro.message, true);
  } finally {
    if (botao) botao.disabled = false;
  }
}

$("#btn-nova-categoria")?.addEventListener(
  "click",
  abrirFormularioCategoria
);

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

/* =========================
   PRODUTOS
========================= */

function normalizarProduto(p) {
  return {
    ...p,
    id: p.id ?? p.id_produto,
    name: p.name ?? p.nome ?? "",
    description: p.description ?? p.descricao ?? "",
    category_id: p.category_id ?? p.id_categoria,
    category_name: p.category_name ?? p.nome_categoria ?? "",
    price: p.price ?? p.preco ?? 0,
    promo_price: p.promo_price ?? p.preco_promocional ?? null,
    image_url: p.image_url ?? p.imagem_url ?? p.imagem ?? "",
    prep_minutes: p.prep_minutes ?? p.tempo_preparo_min ?? null,
    available: boolValor(p.available ?? p.disponivel, true),
    active: boolValor(p.active ?? p.ativo, true),
    featured: boolValor(p.featured ?? p.destaque, false)
  };
}

async function carregarProdutos() {
  if (!$("#lista-produtos")) return;

  mostrarErroTabela(
    "#lista-produtos",
    "Carregando produtos...",
    6
  );

  mostrarMensagem("");

  try {
    const dados = await requisicao("/produtos");

    produtos = arrayDaResposta(
      dados,
      ["produtos", "data", "items"]
    ).map(normalizarProduto);

    renderizarProdutos();
  } catch (erro) {
    mostrarErroTabela("#lista-produtos", erro.message, 6);
    mostrarMensagem("Não foi possível carregar os produtos.", true);
  }
}

function renderizarProdutos() {
  const lista = $("#lista-produtos");
  if (!lista) return;

  lista.replaceChildren();

  if (!produtos.length) {
    mostrarErroTabela(
      "#lista-produtos",
      "Nenhum produto encontrado.",
      6
    );
    return;
  }

  produtos.forEach(produto => {
    const tr = elemento("tr");

    const temPromocao =
      produto.promo_price !== null &&
      produto.promo_price !== undefined &&
      produto.promo_price !== "" &&
      Number(produto.promo_price) > 0;

    tr.append(
      elemento("td", "", produto.name || "—"),
      elemento("td", "", produto.category_name || "—"),
      elemento(
        "td",
        "",
        temPromocao
          ? `${dinheiro(produto.promo_price)} (Promoção)`
          : dinheiro(produto.price)
      ),
      elemento(
        "td",
        "",
        produto.available ? "Disponível" : "Indisponível"
      ),
      elemento("td", "", produto.active ? "Sim" : "Não")
    );

    const acoes = elemento("td");

    const editar = elemento("button", "btn btn-light", "Editar");
    const duplicar = elemento("button", "btn btn-light", "Duplicar");
    const status = elemento(
      "button",
      "btn btn-light",
      produto.active ? "Desativar" : "Ativar"
    );

    [editar, duplicar, status].forEach(botao => {
      botao.type = "button";
    });

    editar.addEventListener("click", async () => {
      if (await carregarCategorias()) {
        abrirFormularioProduto(produto);
      }
    });

    duplicar.addEventListener("click", () => {
      duplicarProduto(produto.id);
    });

    status.addEventListener("click", () => {
      alterarAtivoProduto(produto);
    });

    acoes.append(editar, duplicar, status);
    tr.append(acoes);
    lista.append(tr);
  });
}

function definirStatusUploadImagem(texto, erro = false) {
  const status = $("#produto-imagem-status");
  if (!status) return;
  status.textContent = texto;
  status.dataset.tipo = erro ? "erro" : "sucesso";
}

function atualizarPreviewImagem(url) {
  const preview = $("#produto-imagem-preview");
  if (!preview) return;
  const valor = (url || "").trim();

  if (!valor) {
    preview.removeAttribute("src");
    preview.hidden = true;
    return;
  }

  try {
    const endereco = new URL(valor);
    if (!["http:", "https:"].includes(endereco.protocol)) {
      throw new Error("URL invalida.");
    }
    preview.src = endereco.href;
    preview.hidden = false;
  } catch {
    preview.removeAttribute("src");
    preview.hidden = true;
  }
}

async function enviarImagemProduto(arquivo) {
  definirStatusUploadImagem("Preparando o envio da imagem...");
  const assinatura = await requisicao("/produtos/upload-assinatura");

  const dados = new FormData();
  dados.append("file", arquivo);
  dados.append("api_key", assinatura.api_key);
  dados.append("timestamp", String(assinatura.timestamp));
  dados.append("folder", assinatura.folder);
  dados.append("signature", assinatura.signature);

  const resposta = await fetch(
    `https://api.cloudinary.com/v1_1/${encodeURIComponent(assinatura.cloud_name)}/image/upload`,
    { method: "POST", body: dados }
  );

  let resultado;
  try {
    resultado = await resposta.json();
  } catch {
    throw new Error("Resposta invalida do servico de imagens.");
  }

  if (!resposta.ok) {
    throw new Error(
      resultado?.error?.message || "Falha no envio da imagem."
    );
  }

  if (!resultado.secure_url) {
    throw new Error("O servico nao retornou uma URL segura.");
  }

  const campoUrl = $("#produto-imagem");
  if (!campoUrl) throw new Error("Campo da URL nao encontrado.");

  campoUrl.value = resultado.secure_url;
  atualizarPreviewImagem(resultado.secure_url);
  definirStatusUploadImagem("Imagem enviada com sucesso.");
}

$("#produto-imagem-arquivo")?.addEventListener("change", async evento => {
  const campoArquivo = evento.currentTarget;
  const arquivo = campoArquivo.files?.[0];
  if (!arquivo) return;

  const tiposPermitidos = [
    "image/jpeg", "image/png", "image/webp", "image/avif"
  ];

  if (!tiposPermitidos.includes(arquivo.type)) {
    definirStatusUploadImagem("Use uma imagem JPG, PNG, WEBP ou AVIF.", true);
    campoArquivo.value = "";
    return;
  }

  if (arquivo.size > 5 * 1024 * 1024) {
    definirStatusUploadImagem("A imagem deve ter no maximo 5 MB.", true);
    campoArquivo.value = "";
    return;
  }

  if (uploadImagemEmAndamento) {
    definirStatusUploadImagem("Ja existe um envio em andamento.", true);
    campoArquivo.value = "";
    return;
  }

  uploadImagemEmAndamento = true;
  try {
    await enviarImagemProduto(arquivo);
  } catch (erro) {
    definirStatusUploadImagem(erro.message || "Falha no envio.", true);
    campoArquivo.value = "";
  } finally {
    uploadImagemEmAndamento = false;
  }
});

$("#produto-imagem")?.addEventListener("input", evento => {
  atualizarPreviewImagem(evento.currentTarget.value);
});

function abrirFormularioProduto(produto = null) {
  const form = $("#form-produto");
  const card = $("#formulario-produto-card");

  if (!form || !card) {
    mostrarMensagem(
      "Não foi encontrado o formulário de produtos.",
      true
    );
    return;
  }

  form.reset();
  definirStatusUploadImagem("");
  atualizarPreviewImagem("");
  card.hidden = false;

  if ($("#produto-id")) {
    $("#produto-id").value = produto?.id ?? "";
  }

  definirTexto(
    "#titulo-form-produto",
    produto ? "Editar produto" : "Cadastrar produto"
  );

  const valores = {
    "#produto-nome": produto?.name || "",
    "#produto-descricao": produto?.description || "",
    "#produto-preco": produto?.price ?? "",
    "#produto-preco-promocional": produto?.promo_price ?? "",
    "#produto-imagem": produto?.image_url || "",
    "#produto-preparo": produto?.prep_minutes ?? ""
  };

  Object.entries(valores).forEach(([seletor, valor]) => {
    const campo = $(seletor);
    if (campo) campo.value = valor;
  });

  if ($("#produto-disponivel")) {
    $("#produto-disponivel").checked =
      produto ? produto.available : true;
  }

  if ($("#produto-destaque")) {
    $("#produto-destaque").checked =
      Boolean(produto?.featured);
  }

  preencherSelectCategorias(produto?.category_id ?? null);

  if ($("#produto-categoria")) {
    $("#produto-categoria").value =
      produto?.category_id != null
        ? String(produto.category_id)
        : "";
  }

  atualizarPreviewImagem($("#produto-imagem")?.value || "");

  card.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}

function fecharFormularioProduto() {
  const card = $("#formulario-produto-card");
  if (card) card.hidden = true;

  $("#form-produto")?.reset();
  definirStatusUploadImagem("");
  atualizarPreviewImagem("");

  if ($("#produto-id")) {
    $("#produto-id").value = "";
  }
}

$("#btn-novo-produto")?.addEventListener("click", async () => {
  if (await carregarCategorias()) {
    abrirFormularioProduto();
  }
});

$("#btn-cancelar-produto")?.addEventListener(
  "click",
  fecharFormularioProduto
);

$("#form-produto")?.addEventListener(
  "submit",
  async evento => {
    evento.preventDefault();

    if (uploadImagemEmAndamento) {
      mostrarMensagem("Aguarde o envio da imagem terminar.", true);
      return;
    }

    const id = $("#produto-id")?.value || "";
    const precoTexto = $("#produto-preco")?.value.trim() || "";
    const promoTexto =
      $("#produto-preco-promocional")?.value.trim() || "";

    const preco = numeroBR(precoTexto);
    const promo = promoTexto === "" ? null : numeroBR(promoTexto);

    if (
      !precoTexto ||
      !Number.isFinite(preco) ||
      preco <= 0
    ) {
      mostrarMensagem(
        "Informe um preço normal válido e maior que zero.",
        true
      );
      return;
    }

    if (
      promo !== null &&
      (!Number.isFinite(promo) || promo <= 0 || promo >= preco)
    ) {
      mostrarMensagem(
        "O preço promocional deve ser maior que zero e menor que o preço normal.",
        true
      );
      return;
    }

    const nome = $("#produto-nome")?.value.trim() || "";

    if (!nome) {
      mostrarMensagem("Informe o nome do produto.", true);
      return;
    }

    const categoriaId = Number($("#produto-categoria")?.value);

    if (!categoriaId) {
      mostrarMensagem("Selecione uma categoria.", true);
      return;
    }

    const preparoTexto = $("#produto-preparo")?.value.trim() || "";
    const preparo = preparoTexto === "" ? null : Number(preparoTexto);

    if (
      preparo !== null &&
      (!Number.isInteger(preparo) || preparo < 0)
    ) {
      mostrarMensagem(
        "O tempo de preparo deve ser um número inteiro igual ou maior que zero.",
        true
      );
      return;
    }

    const dados = {
      name: nome,
      description: $("#produto-descricao")?.value.trim() || "",
      category_id: categoriaId,
      price: preco,
      promo_price: promo,
      image_url: $("#produto-imagem")?.value.trim() || "",
      prep_minutes: preparo,
      available: $("#produto-disponivel")?.checked ?? true,
      featured: $("#produto-destaque")?.checked ?? false
    };

    const botao = evento.submitter;
    if (botao) botao.disabled = true;

    try {
      await requisicao(
        id
          ? `/produtos/${encodeURIComponent(id)}`
          : "/produtos",
        {
          method: id ? "PATCH" : "POST",
          body: JSON.stringify(dados)
        }
      );

      fecharFormularioProduto();
      await carregarProdutos();

      mostrarMensagem(
        id
          ? "Produto atualizado com sucesso."
          : "Produto cadastrado com sucesso."
      );
    } catch (erro) {
      mostrarMensagem(erro.message, true);
    } finally {
      if (botao) botao.disabled = false;
    }
  }
);

async function duplicarProduto(id) {
  if (!confirm("Deseja criar uma cópia deste produto?")) return;

  try {
    await requisicao(
      `/produtos/${encodeURIComponent(id)}/duplicar`,
      {
        method: "POST",
        body: "{}"
      }
    );

    await carregarProdutos();
    mostrarMensagem("Produto duplicado com sucesso.");
  } catch (erro) {
    mostrarMensagem(erro.message, true);
  }
}

async function alterarAtivoProduto(produto) {
  const novoAtivo = !produto.active;

  if (
    !confirm(
      `Deseja ${novoAtivo ? "ativar" : "desativar"} o produto "${produto.name}"?`
    )
  ) {
    return;
  }

  try {
    await requisicao(
      `/produtos/${encodeURIComponent(produto.id)}/ativo`,
      {
        method: "PATCH",
        body: JSON.stringify({ active: novoAtivo })
      }
    );

    await carregarProdutos();

    mostrarMensagem(
      `Produto ${novoAtivo ? "ativado" : "desativado"} com sucesso.`
    );
  } catch (erro) {
    mostrarMensagem(erro.message, true);
  }
}

/* =========================
   CUPONS
========================= */

async function carregarCupons() {
  if (!$("#lista-cupons")) return;

  mostrarErroTabela(
    "#lista-cupons",
    "Carregando cupons...",
    7
  );

  mostrarMensagem("");

  try {
    const dados = await requisicao("/cupons");

    cupons = arrayDaResposta(
      dados,
      ["cupons", "data", "items"]
    );

    renderizarCupons();
  } catch (erro) {
    mostrarErroTabela("#lista-cupons", erro.message, 7);
    mostrarMensagem("Não foi possível carregar os cupons.", true);
  }
}

function formatarValorCupom(cupom) {
  const valor = Number(cupom.valor || 0);

  return cupom.tipo === "percentual"
    ? `${valor}%`
    : dinheiro(valor);
}

function renderizarCupons() {
  const lista = $("#lista-cupons");
  if (!lista) return;

  lista.replaceChildren();

  if (!cupons.length) {
    mostrarErroTabela(
      "#lista-cupons",
      "Nenhum cupom cadastrado.",
      7
    );
    return;
  }

  cupons.forEach(cupom => {
    const tr = elemento("tr");
    const usos = Number(cupom.utilizacoes || 0);
    const limite = cupom.limite_total;

    const uso =
      limite != null && limite !== ""
        ? `${usos} / ${limite}`
        : String(usos);

    const validade =
      `${formatarDataCupom(cupom.inicio_em) || "Sem início"} até ` +
      `${formatarDataCupom(cupom.fim_em) || "Sem vencimento"}`;

    tr.append(
      elemento("td", "", cupom.codigo || "—"),
      elemento("td", "", formatarValorCupom(cupom)),
      elemento("td", "", dinheiro(cupom.pedido_minimo)),
      elemento("td", "", uso),
      elemento("td", "", validade),
      elemento(
        "td",
        "",
        boolValor(cupom.ativo) ? "Ativo" : "Inativo"
      )
    );

    const acoes = elemento("td");

    const editar = elemento("button", "btn btn-light", "Editar");
    const status = elemento(
      "button",
      "btn btn-light",
      boolValor(cupom.ativo) ? "Desativar" : "Ativar"
    );

    editar.type = "button";
    status.type = "button";

    editar.addEventListener("click", () => editarCupom(cupom.id));
    status.addEventListener("click", () => alternarStatusCupom(cupom));

    acoes.append(editar, status);
    tr.append(acoes);
    lista.append(tr);
  });
}

function abrirFormularioCupom() {
  const form = $("#form-cupom");
  const card = $("#formulario-cupom-card");

  if (!form || !card) {
    mostrarMensagem(
      "Não foi encontrado o formulário de cupons.",
      true
    );
    return;
  }

  form.reset();

  if ($("#cupom-id")) $("#cupom-id").value = "";
  if ($("#cupom-ativo")) $("#cupom-ativo").checked = true;

  card.hidden = false;
  atualizarLimiteValorCupom();

  card.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });
}

function editarCupom(id) {
  const cupom = cupons.find(
    item => String(item.id) === String(id)
  );

  if (!cupom) return;

  const valores = {
    "#cupom-id": cupom.id,
    "#cupom-codigo": cupom.codigo || "",
    "#cupom-tipo": cupom.tipo || "valor_fixo",
    "#cupom-valor": cupom.valor ?? "",
    "#cupom-pedido-minimo": cupom.pedido_minimo ?? 0,
    "#cupom-inicio": valorParaInputDataHora(cupom.inicio_em),
    "#cupom-fim": valorParaInputDataHora(cupom.fim_em),
    "#cupom-limite-total": cupom.limite_total ?? "",
    "#cupom-limite-cliente": cupom.limite_por_cliente ?? ""
  };

  Object.entries(valores).forEach(([seletor, valor]) => {
    const campo = $(seletor);
    if (campo) campo.value = valor;
  });

  if ($("#cupom-ativo")) {
    $("#cupom-ativo").checked = boolValor(cupom.ativo);
  }

  const card = $("#formulario-cupom-card");

  if (card) {
    card.hidden = false;
    card.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }

  atualizarLimiteValorCupom();
}

function atualizarLimiteValorCupom() {
  const tipo = $("#cupom-tipo");
  const campoValor = $("#cupom-valor");

  if (!tipo || !campoValor) return;

  if (tipo.value === "percentual") {
    campoValor.max = "100";
  } else {
    campoValor.removeAttribute("max");
  }
}

async function salvarCupom(evento) {
  evento.preventDefault();

  const id = $("#cupom-id")?.value || "";

  const dados = {
    codigo: $("#cupom-codigo")?.value.trim().toUpperCase() || "",
    tipo: $("#cupom-tipo")?.value || "valor_fixo",
    valor: numeroBR($("#cupom-valor")?.value),
    pedido_minimo: numeroBR($("#cupom-pedido-minimo")?.value || 0),
    inicio_em: $("#cupom-inicio")?.value || null,
    fim_em: $("#cupom-fim")?.value || null,
    limite_total: $("#cupom-limite-total")?.value || null,
    limite_por_cliente: $("#cupom-limite-cliente")?.value || null,
    ativo: $("#cupom-ativo")?.checked ?? true
  };

  if (!dados.codigo) {
    mostrarMensagem("Informe o código do cupom.", true);
    return;
  }

  if (!Number.isFinite(dados.valor) || dados.valor <= 0) {
    mostrarMensagem("Informe um valor de desconto válido.", true);
    return;
  }

  if (
    dados.tipo === "percentual" &&
    dados.valor > 100
  ) {
    mostrarMensagem(
      "O desconto percentual não pode ultrapassar 100%.",
      true
    );
    return;
  }

  if (
    !Number.isFinite(dados.pedido_minimo) ||
    dados.pedido_minimo < 0
  ) {
    mostrarMensagem(
      "O pedido mínimo não pode ser negativo.",
      true
    );
    return;
  }

  if (
    dados.inicio_em &&
    dados.fim_em &&
    new Date(dados.fim_em) < new Date(dados.inicio_em)
  ) {
    mostrarMensagem(
      "A data final não pode ser anterior à data inicial.",
      true
    );
    return;
  }

  for (const chave of ["limite_total", "limite_por_cliente"]) {
    if (dados[chave] !== null) {
      const numero = Number(dados[chave]);

      if (!Number.isInteger(numero) || numero < 1) {
        mostrarMensagem(
          "Os limites devem ser números inteiros maiores que zero.",
          true
        );
        return;
      }

      dados[chave] = numero;
    }
  }

  const botao = evento.submitter;
  if (botao) botao.disabled = true;

  try {
    await requisicao(
      id
        ? `/cupons/${encodeURIComponent(id)}`
        : "/cupons",
      {
        method: id ? "PATCH" : "POST",
        body: JSON.stringify(dados)
      }
    );

    if ($("#formulario-cupom-card")) {
      $("#formulario-cupom-card").hidden = true;
    }

    await carregarCupons();

    mostrarMensagem(
      id
        ? "Cupom atualizado com sucesso."
        : "Cupom cadastrado com sucesso."
    );
  } catch (erro) {
    mostrarMensagem(erro.message, true);
  } finally {
    if (botao) botao.disabled = false;
  }
}

async function alternarStatusCupom(cupom) {
  const ativo = boolValor(cupom.ativo);

  if (
    !confirm(
      `Deseja ${ativo ? "desativar" : "ativar"} o cupom "${cupom.codigo}"?`
    )
  ) {
    return;
  }

  try {
    await requisicao(
      `/cupons/${encodeURIComponent(cupom.id)}/ativo`,
      {
        method: "PATCH",
        body: JSON.stringify({ ativo: !ativo })
      }
    );

    await carregarCupons();

    mostrarMensagem(
      `Cupom ${ativo ? "desativado" : "ativado"} com sucesso.`
    );
  } catch (erro) {
    mostrarMensagem(erro.message, true);
  }
}

$("#form-cupom")?.addEventListener("submit", salvarCupom);

$("#btn-novo-cupom")?.addEventListener(
  "click",
  abrirFormularioCupom
);

$("#btn-cancelar-cupom")?.addEventListener("click", () => {
  if ($("#formulario-cupom-card")) {
    $("#formulario-cupom-card").hidden = true;
  }
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
   FATURAMENTO
========================= */

function configurarFiltroFaturamento() {
  const filtro = $("#filtro-periodo-faturamento");
  const campos = $("#campos-periodo-personalizado");

  if (filtro && campos) {
    campos.hidden = filtro.value !== "personalizado";
  }
}

async function carregarFaturamento() {
  const lista = $("#lista-faturamento");

  if (!lista) {
    mostrarMensagem(
      "A seção de faturamento não existe no admin.html.",
      true
    );
    return;
  }

  configurarFiltroFaturamento();
  mostrarMensagem("");

  const parametros = new URLSearchParams();
  const periodo =
    $("#filtro-periodo-faturamento")?.value || "hoje";

  parametros.set("periodo", periodo);

  if (periodo === "personalizado") {
    const inicio =
      $("#faturamento-data-inicial")?.value || "";

    const fim =
      $("#faturamento-data-final")?.value || "";

    if (!inicio || !fim) {
      mostrarErroTabela(
        "#lista-faturamento",
        "Selecione a data inicial e a data final.",
        7
      );

      definirTexto(
        "#mensagem-filtro-faturamento",
        "Preencha as duas datas para consultar."
      );

      return;
    }

    if (fim < inicio) {
      mostrarErroTabela(
        "#lista-faturamento",
        "A data final não pode ser anterior à inicial.",
        7
      );

      definirTexto(
        "#mensagem-filtro-faturamento",
        "Confira o intervalo de datas."
      );

      return;
    }

    parametros.set("data_inicial", inicio);
    parametros.set("data_final", fim);
  }

  mostrarErroTabela(
    "#lista-faturamento",
    "Carregando faturamento...",
    7
  );

  definirTexto("#mensagem-filtro-faturamento", "");

  try {
    const resposta = await requisicao(
      `/faturamento?${parametros.toString()}`
    );

    faturamento = resposta.faturamento || resposta;

    definirTexto(
      "#faturamento-total",
      dinheiro(faturamento.total)
    );

    definirTexto(
      "#faturamento-quantidade",
      Number(faturamento.quantidade || 0).toLocaleString("pt-BR")
    );

    definirTexto(
      "#faturamento-ticket-medio",
      dinheiro(faturamento.ticket_medio)
    );

    definirTexto(
      "#descricao-periodo-faturamento",
      faturamento.periodo_descricao || ""
    );

    const registros = arrayDaResposta(
      faturamento,
      ["pagamentos", "registros", "itens"]
    );

    renderizarFaturamento(registros);
  } catch (erro) {
    mostrarErroTabela(
      "#lista-faturamento",
      erro.message,
      7
    );

    definirTexto(
      "#mensagem-filtro-faturamento",
      erro.message
    );

    mostrarMensagem(
      "Não foi possível carregar o faturamento.",
      true
    );
  }
}

function renderizarFaturamento(registros) {
  const lista = $("#lista-faturamento");
  if (!lista) return;

  lista.replaceChildren();

  if (!Array.isArray(registros) || !registros.length) {
    mostrarErroTabela(
      "#lista-faturamento",
      "Nenhum pagamento confirmado neste período.",
      7
    );
    return;
  }

  registros.forEach(pagamento => {
    const tr = elemento("tr");

    const numero =
      pagamento.numero_pedido ??
      pagamento.pedido_id ??
      "—";

    const forma = String(
      pagamento.forma ??
      pagamento.forma_pagamento ??
      "—"
    ).replaceAll("_", " ");

    tr.append(
      elemento(
        "td",
        "",
        numero === "—" ? "—" : `#${numero}`
      ),
      elemento(
        "td",
        "",
        pagamento.nome_cliente || "Cliente"
      ),
      elemento("td", "", forma),
      elemento("td", "", dinheiro(pagamento.valor)),
      elemento("td", "", pagamento.status || "Pago"),
      elemento(
        "td",
        "",
        dataHoraBR(
          pagamento.pago_em ?? pagamento.data_pagamento
        )
      ),
      elemento(
        "td",
        "",
        pagamento.pagamento_id ?? pagamento.id ?? "—"
      )
    );

    lista.append(tr);
  });
}

$("#filtro-periodo-faturamento")?.addEventListener(
  "change",
  configurarFiltroFaturamento
);

$("#btn-aplicar-filtro-faturamento")?.addEventListener(
  "click",
  carregarFaturamento
);

$("#btn-atualizar-faturamento")?.addEventListener(
  "click",
  carregarFaturamento
);

/* =========================
   CONFIGURAÇÕES / ENTREGA
========================= */

async function carregarConfiguracoes() {
  carregarFuncionamento();
  const campo = $("#taxa-entrega");
  const msg = $("#mensagem-taxa-entrega");

  if (!campo || !msg) return;

  mostrarMensagemElemento(
    msg,
    "Carregando configurações..."
  );

  try {
    const dados = await requisicao("/configuracoes");

    if (dados.taxa_entrega_padrao === undefined) {
      throw new Error(
        "O servidor não retornou a taxa de entrega."
      );
    }

    campo.value = dados.taxa_entrega_padrao;

    mostrarMensagemElemento(msg, "");
  } catch (erro) {
    mostrarMensagemElemento(
      msg,
      `Não foi possível carregar a taxa: ${erro.message}`,
      true
    );
  }
}

$("#form-taxa-entrega")?.addEventListener(
  "submit",
  async evento => {
    evento.preventDefault();

    const campo = $("#taxa-entrega");
    const msg = $("#mensagem-taxa-entrega");
    const botao = $("#btn-salvar-taxa-entrega");

    if (!campo || !msg) return;

    const texto = campo.value.trim();
    const valor = numeroBR(texto);

    if (
      texto === "" ||
      !Number.isFinite(valor) ||
      valor < 0 ||
      valor > 99999999.99
    ) {
      mostrarMensagemElemento(
        msg,
        "Informe um valor válido para a entrega.",
        true
      );
      return;
    }

    if (botao) botao.disabled = true;

    mostrarMensagemElemento(msg, "Salvando taxa...");

    try {
      await requisicao("/configuracoes/taxa-entrega", {
        method: "PATCH",
        body: JSON.stringify({
          taxa_entrega_padrao: valor
        })
      });

      mostrarMensagemElemento(
        msg,
        "Taxa de entrega salva com sucesso!"
      );

      mostrarMensagem(
        "Configuração da entrega atualizada."
      );
    } catch (erro) {
      mostrarMensagemElemento(
        msg,
        `Erro ao salvar: ${erro.message}`,
        true
      );
    } finally {
      if (botao) botao.disabled = false;
    }
  }
);

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
   CLIENTES
========================= */

async function carregarClientes() {
  const lista = $("#lista-clientes");

  if (!lista) {
    mostrarMensagem(
      "A tabela de clientes não foi encontrada no admin.html.",
      true
    );
    return;
  }

  mostrarErroTabela(
    "#lista-clientes",
    "Carregando clientes...",
    5
  );

  mostrarMensagem("");

  try {
    const dados = await requisicao("/clientes");

    clientes = arrayDaResposta(
      dados,
      ["clientes", "data", "items"]
    );

    renderizarClientes();
  } catch (erro) {
    clientes = [];

    mostrarErroTabela(
      "#lista-clientes",
      erro.message,
      5
    );

    mostrarMensagem(
      "Não foi possível carregar os clientes.",
      true
    );
  }
}

function renderizarClientes() {
  const lista = $("#lista-clientes");
  if (!lista) return;

  lista.replaceChildren();

  const filtro = (
    $("#filtro-busca-cliente")?.value || ""
  ).trim().toLocaleLowerCase("pt-BR");

  const clientesFiltrados = clientes.filter(cliente => {
    const nome = String(
      cliente.nome || cliente.nome_cliente || ""
    ).toLocaleLowerCase("pt-BR");

    const telefone = String(
      cliente.telefone_cliente || cliente.telefone || ""
    ).toLocaleLowerCase("pt-BR");

    return nome.includes(filtro) || telefone.includes(filtro);
  });

  if (!clientesFiltrados.length) {
    mostrarErroTabela(
      "#lista-clientes",
      clientes.length
        ? "Nenhum cliente corresponde à busca."
        : "Nenhum cliente encontrado.",
      5
    );
    return;
  }

  clientesFiltrados.forEach(cliente => {
    const tr = elemento("tr");

    const nome =
      cliente.nome ||
      cliente.nome_cliente ||
      "Cliente";

    const telefone =
      cliente.telefone_cliente ||
      cliente.telefone ||
      "—";

    const totalPedidos = Number(
      cliente.total_pedidos || 0
    );

    const totalGasto = Number(
      cliente.total_gasto || 0
    );

    const ultimaCompra = cliente.ultima_compra
      ? dataHoraBR(cliente.ultima_compra)
      : "—";

    tr.append(
      elemento("td", "", nome),
      elemento("td", "", telefone),
      elemento("td", "", totalPedidos.toLocaleString("pt-BR")),
      elemento("td", "", dinheiro(totalGasto)),
      elemento("td", "", ultimaCompra)
    );

    lista.append(tr);
  });
}

$("#btn-atualizar-clientes")?.addEventListener(
  "click",
  carregarClientes
);

$("#filtro-busca-cliente")?.addEventListener(
  "input",
  renderizarClientes
);

/* =========================
   BOTÕES GERAIS
========================= */

$("#btn-atualizar")?.addEventListener(
  "click",
  carregarPedidos
);

$("#btn-atualizar-produtos")?.addEventListener(
  "click",
  carregarProdutos
);

$("#btn-atualizar-categorias")?.addEventListener(
  "click",
  carregarCategorias
);

$("#btn-fechar")?.addEventListener("click", () => {
  if (dialogDetalhes?.open) {
    dialogDetalhes.close();
  }
});

$("#btn-imprimir")?.addEventListener("click", () => {
  window.print();
});

/* =========================
   INICIALIZAÇÃO
========================= */

verificarSessao();


