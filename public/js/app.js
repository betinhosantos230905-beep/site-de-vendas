
/* Cardápio, detalhes do produto, carrinho, cupons e checkout. */

const brl = n => Number(n).toLocaleString("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function precoPromocional(p) {
  const promocional = Number(p.promo_price);
  const normal = Number(p.price);

  if (
    p.promo_price !== null &&
    p.promo_price !== undefined &&
    p.promo_price !== "" &&
    Number.isFinite(promocional) &&
    promocional > 0 &&
    promocional < normal
  ) {
    return promocional;
  }

  return null;
}

function precoAtual(p) {
  return precoPromocional(p) ?? Number(p.price);
}

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);

  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;

    if (k.startsWith("on")) {
      el.addEventListener(k.slice(2), v);
    } else if (k === "class") {
      el.className = v;
    } else if (k === "style") {
      el.style.cssText = v;
    } else {
      el.setAttribute(k, v === true ? "" : v);
    }
  }

  kids.flat().forEach(c => {
    el.append(c instanceof Node ? c : document.createTextNode(c ?? ""));
  });

  return el;
}

const $ = id => document.getElementById(id);

const state = {
  categories: [],
  products: [],
  coupons: [],
  deliveryFee: 7.00,
  active: "all",
  appliedCoupon: null,
  couponPhone: "",
  couponMessage: "",
  couponLoading: false,
  couponRequestId: 0,
};

let chavePedidoPendente = null;

/* ---------- Mensagens ---------- */

function toast(msg) {
  const t = $("toast");
  if (!t) return;

  t.textContent = msg;
  t.classList.add("show");

  clearTimeout(toast.t);
  toast.t = setTimeout(() => t.classList.remove("show"), 3000);
}

/* ---------- Cupons ---------- */

function codigoCupom(cupom) {
  return String(cupom?.codigo || cupom?.code || "")
    .trim()
    .toUpperCase();
}

function dadosListaCupons(resposta) {
  if (Array.isArray(resposta)) return resposta;
  if (Array.isArray(resposta?.data)) return resposta.data;
  if (Array.isArray(resposta?.cupons)) return resposta.cupons;
  if (Array.isArray(resposta?.coupons)) return resposta.coupons;

  return [];
}

function textoDescontoCupom(cupom) {
  const tipo = String(cupom?.tipo || cupom?.type || "").toLowerCase();
  const valor = Number(cupom?.valor ?? cupom?.value ?? 0);

  if (tipo.includes("percent") || tipo.includes("porcent")) {
    return `${valor}% de desconto`;
  }

  if (tipo.includes("fix") || tipo.includes("valor")) {
    return `${brl(valor)} de desconto`;
  }

  return "Consulte as condições do cupom";
}

function formatarValidadeCupom(data) {
  if (!data) return "";

  const texto = String(data);
  const correspondencia = texto.match(/^(\d{4})-(\d{2})-(\d{2})/);

  if (!correspondencia) {
    return `Válido até ${texto}`;
  }

  const [, ano, mes, dia] = correspondencia;

  return `Válido até ${dia}/${mes}/${ano}`;
}

/*
 * Cria uma faixa compacta de cupons.
 * O cliente pode tocar na faixa para abrir ou recolher a lista.
 */
function criarSecaoCupons() {
  let secao = $("coupons-section");

  if (secao) return secao;

  secao = h("section", {
    id: "coupons-section",
    class: "coupons-section",
    "aria-label": "Cupons disponíveis",
  });

  const lista = h("div", {
    id: "coupons-list",
    class: "coupons-list",
    hidden: true,
  });

  const abrir = h("button", {
    type: "button",
    class: "coupons-toggle",
    "aria-expanded": "false",
    "aria-controls": "coupons-list",

    onclick: () => {
      const aberta = abrir.getAttribute("aria-expanded") === "true";

      abrir.setAttribute("aria-expanded", String(!aberta));
      lista.hidden = aberta;
    },
  },
    h("span", {
      class: "coupons-toggle-icon",
      "aria-hidden": "true",
    }, "%"),

    h("span", { class: "coupons-toggle-text" },
      h("strong", {}, "Cupons disponíveis"),
      h("small", {}, "Toque para conferir seus descontos")
    ),

    h("span", {
      class: "coupons-toggle-arrow",
      "aria-hidden": "true",
    }, "⌄")
  );

  secao.append(abrir, lista);

  const search = document.querySelector(".search");
  const cats = $("cats")?.closest(".cats");

  if (search?.parentNode) {
    search.parentNode.insertBefore(secao, search.nextSibling);
  } else if (cats?.parentNode) {
    cats.parentNode.insertBefore(secao, cats);
  } else {
    document.body.insertBefore(secao, document.body.firstChild);
  }

  return secao;
}

function renderCoupons() {
  const secao = criarSecaoCupons();
  const lista = $("coupons-list");

  if (!lista) return;

  const cupons = state.coupons.filter(cupom => codigoCupom(cupom));

  if (!cupons.length) {
    secao.hidden = true;
    lista.replaceChildren();
    return;
  }

  secao.hidden = false;

  lista.replaceChildren(
    ...cupons.map(cupom => {
      const codigo = codigoCupom(cupom);

      const minimo = Number(
        cupom.pedido_minimo ??
        cupom.minimo_pedido ??
        0
      );

      const validade = formatarValidadeCupom(
        cupom.fim_em ?? cupom.valid_until ?? cupom.validade
      );

      const botao = h("button", {
        class: "btn ghost coupon-select",
        type: "button",

        onclick: () => {
          if (!SaltyCart.items.length) {
            toast("Adicione produtos ao carrinho para usar o cupom.");
            return;
          }

          openCart();

          const campo = $("coupon-code");

          if (campo) {
            campo.value = codigo;
            campo.focus();
          }

          const telefone = $("coupon-phone");

          if (telefone) {
            telefone.value = state.couponPhone;
          }

          toast(`Cupom ${codigo} selecionado. Informe seu telefone e aplique.`);
        },
      }, "Usar cupom");

      return h("article", { class: "coupon-card" },
        h("div", { class: "coupon-card-content" },
          h("strong", { class: "coupon-code" }, codigo),

          h("p", { class: "coupon-discount" },
            textoDescontoCupom(cupom)
          ),

          minimo > 0
            ? h("p", { class: "coupon-detail" },
                `Pedido mínimo: ${brl(minimo)}`
              )
            : null,

          validade
            ? h("p", { class: "coupon-detail" }, validade)
            : null
        ),

        botao
      );
    })
  );
}

async function carregarCupons() {
  try {
    const resposta = await SaltyAPI.coupons();

    state.coupons = dadosListaCupons(resposta);

    renderCoupons();
  } catch (erro) {
    console.warn("Não foi possível carregar os cupons:", erro);

    state.coupons = [];

    renderCoupons();
  }
}

/* ---------- Taxa de entrega ---------- */

async function carregarTaxaEntrega() {
  try {
    const resposta = await SaltyAPI.deliverySettings();
    const dados = resposta?.data || resposta;
    const taxa = Number(dados?.taxa_entrega_padrao);

    if (!Number.isFinite(taxa) || taxa < 0) {
      throw new Error("A taxa de entrega retornada é inválida.");
    }

    state.deliveryFee = taxa;
  } catch (erro) {
    console.warn(
      "Não foi possível carregar a taxa de entrega. Será usado o valor padrão de R$ 7,00:",
      erro
    );
  }
}

function limparCupom(mensagem = "") {
  state.appliedCoupon = null;
  state.couponMessage = mensagem;
}

function obterDesconto(resposta) {
  const dados = resposta?.data || resposta;

  return Number(
    dados?.desconto ??
    dados?.valor_desconto ??
    dados?.discount ??
    0
  );
}

function cupomFoiValidado(resposta) {
  const dados = resposta?.data || resposta;

  return (
    dados?.valid === true ||
    dados?.valido === true ||
    dados?.ok === true
  );
}

async function aplicarCupom() {
  if (state.couponLoading) return;

  const campoCodigo = $("coupon-code");
  const campoTelefone = $("coupon-phone");

  if (!campoCodigo || !campoTelefone) return;

  const codigo = campoCodigo.value.trim().toUpperCase();
  const telefone = campoTelefone.value.trim();
  const subtotal = SaltyCart.subtotal();

  if (!codigo) {
    limparCupom("Digite o código do cupom.");
    renderCart();
    return;
  }

  if (!telefone) {
    limparCupom("Informe seu telefone para validar o cupom.");
    renderCart();
    return;
  }

  if (!SaltyCart.items.length || subtotal <= 0) {
    limparCupom("Adicione produtos ao carrinho primeiro.");
    renderCart();
    return;
  }

  const requisicaoAtual = ++state.couponRequestId;

  state.couponPhone = telefone;
  state.couponLoading = true;
  state.couponMessage = "Validando cupom...";

  renderCart();

  try {
    const resposta = await SaltyAPI.validateCoupon({
      cupom_codigo: codigo,
      telefone,
      subtotal,
    });

    if (requisicaoAtual !== state.couponRequestId) return;

    const subtotalAtual = SaltyCart.subtotal();

    if (Math.abs(subtotalAtual - subtotal) > 0.001) {
      limparCupom("O carrinho mudou. Aplique o cupom novamente.");
      renderCart();
      return;
    }

    if (!cupomFoiValidado(resposta)) {
      const dados = resposta?.data || resposta;

      limparCupom(
        dados?.error ||
        dados?.mensagem ||
        "Este cupom não é válido para o seu pedido."
      );

      renderCart();
      return;
    }

    const desconto = obterDesconto(resposta);

    if (!Number.isFinite(desconto) || desconto <= 0) {
      limparCupom("O servidor não retornou um desconto válido.");
      renderCart();
      return;
    }

    const dados = resposta?.data || resposta;
    const cupomResposta = dados?.coupon || dados?.cupom || {};

    state.appliedCoupon = {
      codigo: codigoCupom(cupomResposta) || codigo,
      desconto: Math.min(desconto, subtotal),
      subtotalValidado: subtotal,
      telefone,
    };

    state.couponMessage =
      `Cupom aplicado! Você economiza ${brl(state.appliedCoupon.desconto)}.`;

    renderCart();

    toast("Cupom aplicado com sucesso!");
  } catch (erro) {
    if (requisicaoAtual !== state.couponRequestId) return;

    limparCupom(
      erro.message || "Não foi possível validar o cupom."
    );

    renderCart();
  } finally {
    if (requisicaoAtual === state.couponRequestId) {
      state.couponLoading = false;

      const botao = $("apply-coupon");

      if (botao) {
        botao.disabled = false;
        botao.textContent = "Aplicar cupom";
      }

      if ($("cart-dialog")?.open) {
        renderCart();
      }
    }
  }
}

/* ---------- Categorias e lista ---------- */

function renderCats() {
  const mk = (id, label) => h("button", {
    class: "chip",
    type: "button",
    "aria-pressed": String(state.active === id),

    onclick: () => {
      state.active = id;

      renderCats();
      renderMenu();

      window.scrollTo({ top: 0 });
    },
  }, label);

  $("cats").replaceChildren(
    mk("all", "Todos"),
    ...state.categories.map(c => mk(c.id, c.name))
  );
}

function productCard(p, cat) {
  const promocional = precoPromocional(p);

  const temOpcoesComPreco = (p.option_groups || []).some(
    g => g.min > 0 && g.options.some(o => o.price > 0)
  );

  const prefixo = temOpcoesComPreco ? "a partir de " : "";

  const preco = promocional !== null
    ? h("span", { class: "price" },
        prefixo,
        h("del", { class: "price-original" }, brl(p.price)),
        h("strong", { class: "price-promo" }, brl(promocional))
      )
    : h("span", { class: "price" },
        prefixo + brl(p.price)
      );

  return h("button", {
    class: "card",
    type: "button",
    disabled: !p.available,
    onclick: () => openProduct(p),
  },
   
    h("div", {
      class: `thumb${p.image_url ? " has-image" : ""}`,
      "aria-hidden": "true",
      style: `background:${cat.tone}`,
    },
      p.image_url
        ? h("img", {
            src: p.image_url,
            alt: "",
            loading: "lazy",
            onerror: (evento) => {
              const imagem = evento.currentTarget;
              imagem.remove();
              imagem.parentElement?.classList.remove("has-image");
              if (imagem.parentElement) {
                imagem.parentElement.textContent = cat.emoji;
              }
            },
          })
        : cat.emoji
    ),


    h("div", { class: "card-body" },
      h("span", { class: "card-name" }, p.name),
      h("span", { class: "card-desc" }, p.description),

      h("span", { class: "card-foot" },
        preco,

        p.featured && p.available
          ? h("span", { class: "tag" }, "Destaque")
          : null,

        promocional !== null
          ? h("span", { class: "tag" }, "Promoção")
          : null,

        !p.available
          ? h("span", { class: "tag off" }, "Indisponível")
          : null
      )
    )
  );
}

function renderMenu() {
  const cats = state.categories.filter(
    c => state.active === "all" || c.id === state.active
  );

  const nodes = [];

  for (const c of cats) {
    const list = state.products.filter(p => p.category_id === c.id);

    if (!list.length) continue;

    nodes.push(
      h("h2", {}, c.name),
      h("div", { class: "grid" },
        list.map(p => productCard(p, c))
      )
    );
  }

  $("menu").replaceChildren(
    ...(nodes.length
      ? nodes
      : [
          h("p", { class: "state" },
            "Nenhum produto nesta categoria no momento."
          ),
        ]
    )
  );
}

/* ---------- Detalhes e personalização ---------- */

function openProduct(p) {
  const dlg = $("product-dialog");
  let qty = 1;

  const promocional = precoPromocional(p);
  const basePrice = precoAtual(p);
  const grupos = p.option_groups || [];

  const chosen = new Map(
    grupos.map(g => [g.id, new Set()])
  );

  const price = h("strong", { class: "price-promo" });

  const originalPrice = h("del", {
    class: "price-original",
    hidden: promocional === null,
  });

  const addBtn = h("button", {
    class: "btn",
    type: "button",
  });

  const qtyOut = h("output", {}, "1");

  const note = h("textarea", {
    id: "pd-note",
    maxlength: "140",
    placeholder: "Ex.: sem cebola",
  });

  const groupEls = new Map();

  const totalAdicionais = () =>
    grupos.reduce(
      (s, g) =>
        s + g.options
          .filter(o => chosen.get(g.id).has(o.id))
          .reduce((a, o) => a + o.price, 0),
      0
    );

  const unit = () => basePrice + totalAdicionais();
  const unitOriginal = () => Number(p.price) + totalAdicionais();

  const missing = () =>
    grupos.filter(g => chosen.get(g.id).size < g.min);

  function refresh(showErrors = false) {
    price.textContent = brl(unit() * qty);
    originalPrice.textContent = brl(unitOriginal() * qty);
    originalPrice.hidden = promocional === null;
    qtyOut.textContent = qty;

    const miss = missing();

    addBtn.disabled = miss.length > 0;
    addBtn.textContent = miss.length
      ? `Escolha: ${miss[0].name.toLowerCase()}`
      : "Adicionar ao carrinho";

    grupos.forEach(g => {
      const set = chosen.get(g.id);
      const group = groupEls.get(g.id);

      group.classList.toggle(
        "invalid",
        showErrors && set.size < g.min
      );

      group.querySelectorAll("input").forEach(inp => {
        const full =
          g.max > 1 && set.size >= g.max && !inp.checked;

        inp.disabled = full;
        inp.closest(".opt").classList.toggle("is-off", full);
      });
    });
  }

  const groups = grupos.map(g => {
    const single = g.max === 1;

    const rule = g.min > 0
      ? (
          single
            ? "Obrigatório: escolha 1"
            : `Obrigatório: escolha de ${g.min} a ${g.max}`
        )
      : `Opcional: até ${g.max}`;

    const fs = h("fieldset", { class: "group" },
      h("legend", {}, g.name),
      h("p", { class: "rule" }, rule),

      g.options.map(o => {
        const inp = h("input", {
          type: single ? "radio" : "checkbox",
          name: `grupo-${p.id}-${g.id}`,
          value: o.id,

          onchange: e => {
            const set = chosen.get(g.id);

            if (single) {
              set.clear();
              set.add(o.id);
            } else if (e.target.checked) {
              set.add(o.id);
            } else {
              set.delete(o.id);
            }

            refresh();
          },
        });

        return h("label", { class: "opt" },
          inp,
          h("span", {}, o.name),
          h("span", {},
            o.price ? `+ ${brl(o.price)}` : "incluso"
          )
        );
      })
    );

    groupEls.set(g.id, fs);

    return fs;
  });

  const step = d => () => {
    qty = Math.min(99, Math.max(1, qty + d));
    refresh();
  };

  addBtn.addEventListener("click", () => {
    if (missing().length) return refresh(true);

    const options = grupos.flatMap(g =>
      g.options
        .filter(o => chosen.get(g.id).has(o.id))
        .map(o => ({
          id: o.id,
          group: g.name,
          name: o.name,
          price: o.price,
        }))
    );

    SaltyCart.add({
      productId: p.id,
      name: p.name,
      basePrice,
      options,
      note: note.value,
      qty,
    });

    dlg.close();
    toast(`${p.name} adicionado ao carrinho`);
  });

  dlg.replaceChildren(
    h("div", { class: "sheet-head" },
      h("div", {},
        h("h3", { id: "pd-title" }, p.name),

        h("p", {},
          (p.description || "") +
          (p.prep_minutes
            ? ` Preparo: cerca de ${p.prep_minutes} min.`
            : "")
        )
      ),

      h("button", {
        class: "close",
        type: "button",
        "aria-label": "Fechar",
        onclick: () => dlg.close(),
      }, "×")
    ),

    h("div", { class: "sheet-body" },
      ...groups,

      h("label", { class: "lbl", for: "pd-note" },
        "Observações"
      ),

      note
    ),

    h("div", { class: "sheet-foot" },
      h("div", {
        class: "stepper",
        role: "group",
        "aria-label": "Quantidade",
      },
        h("button", {
          type: "button",
          "aria-label": "Diminuir",
          onclick: step(-1),
        }, "−"),

        qtyOut,

        h("button", {
          type: "button",
          "aria-label": "Aumentar",
          onclick: step(1),
        }, "+")
      ),

      addBtn,
      originalPrice,
      price
    )
  );

  refresh();
  dlg.showModal();
}

/* ---------- Carrinho ---------- */

function invalidarCupomSeNecessario() {
  if (!state.appliedCoupon) return;

  const subtotal = SaltyCart.subtotal();

  if (
    Math.abs(state.appliedCoupon.subtotalValidado - subtotal) > 0.001
  ) {
    limparCupom("O carrinho mudou. Aplique o cupom novamente.");
  }
}

function openCart() {
  const dlg = $("cart-dialog");

  renderCart();

  if (!dlg.open) dlg.showModal();
}

function renderCart() {
  const dlg = $("cart-dialog");
  const items = SaltyCart.items;

  const head = h("div", { class: "sheet-head" },
    h("h3", { id: "cart-title" }, "Seu carrinho"),

    h("button", {
      class: "close",
      type: "button",
      "aria-label": "Fechar carrinho",
      onclick: () => dlg.close(),
    }, "×")
  );

  if (!items.length) {
    limparCupom();

    dlg.replaceChildren(
      head,

      h("div", { class: "sheet-body" },
        h("p", { class: "state" },
          "Seu carrinho está vazio. Escolha algo no cardápio."
        )
      ),

      h("div", { class: "sheet-foot" },
        h("button", {
          class: "btn",
          type: "button",
          onclick: () => dlg.close(),
        }, "Voltar ao cardápio")
      )
    );

    return;
  }

  const subtotal = SaltyCart.subtotal();

  invalidarCupomSeNecessario();

  const lines = items.map(i =>
    h("div", { class: "line" },
      h("div", { class: "line-main" },
        h("strong", {}, i.name),

        i.options.length
          ? h("small", {},
              i.options.map(o => o.name).join(", ")
            )
          : null,

        i.note ? h("small", {}, `Obs.: ${i.note}`) : null,

        h("small", {}, `${brl(i.unitPrice)} cada`)
      ),

      h("div", { class: "line-side" },
        h("strong", {}, brl(i.unitPrice * i.qty)),

        h("div", { class: "stepper" },
          h("button", {
            type: "button",
            "aria-label": `Diminuir ${i.name}`,
            onclick: () => SaltyCart.setQty(i.key, i.qty - 1),
          }, "−"),

          h("output", {}, i.qty),

          h("button", {
            type: "button",
            "aria-label": `Aumentar ${i.name}`,
            onclick: () => SaltyCart.setQty(i.key, i.qty + 1),
          }, "+")
        ),

        h("button", {
          class: "link",
          type: "button",
          onclick: () => SaltyCart.remove(i.key),
        }, "Remover")
      )
    )
  );

  const campoCupom = h("input", {
    id: "coupon-code",
    type: "text",
    placeholder: "Digite o código do cupom",
    autocomplete: "off",
    maxlength: "80",
    value: state.appliedCoupon?.codigo || "",
  });

  campoCupom.addEventListener("input", () => {
    if (state.appliedCoupon) {
      limparCupom("O código mudou. Aplique o cupom novamente.");
    }

    campoCupom.value = campoCupom.value.toUpperCase();
  });

  const campoTelefone = h("input", {
    id: "coupon-phone",
    type: "tel",
    placeholder: "DDD + telefone",
    autocomplete: "tel",
    maxlength: "25",
    value: state.couponPhone,
  });

  campoTelefone.addEventListener("input", () => {
    if (state.appliedCoupon) {
      limparCupom("O telefone mudou. Aplique o cupom novamente.");
    }

    state.couponPhone = campoTelefone.value;
  });

  const botaoCupom = h("button", {
    id: "apply-coupon",
    class: "btn ghost",
    type: "button",
    disabled: state.couponLoading,
    onclick: aplicarCupom,
  }, state.couponLoading ? "Validando..." : "Aplicar cupom");

  const mensagemCupom = h("p", {
    class: "coupon-message",
    role: "status",
    "aria-live": "polite",
  }, state.couponMessage);

  const desconto = state.appliedCoupon?.desconto || 0;
  const taxaEntrega = state.deliveryFee;

  const totalComDesconto = Math.max(
    0,
    subtotal - desconto + taxaEntrega
  );

  const totais = h("div", { class: "totals" },
    h("div", {},
      h("span", {}, "Subtotal"),
      h("span", {}, brl(subtotal))
    ),

    state.appliedCoupon
      ? h("div", { class: "coupon-total" },
          h("span", {}, `Cupom ${state.appliedCoupon.codigo}`),
          h("span", {}, `− ${brl(desconto)}`)
        )
      : null,

    h("div", {},
      h("span", {}, "Taxa de entrega"),
      h("span", {}, brl(taxaEntrega))
    ),

    h("div", { class: "grand" },
      h("span", {}, "Total estimado para entrega"),
      h("span", {}, brl(totalComDesconto))
    )
  );

  dlg.replaceChildren(
    head,

    h("div", { class: "sheet-body" },
      ...lines,

      h("section", {
        class: "coupon-box",
        "aria-label": "Aplicar cupom de desconto",
      },
        h("h4", {}, "Tem um cupom de desconto?"),

        h("p", { class: "hint" },
          "Informe o código e o telefone usado no pedido."
        ),

        h("label", { class: "lbl", for: "coupon-code" },
          "Código do cupom",
          campoCupom
        ),

        h("label", { class: "lbl", for: "coupon-phone" },
          "Seu telefone",
          campoTelefone
        ),

        botaoCupom,
        mensagemCupom
      ),

      totais,

      h("p", { class: "hint" },
        "O total exibido considera a taxa de entrega padrão. A taxa e o desconto serão conferidos pelo servidor ao registrar o pedido."
      )
    ),

    h("div", { class: "sheet-foot" },
      h("button", {
        class: "btn ghost",
        type: "button",
        onclick: () => dlg.close(),
      }, "Voltar ao cardápio"),

      h("button", {
        class: "btn",
        type: "button",
        onclick: abrirCheckout,
      }, "Finalizar pedido")
    )
  );
}

/* ---------- Campos do checkout ---------- */

function criarCampoCheckout(id, texto, tipo = "text", obrigatorio = true) {
  const input = h("input", {
    id,
    name: id,
    type: tipo,
    required: obrigatorio,
    maxlength: id === "checkout-cep" ? 9 : 150,
    autocomplete: ({
      "checkout-nome": "name",
      "checkout-telefone": "tel",
      "checkout-cep": "postal-code",
      "checkout-rua": "street-address",
    })[id] || "off",
  });

  const label = h("label", { class: "lbl", for: id },
    texto,
    input
  );

  return { input, label };
}

function criarChavePedido() {
  if (
    window.crypto &&
    typeof window.crypto.randomUUID === "function"
  ) {
    return window.crypto.randomUUID();
  }

  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;

    return (
      c === "x"
        ? r
        : (r & 3 | 8)
    ).toString(16);
  });
}

/* ---------- Checkout ---------- */

function abrirCheckout() {
  if (!SaltyCart.items.length) {
    toast("Adicione produtos antes de finalizar.");
    return;
  }

  invalidarCupomSeNecessario();

  const dlg = $("checkout-dialog");

    chavePedidoPendente ||= criarChavePedido();

  const nome = criarCampoCheckout(
    "checkout-nome", "Seu nome"
  );

  const telefone = criarCampoCheckout(
    "checkout-telefone", "Telefone", "tel"
  );

  telefone.input.value = state.couponPhone || "";

  const email = criarCampoCheckout(
    "checkout-email", "Seu e-mail", "email"
  );

  email.input.autocomplete = "email";

  const modalidade = h("select", {
    id: "checkout-modalidade",
    name: "modalidade",
    required: true,
  },
    h("option", { value: "entrega" }, "Entrega"),
    h("option", { value: "retirada" }, "Retirada no local")
  );

  const modalidadeLabel = h("label", {
    class: "lbl",
    for: "checkout-modalidade",
  }, "Como deseja receber?", modalidade);

  const cep = criarCampoCheckout("checkout-cep", "CEP");
  const rua = criarCampoCheckout("checkout-rua", "Rua");
  const numero = criarCampoCheckout("checkout-numero", "Número");

  const complemento = criarCampoCheckout(
    "checkout-complemento", "Complemento (opcional)", "text", false
  );

  const bairro = criarCampoCheckout("checkout-bairro", "Bairro");
  const cidade = criarCampoCheckout("checkout-cidade", "Cidade");
  const uf = criarCampoCheckout("checkout-uf", "Estado (UF)");

  const referencia = criarCampoCheckout(
    "checkout-referencia", "Ponto de referência (opcional)", "text", false
  );

  uf.input.maxLength = 2;
  uf.input.autocomplete = "address-level1";

  const endereco = h("div", { class: "checkout-address" },
    h("h4", {}, "Endereço de entrega"),
    cep.label,
    rua.label,
    numero.label,
    complemento.label,
    bairro.label,
    cidade.label,
    uf.label,
    referencia.label
  );

  const pagamento = h("select", {
    id: "checkout-pagamento",
    name: "pagamento",
    required: true,
  },
    h("option", { value: "pix" }, "Pix"),
    h("option", { value: "dinheiro" }, "Dinheiro"),
    h("option", { value: "cartao_entrega" }, "Cartão na entrega")
  );

  const pagamentoLabel = h("label", {
    class: "lbl",
    for: "checkout-pagamento",
  }, "Forma de pagamento", pagamento);

  const troco = criarCampoCheckout(
    "checkout-troco", "Troco para quanto? (opcional)", "number", false
  );

  troco.input.min = "0.01";
  troco.input.step = "0.01";

  const observacoes = h("textarea", {
    id: "checkout-observacoes",
    name: "observacoes",
    maxlength: "300",
    placeholder: "Alguma observação para o pedido?",
  });

  const observacoesLabel = h("label", {
    class: "lbl",
    for: "checkout-observacoes",
  }, "Observações", observacoes);

  const mensagem = h("p", {
    class: "hint",
    role: "status",
    "aria-live": "polite",
  });

  const enviar = h("button", {
    class: "btn",
    type: "submit",
  }, "Confirmar pedido");

  /* ---------- Totais atualizados no checkout ---------- */

  const subtotalCheckout = SaltyCart.subtotal();
  const descontoCheckout = state.appliedCoupon?.desconto || 0;

  const taxaCheckoutValor = h("strong", {}, "");
  const totalCheckoutValor = h("strong", {}, "");

  const taxaCheckout = () =>
    modalidade.value === "entrega" ? state.deliveryFee : 0;

  const totalCheckout = () =>
    Math.max(
      0,
      subtotalCheckout - descontoCheckout + taxaCheckout()
    );

  const atualizarTotaisCheckout = () => {
    taxaCheckoutValor.textContent = brl(taxaCheckout());
    totalCheckoutValor.textContent = brl(totalCheckout());
  };

  const formulario = h("form", {
    class: "sheet-body",

    onsubmit: async event => {
      event.preventDefault();

      if (!formulario.reportValidity()) return;

      enviar.disabled = true;
      enviar.textContent = "Enviando pedido...";
      mensagem.textContent = "";

      const tipoEntrega = modalidade.value;
      const valorTroco = troco.input.value;
      const telefoneCliente = telefone.input.value.trim();

      const subtotalPedido = SaltyCart.subtotal();

      const cupomAplicado =
        state.appliedCoupon &&
        state.appliedCoupon.telefone === telefoneCliente &&
        Math.abs(
          state.appliedCoupon.subtotalValidado - subtotalPedido
        ) < 0.001
          ? state.appliedCoupon.codigo
          : "";

      const dados = {
        chave_idempotencia: chavePedidoPendente,
        nome: nome.input.value.trim(),
        telefone: telefoneCliente,
        email: email.input.value.trim(),
        modalidade: tipoEntrega,
        pagamento: pagamento.value,

        troco_para:
          pagamento.value === "dinheiro" && valorTroco
            ? valorTroco
            : null,

        observacoes: observacoes.value.trim(),

        endereco: tipoEntrega === "entrega"
          ? {
              cep: cep.input.value,
              rua: rua.input.value.trim(),
              numero: numero.input.value.trim(),
              complemento: complemento.input.value.trim(),
              bairro: bairro.input.value.trim(),
              cidade: cidade.input.value.trim(),
              uf: uf.input.value.trim().toUpperCase(),
              referencia: referencia.input.value.trim(),
            }
          : {},

        cupom_codigo: cupomAplicado,

        itens: SaltyCart.items.map(item => ({
          produto_id: item.productId,
          quantidade: item.qty,
          opcoes: item.options.map(option => option.id),
          observacao: item.note || "",
        })),
      };

      try {
        const resposta = await SaltyAPI.createOrder(dados);
        const pedido = resposta.pedido;

        if (!pedido || !pedido.numero) {
          throw new Error(
            "O servidor não retornou a confirmação do pedido."
          );
        }

        SaltyCart.clear();
        chavePedidoPendente = null;

        limparCupom();
        state.couponPhone = "";

        dlg.replaceChildren(
          h("div", { class: "sheet-head" },
            h("h3", {}, "Pedido recebido!"),

            h("button", {
              class: "close",
              type: "button",
              "aria-label": "Fechar",
              onclick: () => dlg.close(),
            }, "×")
          ),

          h("div", { class: "sheet-body" },
            h("p", {}, "Seu pedido foi registrado com sucesso."),
            h("p", {}, `Número do pedido: ${pedido.numero}`),
            h("p", {}, `Total: ${brl(pedido.total)}`),
            h("p", {}, "Guarde o número para consultar seu pedido.")
          ),

          h("div", { class: "sheet-foot" },
            h("button", {
              class: "btn",
              type: "button",
              onclick: () => dlg.close(),
            }, "Voltar ao cardápio")
          )
        );

        toast("Pedido registrado com sucesso!");
      } catch (erro) {
        mensagem.textContent =
          erro.message ||
          "Não foi possível registrar o pedido. Tente novamente.";

        enviar.disabled = false;
        enviar.textContent = "Tentar novamente";
      }
    },
  },
    nome.label,
    telefone.label,
    email.label,
    modalidadeLabel,
    endereco,
    pagamentoLabel,
    troco.label,
    observacoesLabel,

    h("div", { class: "totals" },
      h("div", {},
        h("span", {}, "Subtotal dos produtos"),
        h("strong", {}, brl(subtotalCheckout))
      ),

      state.appliedCoupon
        ? h("div", { class: "coupon-total" },
            h("span", {}, `Cupom ${state.appliedCoupon.codigo}`),
            h("strong", {}, `− ${brl(descontoCheckout)}`)
          )
        : null,

      h("div", {},
        h("span", {}, "Taxa de entrega"),
        taxaCheckoutValor
      ),

      h("div", { class: "grand" },
        h("span", {}, "Total estimado"),
        totalCheckoutValor
      )
    ),

    mensagem,

    h("div", { class: "sheet-foot" }, enviar)
  );

  const atualizarEndereco = () => {
    const entregaSelecionada = modalidade.value === "entrega";

    endereco.hidden = !entregaSelecionada;

    [
      cep.input,
      rua.input,
      numero.input,
      bairro.input,
      cidade.input,
      uf.input,
    ].forEach(input => {
      input.required = entregaSelecionada;
    });
  };

    const atualizarTroco = () => {
    troco.label.hidden = pagamento.value !== "dinheiro";
    email.input.required = pagamento.value === "pix";
    };
  modalidade.addEventListener("change", () => {
    atualizarEndereco();
    atualizarTotaisCheckout();
  });

  pagamento.addEventListener("change", atualizarTroco);

  atualizarEndereco();
  atualizarTroco();
  atualizarTotaisCheckout();

  dlg.replaceChildren(
    h("div", { class: "sheet-head" },
      h("h3", { id: "checkout-title" }, "Finalizar pedido"),

      h("button", {
        class: "close",
        type: "button",
        "aria-label": "Fechar checkout",
        onclick: () => dlg.close(),
      }, "×")
    ),

    formulario
  );

  if ($("cart-dialog").open) {
    $("cart-dialog").close();
  }

  if (!dlg.open) dlg.showModal();
}

/* ---------- Indicador do carrinho ---------- */

function updateBadge() {
  const n = SaltyCart.count();

  $("cart-count").textContent = n;
  $("cart-count").hidden = n === 0;

  $("open-cart").setAttribute(
    "aria-label",
    `Abrir carrinho, ${n} ${n === 1 ? "item" : "itens"}`
  );

  if ($("cart-dialog").open) {
    renderCart();
  }
}

/* ---------- Início ---------- */

async function init() {
  $("open-cart").addEventListener("click", openCart);

  const checkoutDialog = h("dialog", {
    id: "checkout-dialog",
    class: "sheet",
    "aria-labelledby": "checkout-title",
  });

  document.body.append(checkoutDialog);

  SaltyCart.onChange(updateBadge);

  for (const id of ["product-dialog", "cart-dialog", "checkout-dialog"]) {
    $(id).addEventListener("click", event => {
      if (event.target === event.currentTarget) {
        event.currentTarget.close();
      }
    });
  }

  try {
    const [cats, prods] = await Promise.all([
      SaltyAPI.categories(),
      SaltyAPI.products(),
    ]);

    state.categories = cats.data;
    state.products = prods.data;

    $("demo-note").hidden = !(cats.demo || prods.demo);

    const removed = SaltyCart.reconcile(state.products);

    renderCats();
    renderMenu();
    updateBadge();

    // Falhas na taxa ou nos cupons não impedem o cardápio de abrir.
    await Promise.all([
      carregarCupons(),
      carregarTaxaEntrega(),
    ]);

    // Atualiza os valores caso o carrinho já esteja aberto.
    if ($("cart-dialog").open) {
      renderCart();
    }

    if (removed) {
      toast(
        "Alguns itens do carrinho não estão mais disponíveis e foram removidos."
      );
    }
  } catch (err) {
    console.error(err);

    $("menu").replaceChildren(
      h("p", { class: "state" },
        "Não foi possível carregar o cardápio. Verifique se o servidor Flask está rodando e recarregue a página."
      )
    );
  }
}

init();
