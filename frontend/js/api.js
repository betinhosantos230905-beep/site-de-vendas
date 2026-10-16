
/* =========================================================
   SALTY — Comunicação com a API do backend
   ========================================================= */

const SaltyAPI = (() => {
  /**
   * Realiza uma requisição ao backend.
   * Converte a resposta para JSON e trata possíveis erros.
   */
  async function request(path, options = {}) {
    const res = await fetch(`/api${path}`, options);

    const body = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(
        body.error ||
        `Erro ${res.status} ao comunicar com o servidor.`
      );
    }

    return body;
  }

  /**
   * Requisições GET.
   */
  function get(path) {
    return request(path);
  }

  /**
   * Requisições POST com envio de dados em JSON.
   */
  function post(path, data) {
    return request(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
  }

  /* =======================================================
     FUNÇÕES DISPONÍVEIS PARA O FRONTEND
     ======================================================= */

  return {
    // Categorias do cardápio.
    categories: () => get("/categories"),

    // Produtos disponíveis no cardápio.
    products: () => get("/products"),

    // Lista pública de cupons disponíveis para os clientes.
    coupons: () => get("/coupons"),

    // Busca a taxa de entrega configurada no banco de dados.
    deliverySettings: () => get("/configuracoes"),

    // Valida o cupom informado pelo cliente.
    validateCoupon: data => post("/coupons/validate", data),

    // Envia os dados para registrar um pedido.
    // O backend recalcula os preços, a taxa e o desconto.
    createOrder: data => post("/orders", data),
  };
})();
