
/* Carrinho: estado + persistência local.
   O backend recalcula os valores ao registrar o pedido. */
const SaltyCart = (() => {
  const KEY = "salty.cart.v1";
  let items = [];
  const listeners = [];

  try {
    items = JSON.parse(localStorage.getItem(KEY)) || [];

    if (!Array.isArray(items)) {
      items = [];
    }
  } catch {
    items = [];
  }

  const save = () => {
    try {
      localStorage.setItem(KEY, JSON.stringify(items));
    } catch {
      /* Armazenamento local indisponível. */
    }

    listeners.forEach(fn => fn());
  };

  // A mesma combinação de produto, opções e observação
  // representa a mesma linha do carrinho.
  const keyOf = (productId, optionIds, note) =>
    `${productId}|${[...optionIds].sort().join(",")}|${note.trim().toLowerCase()}`;

  return {
    onChange: fn => listeners.push(fn),

    get items() {
      return items;
    },

    count: () => items.reduce((total, item) => total + item.qty, 0),

    subtotal: () =>
      items.reduce((total, item) => total + item.unitPrice * item.qty, 0),

    add({ productId, name, basePrice, options, note, qty }) {
      const observacao = (note || "").trim();
      const opcoes = Array.isArray(options) ? options : [];

      const unitPrice =
        basePrice + opcoes.reduce((total, option) => total + option.price, 0);

      const key = keyOf(
        productId,
        opcoes.map(option => option.id),
        observacao
      );

      const found = items.find(item => item.key === key);

      if (found) {
        found.qty = Math.min(found.qty + qty, 99);
      } else {
        items.push({
          key,
          productId,
          name,
          unitPrice,
          options: opcoes,
          note: observacao,
          qty: Math.min(qty, 99),
        });
      }

      save();
    },

    setQty(key, qty) {
      const item = items.find(item => item.key === key);

      if (!item) return;

      if (qty <= 0) {
        items = items.filter(item => item.key !== key);
      } else {
        item.qty = Math.min(qty, 99);
      }

      save();
    },

    remove(key) {
      items = items.filter(item => item.key !== key);
      save();
    },

    // Limpa o carrinho após a confirmação do pedido.
    clear() {
      items = [];
      save();
    },

    // Remove produtos que desapareceram ou ficaram indisponíveis.
    reconcile(products) {
      const disponiveis = new Set(
        products.filter(product => product.available).map(product => product.id)
      );

      const quantidadeAnterior = items.length;

      items = items.filter(item => disponiveis.has(item.productId));

      if (items.length !== quantidadeAnterior) {
        save();
      }

      return quantidadeAnterior - items.length;
    },
  };
})();
