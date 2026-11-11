const DEMO_PRODUCTS = [
  {
    id: 5,
    name: "Luminária LED para Monitor",
    short: "Iluminação funcional para a mesa",
    price: 262.9,
    stock: 26,
    category: "ACESSÓRIOS",
    description: "Ilumine sua área de trabalho sem ocupar espaço na mesa.",
    image: "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 6,
    name: "Microfone USB",
    short: "Voz clara nas gravações",
    price: 408.9,
    stock: 5,
    category: "ÁUDIO",
    description: "Captação de voz clara para chamadas, gravações e transmissões.",
    image: "https://images.unsplash.com/photo-1599669454699-248893623440?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 7,
    name: "Webcam Full HD",
    short: "Imagem nítida para chamadas",
    price: 300.9,
    stock: 16,
    category: "IMAGEM",
    description: "Imagem em alta definição para reuniões, aulas e transmissões.",
    image: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 8,
    name: "SSD Externo",
    short: "Armazenamento portátil",
    price: 231.9,
    stock: 3,
    category: "ACESSÓRIOS",
    description: "Leve seus arquivos e projetos com você com praticidade.",
    image: "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 9,
    name: "Base Refrigerada para Notebook",
    short: "Mais ventilação para o notebook",
    price: 112.9,
    stock: 9,
    category: "SETUP",
    description: "Ajuda a manter o notebook ventilado durante o uso diário.",
    image: "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 10,
    name: "Controle Sem Fio",
    short: "Conforto para jogar",
    price: 268.9,
    stock: 19,
    category: "SETUP",
    description: "Mais liberdade e conforto para jogar no computador.",
    image: "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 11,
    name: "Cadeira Ergonômica",
    short: "Conforto para longas sessões",
    price: 653.9,
    stock: 20,
    category: "SETUP",
    description: "Uma opção confortável para o escritório ou espaço de jogos.",
    image: "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: 12,
    name: "Teclado Sem Fio",
    short: "Liberdade para organizar o setup",
    price: 200.9,
    stock: 25,
    category: "SETUP",
    description: "Um teclado prático para manter a mesa organizada.",
    image: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80",
  },
];

let PRODUCTS = DEMO_PRODUCTS;

const STORAGE_KEY = "nord-store-demo";
const AVAILABLE_THEMES = ["light", "dark", "purple", "night-owl"];
const money = (value) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
let cepLookupController = null;
const readState = () => {
  try {
    return { cart: [], coupon: "", cep: "", user: null, registeredUser: null, theme: "dark", pendingPayment: null, completedOrder: null, demoOrder: null, checkoutKey: null, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
  } catch {
    return { cart: [], coupon: "", cep: "", user: null, registeredUser: null, theme: "dark", pendingPayment: null, completedOrder: null, demoOrder: null, checkoutKey: null };
  }
};
let state = readState();
state.user = null;
state.registeredUser = null;
state.theme = "dark";
let paymentPollTimer = null;
let pendingProfilePhoto = null;
let paymentMode = "demo";
let catalogoCarregado = false;
let erroCatalogo = "";
let authChecked = false;
let authError = "";
let checkoutConfigCarregada = false;
let erroCheckoutConfig = "";
let reconexaoEmAndamento = false;
function applyTheme() {
  if (!AVAILABLE_THEMES.includes(state.theme)) state.theme = "dark";
  document.body.dataset.theme = state.theme;
  document.querySelectorAll("[data-theme-choice]").forEach((choice) => {
    choice.checked = choice.value === state.theme;
  });
}
applyTheme();
const saveState = () => {
  const persistedState = { ...state };
  delete persistedState.user;
  delete persistedState.registeredUser;
  delete persistedState.theme;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(persistedState));
  applyTheme();
  updateCartCounts();
};
const findProduct = (id) => PRODUCTS.find((product) => product.id === Number(id));
const cartQuantity = () => state.cart.reduce((total, item) => total + item.quantity, 0);
function reconcileCartWithCatalog() {
  const quantities = new Map();
  if (Array.isArray(state.cart)) {
    state.cart.forEach((item) => {
      if (!item || typeof item !== "object" || typeof item.quantity === "boolean") return;
      const productId = Number(item.id);
      const quantity = Number(item.quantity);
      const product = Number.isInteger(productId) ? findProduct(productId) : null;
      if (!product || !Number.isInteger(quantity) || quantity <= 0 || product.stock <= 0) return;
      quantities.set(productId, Math.min(product.stock, (quantities.get(productId) || 0) + quantity));
    });
  }

  const cart = [...quantities].map(([id, quantity]) => ({ id, quantity }));
  if (JSON.stringify(cart) !== JSON.stringify(state.cart)) {
    state.cart = cart;
    saveState();
  }
}
const subtotal = () => state.cart.reduce((total, item) => total + (findProduct(item.id)?.price || 0) * item.quantity, 0);
const shippingPrice = () => {
  const cleanCep = state.cep.replace(/\D/g, "");
  return cleanCep.length === 8 ? (/^[01]/.test(cleanCep) ? 15 : 25) : 15;
};
const couponRate = () => ({ DESCONTO10: 0.1, DESCONTO20: 0.2 }[state.coupon] || 0);
const discountValue = () => subtotal() * couponRate();
const totalPrice = () => Math.max(0, subtotal() - discountValue() + shippingPrice());

function updateCartCounts() {
  document.querySelectorAll("[data-cart-count]").forEach((element) => { element.textContent = cartQuantity(); });
  updateAccountDisplay();
}

function updateAccountDisplay() {
  const user = state.user;
  if (!user?.name) {
    document.querySelectorAll("[data-account-link]").forEach((link) => {
      link.href = "login.html";
      link.classList.remove("account-link");
      link.removeAttribute("aria-label");
      link.textContent = "Entrar";
    });
    return;
  }

  const initials = user.name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toLocaleUpperCase("pt-BR");
  document.querySelectorAll("[data-account-link]").forEach((link) => {
    link.href = "account.html";
    link.classList.add("account-link");
    link.setAttribute("aria-label", `Conta de ${user.name}`);
    const avatar = user.photo
      ? `<img src="${escapeHtml(user.photo)}" alt="" class="account-avatar">`
      : `<span class="account-avatar" aria-hidden="true">${escapeHtml(initials)}</span>`;
    link.innerHTML = `${avatar}<span class="account-copy"><strong>${escapeHtml(user.name)}</strong><small>Conta conectada</small></span>`;
  });
}

function showToast(message) {
  document.querySelector(".toast")?.remove();
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.setAttribute("role", "status");
  toast.textContent = message;
  document.body.append(toast);
  window.setTimeout(() => toast.remove(), 2600);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    throw new Error(data.message || "Não foi possível concluir a solicitação.");
  }
  return data;
}

async function carregarSessaoDaConta() {
  try {
    const data = await requestJson("/api/auth/me");
    state.user = data.user;
    state.registeredUser = null;
    state.theme = data.user?.theme || "dark";
    authError = "";
    authChecked = true;
    saveState();
    renderAccount();
    return true;
  } catch {
    authError = "Não foi possível verificar sua conta. Confira se o servidor está funcionando e tente novamente.";
    authChecked = true;
    renderAccount();
    const message = document.querySelector("[data-auth-message]");
    if (message) message.textContent = authError;
    return false;
  }
}

function addToCart(id, quantity = 1) {
  const product = findProduct(id);
  if (!product) return;
  const item = state.cart.find((entry) => entry.id === product.id);
  const currentQuantity = item?.quantity || 0;
  if (currentQuantity + quantity > product.stock) {
    showToast(`Estoque disponível: ${product.stock} unidade(s).`);
    return;
  }
  state.completedOrder = null;
  state.demoOrder = null;
  if (item) item.quantity += quantity;
  else state.cart.push({ id: product.id, quantity });
  saveState();
  showToast(`${product.short} adicionado à sacola.`);
}

function renderProducts(searchTerm = "") {
  const grid = document.querySelector("[data-product-grid]");
  if (!grid) return;
  if (!catalogoCarregado) {
    const message = erroCatalogo || "Conectando ao catálogo da loja...";
    grid.innerHTML = `<p class="search-empty" role="${erroCatalogo ? "alert" : "status"}">${escapeHtml(message)}${erroCatalogo ? ` <button class="button button-outline" type="button" data-retry-store>Conectar novamente</button>` : ""}</p>`;
    return;
  }
  const normalizedSearch = searchTerm.trim().toLocaleLowerCase("pt-BR");
  const matchingProducts = PRODUCTS.filter((product) => `${product.name} ${product.short} ${product.category}`.toLocaleLowerCase("pt-BR").includes(normalizedSearch));
  if (!matchingProducts.length) {
    grid.innerHTML = `<p class="search-empty">Nenhum produto encontrado.</p>`;
    return;
  }
  grid.innerHTML = matchingProducts.map((product, index) => `
    <article class="product-card" style="animation-delay:${index * 70}ms">
      <a class="product-image-wrap" href="produto.html?id=${product.id}" aria-label="Ver ${escapeHtml(product.name)}">
        <img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.name)}" loading="lazy">
        <span class="product-tag">${escapeHtml(product.category)}</span>
      </a>
      <div class="product-info"><div><h3><a href="produto.html?id=${product.id}">${escapeHtml(product.name)}</a></h3><p>${escapeHtml(product.short)}</p></div><span class="product-price">${money(product.price)}</span></div>
      <button class="product-add" type="button" data-add="${product.id}" aria-label="Adicionar ${escapeHtml(product.name)} à sacola">Adicionar à sacola</button>
    </article>`).join("");
}

function renderProductDetail() {
  const container = document.querySelector("[data-product-detail]");
  if (!container) return;
  if (!catalogoCarregado || !PRODUCTS.length) {
    container.innerHTML = `<p class="search-empty" role="status">${escapeHtml(erroCatalogo || "Carregando produto...")}</p>`;
    return;
  }
  const product = findProduct(new URLSearchParams(location.search).get("id")) || PRODUCTS[0];
  document.title = `${product.name} — NÓRD`;
  container.innerHTML = `
    <a class="back-link" href="index.html#catalogo">← Voltar à seleção</a>
    <section class="product-detail">
      <div class="product-detail-image"><img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.name)}"></div>
      <div class="product-detail-copy"><p class="eyebrow">${escapeHtml(product.category)} / NÓRD ESSENTIALS</p><h1>${escapeHtml(product.name)}</h1><p>${escapeHtml(product.short)}</p><p class="detail-price">${money(product.price)}</p><p class="detail-description">${escapeHtml(product.description)}</p><p class="stock-note">● ${product.stock} unidades disponíveis</p>
        <div class="detail-actions"><div class="quantity-control detail-quantity"><button type="button" data-detail-qty="-1" aria-label="Diminuir quantidade">−</button><span data-detail-quantity>1</span><button type="button" data-detail-qty="1" aria-label="Aumentar quantidade">+</button></div><button class="button button-dark" type="button" data-detail-add="${product.id}">Adicionar à sacola <span aria-hidden="true">↗</span></button></div>
      </div>
    </section>`;
}

function renderSummary(includeCheckout = false) {
  const checkoutMethod = includeCheckout
    ? document.querySelector('input[name="payment"]:checked')?.value || "PIX"
    : "";
  const pixDiscount = includeCheckout && checkoutMethod === "PIX" ? totalPrice() * 0.05 : 0;
  const finalTotal = totalPrice() - pixDiscount;
  const items = state.cart.map((item) => {
    const product = findProduct(item.id);
    return product ? `<div class="summary-item"><span>${escapeHtml(product.short)} × ${item.quantity}</span><strong>${money(product.price * item.quantity)}</strong></div>` : "";
  }).join("");
  return `<aside class="summary-panel ${includeCheckout ? "checkout-summary" : ""}">
    <h2>Resumo do pedido</h2>${includeCheckout ? items : ""}
    <div class="summary-line"><span>Subtotal</span><span>${money(subtotal())}</span></div>
    ${couponRate() ? `<div class="summary-line discount"><span>Desconto (${escapeHtml(state.coupon)})</span><span>− ${money(discountValue())}</span></div>` : ""}
    <div class="summary-line"><span>Frete estimado</span><span>${money(shippingPrice())}</span></div>
    ${includeCheckout ? `<div class="summary-line discount" data-pix-discount${pixDiscount ? "" : " hidden"}><span>Desconto PIX (5%)</span><span>− ${money(pixDiscount)}</span></div>` : ""}
    <div class="summary-line total"><span>Total</span><span data-checkout-total>${money(finalTotal)}</span></div>
    ${includeCheckout ? "" : `<form class="coupon-form" data-coupon-form><input name="coupon" value="${escapeHtml(state.coupon)}" placeholder="Cupom de desconto" aria-label="Cupom de desconto"><button type="submit">Aplicar</button></form><form class="shipping-form" data-shipping-form><label for="shipping-cep">Calcular frete pelo CEP</label><input id="shipping-cep" name="cep" inputmode="numeric" maxlength="9" placeholder="00000-000" value="${escapeHtml(state.cep)}" aria-label="CEP"></form>`}
    ${includeCheckout ? `<button class="button button-green" type="submit" form="checkout-form">Confirmar pedido <span aria-hidden="true">↗</span></button>` : `<a class="button button-green" href="checkout.html">Ir para pagamento <span aria-hidden="true">↗</span></a>`}
    <p class="summary-help">${includeCheckout ? (paymentMode === "demo" ? "Demonstração: nenhuma cobrança será feita." : "Pagamento processado com segurança pelo Mercado Pago.") : "Frete calculado com base no CEP informado."}</p>
  </aside>`;
}

function updateCheckoutTotal() {
  const total = document.querySelector("[data-checkout-total]");
  if (!total) return;
  const method = document.querySelector('input[name="payment"]:checked')?.value;
  const discount = method === "PIX" ? totalPrice() * 0.05 : 0;
  total.textContent = money(totalPrice() - discount);
  const discountRow = document.querySelector("[data-pix-discount]");
  if (discountRow) {
    discountRow.hidden = !discount;
    discountRow.lastElementChild.textContent = `− ${money(discount)}`;
  }
}

function renderCart() {
  const container = document.querySelector("[data-cart-page]");
  if (!container) return;
  if (!catalogoCarregado) {
    const message = erroCatalogo || "Conectando à loja...";
    container.innerHTML = `<section class="empty-state"><p role="${erroCatalogo ? "alert" : "status"}">${escapeHtml(message)}</p>${erroCatalogo ? `<button class="button button-dark" type="button" data-retry-store>Conectar novamente</button>` : ""}</section>`;
    return;
  }
  if (!state.cart.length) {
    container.innerHTML = `<section class="empty-state"><h2>Sua sacola está esperando.</h2><p>Adicione um essencial para começar.</p><a class="button button-dark" href="index.html#catalogo">Explorar produtos <span aria-hidden="true">↗</span></a></section>`;
    return;
  }
  const rows = state.cart.map((item) => {
    const product = findProduct(item.id);
    if (!product) return "";
    return `<article class="cart-row"><img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.name)}" loading="lazy"><div><h2>${escapeHtml(product.name)}</h2><p>${money(product.price)} cada</p><div class="quantity-control"><button type="button" data-cart-qty="${product.id}" data-delta="-1" aria-label="Diminuir quantidade">−</button><span>${item.quantity}</span><button type="button" data-cart-qty="${product.id}" data-delta="1" aria-label="Aumentar quantidade">+</button></div><button class="remove-item" type="button" data-remove="${product.id}">Remover</button></div><span class="cart-row-price">${money(product.price * item.quantity)}</span></article>`;
  }).join("");
  container.innerHTML = `<section class="cart-items" aria-label="Itens da sacola">${rows}</section>${renderSummary()}`;
}

function updatePaymentFields() {
  const payment = document.querySelector('input[name="payment"]:checked')?.value || "PIX";
  const cardFields = document.querySelector("[data-card-fields]");
  if (!cardFields) return;

  const isCard = payment === "CARTAO" && paymentMode === "mercado-pago";
  cardFields.hidden = !isCard;
  cardFields.querySelectorAll("input, select").forEach((field) => {
    field.disabled = !isCard;
    field.required = isCard;
    if (!isCard) field.value = field.name === "installments" ? "1" : "";
  });
  const cpf = document.querySelector("#customer-cpf");
  if (cpf) {
    cpf.required = paymentMode === "mercado-pago";
    cpf.closest("[data-cpf-field]").hidden = paymentMode === "demo";
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  })[character]);
}

function updateCheckoutProgress(confirmed = false) {
  const progress = document.querySelector(".checkout-progress");
  if (!progress) return;
  progress.innerHTML = confirmed
    ? `<span class="step-done">01 Sacola</span><span class="progress-line"></span><span class="step-done">02 Pagamento</span><span class="progress-line"></span><span class="step-current">03 Confirmação</span>`
    : `<span class="step-done">01 Sacola</span><span class="progress-line"></span><span class="step-current">02 Pagamento</span>`;
}

function renderOrderSuccess(order) {
  const container = document.querySelector("[data-checkout-page]");
  if (!container) return;
  const firstName = escapeHtml(String(order.name || state.user?.name || "Cliente").trim().split(/\s+/)[0]);
  const paymentLabel = order.payment === "CARTAO" ? "cartão" : escapeHtml(order.payment || "pagamento");
  container.innerHTML = `<section class="order-success"><span class="success-mark" aria-hidden="true">✓</span><p class="eyebrow">Pedido NÓRD #${escapeHtml(order.id)}</p><h2>Pagamento confirmado.</h2><p>Obrigado, ${firstName}. Recebemos seu pagamento de <strong>${money(Number(order.total))}</strong> via ${paymentLabel}. Seu pedido está liberado.</p><a class="button button-dark" href="index.html">Voltar para a loja <span aria-hidden="true">↗</span></a></section>`;
  const title = document.querySelector(".page-intro h1");
  const intro = document.querySelector(".page-intro .intro-copy");
  if (title) title.innerHTML = `Compra <em>confirmada.</em>`;
  if (intro) intro.textContent = "Pagamento recebido. Seu pedido foi liberado.";
  updateCheckoutProgress(true);
}

function renderDemoConfirmation(order) {
  const container = document.querySelector("[data-checkout-page]");
  if (!container) return;
  const firstName = escapeHtml(String(order.name || state.user?.name || "Cliente").trim().split(/\s+/)[0]);
  const paymentLabels = { PIX: "PIX", CARTAO: "cartão de crédito", BOLETO: "boleto" };
  const paymentLabel = paymentLabels[order.payment] || "pagamento";
  let example = "";
  if (order.payment === "PIX") {
    example = `<div class="demo-payment-example"><strong>Exemplo de código PIX</strong><code>DEMO-PIX-NAO-PAGAVEL</code><span>Este código é ilustrativo e não pode ser usado para transferir dinheiro.</span></div>`;
  } else if (order.payment === "BOLETO") {
    example = `<div class="demo-payment-example"><strong>Exemplo de boleto</strong><code>DEMO-BOLETO-NAO-PAGAVEL</code><span>Este identificador é ilustrativo; nenhum boleto foi emitido.</span></div>`;
  } else {
    example = `<div class="demo-payment-example"><strong>Cartão de crédito</strong><span>Etapa apresentada em modo de demonstração. Nenhum dado de cartão foi solicitado ou cobrado.</span></div>`;
  }
  container.innerHTML = `<section class="payment-pending demo-confirmation"><span class="demo-label">MODO DEMONSTRAÇÃO — SEM PAGAMENTO REAL</span><span class="success-mark" aria-hidden="true">✓</span><p class="eyebrow">Pedido de demonstração #${escapeHtml(order.id)}</p><h2>Fluxo de pedido concluído.</h2><p>Obrigado, ${firstName}. O pedido de <strong>${money(Number(order.total))}</strong> via ${paymentLabel} foi salvo apenas para demonstrar o site.</p>${example}<p class="demo-notice">Nenhum pagamento foi realizado ou confirmado; este pedido não é uma compra real e não será enviado.</p><a class="button button-dark" href="index.html">Voltar para a loja <span aria-hidden="true">↗</span></a></section>`;
  const title = document.querySelector(".page-intro h1");
  const intro = document.querySelector(".page-intro .intro-copy");
  if (title) title.innerHTML = `Demonstração <em>concluída.</em>`;
  if (intro) intro.textContent = "Este checkout é uma simulação local, sem cobrança.";
  updateCheckoutProgress(true);
}

function pararConsultaPagamento() {
  if (paymentPollTimer) {
    window.clearInterval(paymentPollTimer);
    paymentPollTimer = null;
  }
}

async function consultarPagamentoPendente() {
  const pagamento = state.pendingPayment;
  if (!pagamento?.order?.checkout_key) return;
  try {
    const response = await fetch(`/api/pedidos/${encodeURIComponent(pagamento.order.checkout_key)}`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) {
      throw new Error(data.message || "Não foi possível consultar o pagamento.");
    }

    if (data.order.status === "LIBERADO") {
      pararConsultaPagamento();
      state.completedOrder = {
        id: data.order.id,
        name: state.user?.name || "Cliente",
        total: data.order.total,
        payment: data.order.payment,
      };
      state.pendingPayment = null;
      state.checkoutKey = null;
      state.cart = [];
      state.coupon = "";
      saveState();
      renderCheckout();
      return;
    }

    if (["PAGAMENTO_RECUSADO", "PAGAMENTO_CANCELADO"].includes(data.order.status)) {
      pararConsultaPagamento();
      state.pendingPayment.order = { ...state.pendingPayment.order, ...data.order };
      state.pendingPayment.payment.status = data.order.payment_status;
      saveState();
      renderPaymentPending(state.pendingPayment);
      return;
    }

    const status = document.querySelector("[data-payment-status]");
    if (status) {
      status.textContent = `Pagamento ${data.order.payment_status.toLowerCase()}. O pedido continua aguardando a confirmação do Mercado Pago.`;
    }
  } catch {
    const status = document.querySelector("[data-payment-status]");
    if (status) status.textContent = "Não foi possível consultar agora; vamos tentar novamente automaticamente.";
  }
}

function renderPaymentPending(pagamento) {
  const container = document.querySelector("[data-checkout-page]");
  if (!container) return;
  const metodo = pagamento.order.payment;
  const statusFalhou = ["PAGAMENTO_RECUSADO", "PAGAMENTO_CANCELADO"].includes(pagamento.order.status);
  const pix = pagamento.payment?.pix;
  const boleto = pagamento.payment?.boleto;
  let detalhes = "";

  if (metodo === "PIX" && pix?.qr_base64 && pix?.codigo) {
    detalhes = `<div class="payment-instructions"><img class="payment-qr" src="data:image/png;base64,${escapeHtml(pix.qr_base64)}" alt="QR Code PIX do pedido"><label for="pix-copy-code">PIX copia e cola</label><textarea id="pix-copy-code" data-payment-code readonly>${escapeHtml(pix.codigo)}</textarea><button class="button button-dark" type="button" data-copy-payment>Copiar código PIX</button></div>`;
  } else if (metodo === "BOLETO" && boleto?.url) {
    detalhes = `<div class="payment-instructions">${boleto.codigo ? `<p class="payment-code-label">Linha digitável</p><textarea data-payment-code readonly>${escapeHtml(boleto.codigo)}</textarea><button class="button button-dark" type="button" data-copy-payment>Copiar linha digitável</button>` : ""}<a class="button button-dark" href="${escapeHtml(boleto.url)}" target="_blank" rel="noopener noreferrer">Abrir boleto do Mercado Pago <span aria-hidden="true">↗</span></a></div>`;
  } else if (metodo === "CARTAO") {
    detalhes = `<p>O Mercado Pago está processando a autorização do cartão.</p>`;
  } else {
    detalhes = `<p>O provedor não retornou os dados da cobrança. Consulte o pagamento novamente ou tente outra forma de pagamento.</p>`;
  }

  container.innerHTML = `<section class="payment-pending"><span class="success-mark" aria-hidden="true">${statusFalhou ? "!" : "…"}</span><p class="eyebrow">Pedido NÓRD #${escapeHtml(pagamento.order.id)}</p><h2>${statusFalhou ? "Pagamento não concluído." : "Aguardando pagamento."}</h2><p data-payment-status>${statusFalhou ? "O Mercado Pago não confirmou o pagamento. O pedido não foi liberado." : "Pague usando os dados abaixo. O pedido só será liberado depois que o Mercado Pago confirmar o recebimento."}</p>${detalhes}${statusFalhou ? `<button class="button button-dark" type="button" data-retry-payment>Tentar outro pagamento</button>` : ""}</section>`;
  const title = document.querySelector(".page-intro h1");
  const intro = document.querySelector(".page-intro .intro-copy");
  if (title) title.innerHTML = statusFalhou ? `Pagamento <em>não concluído.</em>` : `Aguardando <em>pagamento.</em>`;
  if (intro) intro.textContent = statusFalhou ? "Seu pedido continua pendente e não foi liberado." : "Conclua o pagamento para liberar seu pedido.";
  updateCheckoutProgress(false);

  if (!statusFalhou) {
    pararConsultaPagamento();
    consultarPagamentoPendente();
    paymentPollTimer = window.setInterval(consultarPagamentoPendente, 7000);
  }
}

function renderCheckout() {
  const container = document.querySelector("[data-checkout-page]");
  if (!container) return;
  if (state.cart.length && (state.demoOrder || state.completedOrder)) {
    state.demoOrder = null;
    state.completedOrder = null;
    saveState();
  }
  if (state.demoOrder) {
    renderDemoConfirmation(state.demoOrder);
    return;
  }
  if (state.completedOrder) {
    renderOrderSuccess(state.completedOrder);
    return;
  }
  if (state.pendingPayment) {
    renderPaymentPending(state.pendingPayment);
    return;
  }
  if (!catalogoCarregado || !checkoutConfigCarregada) {
    const message = erroCatalogo || erroCheckoutConfig || "Conectando ao servidor da loja...";
    container.innerHTML = `<section class="empty-state"><h2>Finalização indisponível.</h2><p role="alert">${escapeHtml(message)}</p><button class="button button-dark" type="button" data-retry-store>Conectar novamente</button></section>`;
    return;
  }
  if (!state.cart.length) {
    container.innerHTML = `<section class="empty-state"><h2>Sua sacola está vazia.</h2><p>Escolha seus produtos antes de finalizar.</p><a class="button button-dark" href="index.html#catalogo">Ver produtos <span aria-hidden="true">↗</span></a></section>`;
    return;
  }
  container.innerHTML = `<form id="checkout-form" class="checkout-form" data-checkout-form>
    <section class="form-section"><h2>01 / Seus dados</h2><div class="field-grid">
      <div class="field full"><label for="customer-name">Nome completo</label><input id="customer-name" name="name" autocomplete="name" required value="${escapeHtml(state.user?.name || "")}"></div>
      <div class="field"><label for="customer-email">E-mail</label><input id="customer-email" name="email" type="email" autocomplete="email" required value="${escapeHtml(state.user?.email || "")}"></div>
      <div class="field"><label for="customer-phone">Telefone</label><input id="customer-phone" name="phone" type="tel" autocomplete="tel" placeholder="(00) 00000-0000" required></div>
      <div class="field full" data-cpf-field><label for="customer-cpf">CPF do pagador</label><input id="customer-cpf" name="cpf" inputmode="numeric" maxlength="14" autocomplete="off" placeholder="000.000.000-00"></div>
    </div></section>
    <section class="form-section"><h2>02 / Entrega</h2><div class="field-grid">
      <div class="field"><label for="customer-cep">CEP</label><input id="customer-cep" name="cep" inputmode="numeric" maxlength="9" placeholder="00000-000" aria-describedby="customer-cep-status" required value="${escapeHtml(state.cep)}"><small id="customer-cep-status" data-cep-status role="status" aria-live="polite"></small></div>
      <div class="field"><label for="customer-city">Cidade</label><input id="customer-city" name="city" autocomplete="address-level2" required></div>
      <div class="field"><label for="customer-address">Rua</label><input id="customer-address" name="address" autocomplete="address-line1" required></div>
      <div class="field"><label for="customer-address-number">Número</label><input id="customer-address-number" name="addressNumber" autocomplete="address-line2" required></div>
      <div class="field"><label for="customer-neighborhood">Bairro</label><input id="customer-neighborhood" name="neighborhood" required></div>
      <div class="field"><label for="customer-state">Estado</label><select id="customer-state" name="state" required>
        <option value="">Selecione</option>
        ${["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"].map((uf) => `<option value="${uf}">${uf}</option>`).join("")}
      </select></div>
    </div></section>
    <section class="form-section"><h2>03 / Pagamento</h2><div class="payment-options">
      <label class="payment-option"><input type="radio" name="payment" value="PIX" checked><span>PIX</span><small>5% de desconto</small></label>
      <label class="payment-option"><input type="radio" name="payment" value="CARTAO"><span>Cartão de crédito</span><small>${paymentMode === "demo" ? "Simulação" : "Mercado Pago"}</small></label>
      <label class="payment-option"><input type="radio" name="payment" value="BOLETO"><span>Boleto bancário</span><small>${paymentMode === "demo" ? "Simulação" : "Mercado Pago"}</small></label>
    </div>
    ${paymentMode === "demo" ? `<p class="demo-checkout-notice">Modo demonstração: confirmar o pedido não realiza cobrança. Não informe dados reais de cartão.</p>` : ""}
    <div class="field-grid" data-card-fields hidden>
      <div class="field full"><label for="card-number">Número do cartão</label><input id="card-number" name="cardNumber" inputmode="numeric" maxlength="19" placeholder="1234 5678 9012 3456" required></div>
      <div class="field full"><label for="cardholder-name">Nome impresso no cartão</label><input id="cardholder-name" name="cardholderName" autocomplete="cc-name" required></div>
      <div class="field"><label for="card-expiration-month">Mês de validade</label><input id="card-expiration-month" name="expirationMonth" inputmode="numeric" maxlength="2" placeholder="MM" autocomplete="cc-exp-month" required></div>
      <div class="field"><label for="card-expiration-year">Ano de validade</label><input id="card-expiration-year" name="expirationYear" inputmode="numeric" maxlength="4" placeholder="AAAA" autocomplete="cc-exp-year" required></div>
      <div class="field"><label for="card-cvv">CVV</label><input id="card-cvv" name="cvv" inputmode="numeric" maxlength="4" placeholder="123" required></div>
      <div class="field"><label for="card-installments">Parcelas</label><select id="card-installments" name="installments" required>
        <option value="1">1x sem juros</option>
        <option value="2">2x sem juros</option>
        <option value="3">3x sem juros</option>
        <option value="4">4x sem juros</option>
        <option value="5">5x sem juros</option>
        <option value="6">6x sem juros</option>
        <option value="7">7x sem juros</option>
        <option value="8">8x sem juros</option>
        <option value="9">9x sem juros</option>
        <option value="10">10x sem juros</option>
        <option value="11">11x sem juros</option>
        <option value="12">12x sem juros</option>
      </select></div>
    </div>
    </section>
  </form>${renderSummary(true)}${paymentMode === "mercado-pago" ? `<p class="payment-security-note">Os dados do cartão são tokenizados pelo Mercado Pago e não são enviados nem armazenados neste site.</p>` : ""}`;
  updatePaymentFields();
  if (state.cep.replace(/\D/g, "").length === 8) {
    buscarEnderecoPorCep(state.cep);
  }
}

async function buscarEnderecoPorCep(value) {
  const cep = value.replace(/\D/g, "");
  const input = document.querySelector("#customer-cep");
  const status = document.querySelector("[data-cep-status]");
  if (cepLookupController) cepLookupController.abort();
  if (cep.length !== 8 || !input || !status) return;

  const controller = new AbortController();
  cepLookupController = controller;
  status.textContent = "Buscando endereço...";
  try {
    const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`, { signal: controller.signal });
    if (!response.ok) throw new Error(`Consulta de CEP falhou (HTTP ${response.status}).`);
    const address = await response.json();
    if (controller.signal.aborted || input.value.replace(/\D/g, "") !== cep) return;
    if (address.erro) {
      status.textContent = "CEP não encontrado. Confira o número e preencha o endereço manualmente.";
      return;
    }

    document.querySelector("#customer-address").value = address.logradouro || "";
    document.querySelector("#customer-neighborhood").value = address.bairro || "";
    document.querySelector("#customer-city").value = address.localidade || "";
    document.querySelector("#customer-state").value = address.uf || "";
    status.textContent = "Endereço preenchido. Confira os dados e informe o número.";
  } catch (error) {
    if (error.name === "AbortError") return;
    if (!controller.signal.aborted && input.value.replace(/\D/g, "") === cep) {
      status.textContent = "Não foi possível consultar o CEP. Preencha o endereço manualmente.";
    }
  }
}

let authMode = "login";
function renderAuth() {
  const form = document.querySelector("[data-auth-form]");
  if (!form) return;
  form.innerHTML = `${authMode === "register" ? `<div class="field"><label for="auth-name">Nome completo</label><input id="auth-name" name="name" autocomplete="name" required maxlength="100" pattern="[A-Za-zÀ-ÿ ]+"></div>` : ""}
    <div class="field"><label for="auth-email">E-mail</label><input id="auth-email" name="email" type="email" autocomplete="email" required></div>
    <div class="field"><label for="auth-password">Senha</label><input id="auth-password" name="password" type="password" autocomplete="${authMode === "register" ? "new-password" : "current-password"}" required minlength="6" maxlength="20"></div>
    <p class="auth-message" data-auth-message role="status"></p><button class="button button-dark" type="submit">${authMode === "register" ? "Criar conta" : "Entrar"} <span aria-hidden="true">↗</span></button>`;
  document.querySelectorAll("[data-auth-tab]").forEach((tab) => tab.classList.toggle("selected", tab.dataset.authTab === authMode));
}

function renderAccount() {
  const container = document.querySelector("[data-account-page]");
  if (!container) return;
  if (!authChecked) {
    container.innerHTML = `<section class="account-card account-logged-out"><p role="status">Verificando sua conta...</p></section>`;
    return;
  }
  if (!state.user) {
    container.innerHTML = `<section class="account-card account-logged-out"><h2>${authError ? "Não foi possível carregar sua conta" : "Entre na sua conta"}</h2><p>${escapeHtml(authError || "Faça login para consultar e editar seus dados.")}</p>${authError ? `<button class="button button-dark" type="button" data-retry-auth>Tentar novamente <span aria-hidden="true">↗</span></button>` : `<a class="button button-dark" href="login.html">Ir para o login <span aria-hidden="true">↗</span></a>`}</section>`;
    return;
  }

  const user = state.user;
  const initials = user.name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toLocaleUpperCase("pt-BR");
  const avatar = user.photo
    ? `<img src="${escapeHtml(user.photo)}" alt="Foto de perfil de ${escapeHtml(user.name)}" class="profile-avatar">`
    : `<span class="profile-avatar profile-avatar-initials" aria-hidden="true">${escapeHtml(initials)}</span>`;
  container.innerHTML = `<section class="account-card">
    <div class="profile-heading"><div class="profile-avatar-wrap" data-profile-avatar>${avatar}</div>
      <div><p class="eyebrow">Sua conta NÓRD</p><h2>Seus dados pessoais</h2><p>Atualize as informações usadas na sua experiência.</p></div>
    </div>
    <div class="profile-photo-field"><span>Foto de perfil</span><button class="button button-outline" type="button" data-open-photo-dialog>Mudar foto de perfil</button></div>
    <section class="theme-settings" aria-labelledby="theme-settings-title">
      <p class="eyebrow">Aparência</p><h3 id="theme-settings-title">Tema da loja</h3>
      <fieldset class="theme-picker">
        <legend>Escolha como a loja aparece para você</legend>
        <label class="theme-option theme-option-light"><input type="radio" name="theme" value="light" data-theme-choice ${state.theme === "light" ? "checked" : ""}><span class="theme-swatch" aria-hidden="true"></span><strong>Claro</strong></label>
        <label class="theme-option theme-option-dark"><input type="radio" name="theme" value="dark" data-theme-choice ${state.theme === "dark" ? "checked" : ""}><span class="theme-swatch" aria-hidden="true"></span><strong>Escuro</strong></label>
        <label class="theme-option theme-option-purple"><input type="radio" name="theme" value="purple" data-theme-choice ${state.theme === "purple" ? "checked" : ""}><span class="theme-swatch" aria-hidden="true"></span><strong>Roxo</strong></label>
        <label class="theme-option theme-option-night-owl"><input type="radio" name="theme" value="night-owl" data-theme-choice ${state.theme === "night-owl" ? "checked" : ""}><span class="theme-swatch" aria-hidden="true"></span><strong>Verde-água escuro</strong><small>Inspirado no Night Owl</small></label>
      </fieldset>
    </section>
    <form class="account-form" data-account-form>
      <div class="field"><label for="profile-name">Nome completo</label><input id="profile-name" name="name" autocomplete="name" required maxlength="100" pattern="[A-Za-zÀ-ÿ ]+" value="${escapeHtml(user.name)}"></div>
      <div class="field"><label for="profile-email">E-mail</label><input id="profile-email" name="email" type="email" autocomplete="email" required maxlength="100" value="${escapeHtml(user.email)}"></div>
      <p class="auth-message" data-account-message role="status"></p>
      <div class="account-actions"><button class="button button-dark" type="submit">Salvar alterações <span aria-hidden="true">↗</span></button><button class="button button-outline" type="button" data-account-logout>Sair da conta</button></div>
    </form>
  </section>
  <dialog class="profile-photo-dialog" data-photo-dialog aria-labelledby="photo-dialog-title">
    <div class="photo-dialog-content">
      <button class="photo-dialog-close" type="button" data-close-photo-dialog aria-label="Fechar">×</button>
      <p class="eyebrow">Personalize seu perfil</p><h2 id="photo-dialog-title">Mudar foto de perfil</h2>
      <p class="photo-dialog-description">Escolha uma imagem para usar como foto da sua conta.</p>
      <div class="photo-preview" data-photo-preview>${avatar}</div>
      <input id="profile-photo-file" class="visually-hidden-file" type="file" accept="image/*" data-profile-photo>
      <button class="button button-outline photo-choose-button" type="button" data-select-photo>Escolher ficheiro</button>
      <p class="photo-file-note">Imagens PNG, JPEG, WebP ou GIF de até 2 MB. A foto fica salva na sua conta.</p>
      <p class="auth-message" data-photo-message role="status"></p>
      <div class="account-actions photo-dialog-actions">
        <button class="button button-dark" type="button" data-save-photo>Salvar foto</button>
        ${user.photo ? `<button class="button button-outline" type="button" data-remove-photo>Remover foto</button>` : ""}
        <button class="button button-outline" type="button" data-close-photo-dialog>Cancelar</button>
      </div>
    </div>
  </dialog>`;
}

function atualizarPreviaFoto(src) {
  const preview = document.querySelector("[data-photo-preview]");
  if (!preview) return;
  if (src) {
    preview.innerHTML = `<img src="${escapeHtml(src)}" alt="Prévia da foto de perfil" class="profile-avatar">`;
    return;
  }
  const initials = state.user.name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toLocaleUpperCase("pt-BR");
  preview.innerHTML = `<span class="profile-avatar profile-avatar-initials" aria-hidden="true">${escapeHtml(initials)}</span>`;
}

async function tokenizarCartao(formData) {
  const configResponse = await fetch("/api/config");
  const config = await configResponse.json().catch(() => ({}));
  if (!configResponse.ok || !config.mercadoPagoPublicKey) {
    throw new Error("Mercado Pago não configurado. O servidor precisa de uma chave pública para aceitar cartão.");
  }
  await carregarSdkMercadoPago();

  const cartao = String(formData.get("cardNumber") || "").replace(/\D/g, "");
  const mp = new window.MercadoPago(config.mercadoPagoPublicKey, { locale: "pt-BR" });
  const metodos = await mp.getPaymentMethods({ bin: cartao.slice(0, 6) });
  const metodoCartao = (metodos.results || []).find((metodo) => metodo.payment_type_id === "credit_card");
  if (!metodoCartao?.id) throw new Error("Não foi possível identificar a bandeira do cartão.");
  const emissores = await mp.getIssuers({ paymentMethodId: metodoCartao.id, bin: cartao.slice(0, 6) });
  const emissor = emissores[0];
  if (!emissor?.id) throw new Error("Não foi possível identificar o emissor do cartão.");

  const token = await mp.createCardToken({
    cardNumber: cartao,
    cardholderName: String(formData.get("cardholderName") || "").trim(),
    securityCode: String(formData.get("cvv") || ""),
    expirationMonth: String(formData.get("expirationMonth") || "").padStart(2, "0"),
    expirationYear: String(formData.get("expirationYear") || ""),
    identificationType: "CPF",
    identificationNumber: String(formData.get("cpf") || "").replace(/\D/g, ""),
  });
  if (!token?.id) {
    throw new Error("O Mercado Pago não conseguiu tokenizar este cartão.");
  }
  return {
    cardToken: token.id,
    cardPaymentMethodId: metodoCartao.id,
    cardIssuerId: String(emissor.id),
    installments: Number(formData.get("installments") || 1),
  };
}

function carregarSdkMercadoPago() {
  if (window.MercadoPago) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const sdk = document.querySelector('script[data-mercado-pago-sdk]') || document.createElement("script");
    sdk.src = "https://sdk.mercadopago.com/js/v2";
    sdk.dataset.mercadoPagoSdk = "true";
    sdk.onload = () => resolve();
    sdk.onerror = () => reject(new Error("Não foi possível carregar a proteção de cartão do Mercado Pago."));
    if (!sdk.isConnected) document.head.append(sdk);
  });
}

document.addEventListener("change", async (event) => {
  if (event.target.matches("[data-theme-choice]")) {
    const previousTheme = state.theme;
    try {
      const data = await requestJson("/api/auth/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme: event.target.value }),
      });
      state.user = data.user;
      state.theme = data.user.theme;
      saveState();
    } catch {
      state.theme = previousTheme;
      applyTheme();
      const message = document.querySelector("[data-account-message]");
      if (message) message.textContent = "Não foi possível salvar o tema na sua conta. Tente novamente.";
      return;
    }
    const message = document.querySelector("[data-account-message]");
    if (message) message.textContent = "Tema atualizado.";
  }

  if (event.target.matches('input[name="payment"]')) {
    updatePaymentFields();
    updateCheckoutTotal();
  }

  if (event.target.matches("[data-profile-photo]")) {
    const file = event.target.files[0];
    if (!file) return;
    const message = document.querySelector("[data-photo-message]");
    const saveButton = document.querySelector("[data-save-photo]");
    if (!["image/png", "image/jpeg", "image/webp", "image/gif"].includes(file.type) || file.size > 2 * 1024 * 1024) {
      message.textContent = "Escolha uma imagem PNG, JPEG, WebP ou GIF de até 2 MB.";
      event.target.value = "";
      pendingProfilePhoto = null;
      atualizarPreviaFoto(state.user.photo);
      saveButton.disabled = true;
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result !== "string") {
        message.textContent = "Não foi possível carregar essa imagem.";
        atualizarPreviaFoto(state.user.photo);
        return;
      }
      pendingProfilePhoto = reader.result;
      atualizarPreviaFoto(pendingProfilePhoto);
      saveButton.disabled = false;
      message.textContent = "Prévia atualizada. Salve para aplicar essa foto.";
    };
    reader.onerror = () => {
      message.textContent = "Não foi possível ler o arquivo selecionado.";
      atualizarPreviaFoto(state.user.photo);
    };
    reader.readAsDataURL(file);
  }
});

document.addEventListener("click", async (event) => {
  if (event.target.closest("[data-retry-auth]")) {
    await carregarSessaoDaConta();
    return;
  }

  const openPhotoDialog = event.target.closest("[data-open-photo-dialog]");
  if (openPhotoDialog) {
    pendingProfilePhoto = null;
    const dialog = document.querySelector("[data-photo-dialog]");
    const fileInput = document.querySelector("[data-profile-photo]");
    fileInput.value = "";
    atualizarPreviaFoto(state.user.photo);
    document.querySelector("[data-photo-message]").textContent = "";
    document.querySelector("[data-save-photo]").disabled = true;
    dialog.showModal();
    return;
  }

  if (event.target.closest("[data-select-photo]")) {
    document.querySelector("[data-profile-photo]").click();
    return;
  }

  if (event.target.closest("[data-close-photo-dialog]")) {
    pendingProfilePhoto = null;
    document.querySelector("[data-photo-dialog]").close();
    return;
  }

  const savePhotoButton = event.target.closest("[data-save-photo], [data-remove-photo]");
  if (savePhotoButton) {
    const removingPhoto = savePhotoButton.matches("[data-remove-photo]");
    const newPhoto = removingPhoto ? "" : pendingProfilePhoto;
    if (!removingPhoto && !newPhoto) {
      document.querySelector("[data-photo-message]").textContent = "Escolha uma foto antes de salvar.";
      return;
    }

    try {
      const data = await requestJson("/api/auth/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ photo: newPhoto }),
      });
      state.user = data.user;
      state.theme = data.user.theme;
      saveState();
    } catch (error) {
      document.querySelector("[data-photo-message]").textContent = error.message || "Não foi possível salvar a foto na sua conta.";
      return;
    }
    pendingProfilePhoto = null;
    renderAccount();
    document.querySelector("[data-account-message]").textContent = savePhotoButton.matches("[data-remove-photo]")
      ? "Foto de perfil removida."
      : "Foto de perfil atualizada.";
    return;
  }

  if (event.target.closest("[data-account-logout]")) {
    const message = document.querySelector("[data-account-message]");
    try {
      await requestJson("/api/auth/logout", { method: "POST" });
      state.user = null;
      state.theme = "dark";
      saveState();
      window.location.assign("login.html");
    } catch (error) {
      if (message) message.textContent = error.message || "Não foi possível sair da conta agora.";
    }
    return;
  }

  const copyPaymentButton = event.target.closest("[data-copy-payment]");
  if (copyPaymentButton) {
    const code = document.querySelector("[data-payment-code]")?.value || "";
    navigator.clipboard.writeText(code)
      .then(() => showToast("Código de pagamento copiado."))
      .catch(() => showToast("Não foi possível copiar. Selecione e copie o código manualmente."));
  }

  const retryPaymentButton = event.target.closest("[data-retry-payment]");
  if (retryPaymentButton) {
    pararConsultaPagamento();
    state.pendingPayment = null;
    state.checkoutKey = null;
    saveState();
    renderCheckout();
  }

  const addButton = event.target.closest("[data-add]");
  if (addButton) addToCart(addButton.dataset.add);

  const detailAdd = event.target.closest("[data-detail-add]");
  if (detailAdd) addToCart(detailAdd.dataset.detailAdd, Number(document.querySelector("[data-detail-quantity]")?.textContent || 1));

  const detailQty = event.target.closest("[data-detail-qty]");
  if (detailQty) {
    const value = document.querySelector("[data-detail-quantity]");
    const next = Math.max(1, Math.min(10, Number(value.textContent) + Number(detailQty.dataset.detailQty)));
    value.textContent = next;
  }

  const cartQty = event.target.closest("[data-cart-qty]");
  if (cartQty) {
    const item = state.cart.find((entry) => entry.id === Number(cartQty.dataset.cartQty));
    if (item) {
      const product = findProduct(item.id);
      item.quantity = Math.max(0, Math.min(product.stock, item.quantity + Number(cartQty.dataset.delta)));
      state.cart = state.cart.filter((entry) => entry.quantity > 0);
      saveState();
      renderCart();
    }
  }

  const removeButton = event.target.closest("[data-remove]");
  if (removeButton) {
    state.cart = state.cart.filter((item) => item.id !== Number(removeButton.dataset.remove));
    saveState();
    renderCart();
  }

  const authTab = event.target.closest("[data-auth-tab]");
  if (authTab) {
    authMode = authTab.dataset.authTab;
    renderAuth();
  }

  const photoDialog = event.target.closest("[data-photo-dialog]");
  if (photoDialog && event.target === photoDialog) {
    pendingProfilePhoto = null;
    photoDialog.close();
  }
});

document.addEventListener("submit", async (event) => {
  if (event.target.matches("[data-account-form]")) {
    event.preventDefault();
    if (!event.target.reportValidity()) return;
    const formData = new FormData(event.target);
    try {
      const data = await requestJson("/api/auth/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: String(formData.get("name")).trim(),
          email: String(formData.get("email")).trim().toLowerCase(),
        }),
      });
      state.user = data.user;
      state.theme = data.user.theme;
      saveState();
    } catch (error) {
      document.querySelector("[data-account-message]").textContent = error.message || "Não foi possível salvar as alterações na sua conta.";
      return;
    }
    renderAccount();
    document.querySelector("[data-account-message]").textContent = "Dados da conta salvos.";
  }

  if (event.target.matches("[data-coupon-form]")) {
    event.preventDefault();
    const code = new FormData(event.target).get("coupon").trim().toUpperCase();
    if (!["DESCONTO10", "DESCONTO20"].includes(code)) {
      showToast("Cupom inválido. Experimente DESCONTO10 ou DESCONTO20.");
      return;
    }
    state.coupon = code;
    saveState();
    renderCart();
    showToast(`Cupom ${code} aplicado.`);
  }

  if (event.target.matches("[data-shipping-form]")) {
    event.preventDefault();
    const cep = new FormData(event.target).get("cep").replace(/\D/g, "");
    if (cep.length !== 8) {
      showToast("Digite um CEP com 8 números.");
      return;
    }
    state.cep = cep;
    saveState();
    renderCart();
    showToast(`Frete calculado: ${money(shippingPrice())}.`);
  }

  if (event.target.matches("[data-auth-form]")) {
    event.preventDefault();
    if (!event.target.reportValidity()) return;
    const formData = new FormData(event.target);
    const email = String(formData.get("email")).trim().toLowerCase();
    const message = document.querySelector("[data-auth-message]");
    const submitButton = event.target.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    try {
      const data = await requestJson(authMode === "register" ? "/api/auth/register" : "/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: authMode === "register" ? String(formData.get("name")).trim() : undefined,
          email,
          password: String(formData.get("password")),
        }),
      });
      state.user = data.user;
      state.registeredUser = null;
      state.theme = data.user.theme;
      saveState();
      window.location.assign("index.html");
    } catch (error) {
      message.textContent = error.message || "Não foi possível autenticar sua conta.";
      submitButton.disabled = false;
    }
  }

  if (event.target.matches("[data-checkout-form]")) {
    event.preventDefault();
    if (!event.target.reportValidity()) return;
    const formData = new FormData(event.target);
    const method = formData.get("payment");
    const payload = {
      name: String(formData.get("name")).trim(),
      email: String(formData.get("email")).trim().toLowerCase(),
      cep: String(formData.get("cep") || "").trim(),
      payment: method,
      coupon: state.coupon,
      items: state.cart.map((item) => ({ id: item.id, quantity: item.quantity })),
    };
    if (paymentMode === "mercado-pago") {
      Object.assign(payload, {
        phone: String(formData.get("phone") || "").trim(),
        cpf: String(formData.get("cpf") || "").replace(/\D/g, ""),
        city: String(formData.get("city") || "").trim(),
        address: String(formData.get("address") || "").trim(),
        addressNumber: String(formData.get("addressNumber") || "").trim(),
        neighborhood: String(formData.get("neighborhood") || "").trim(),
        state: String(formData.get("state") || "").trim(),
      });
    }

    const confirmButton = document.querySelector('[form="checkout-form"]');
    if (confirmButton) {
      confirmButton.disabled = true;
      confirmButton.textContent = "Processando pedido...";
    }

    try {
      if (method === "CARTAO" && paymentMode === "mercado-pago") {
        Object.assign(payload, await tokenizarCartao(formData));
      }
      if (!state.checkoutKey) state.checkoutKey = crypto.randomUUID();
      payload.checkoutKey = state.checkoutKey;
      saveState();

      const response = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) {
        throw new Error(data.message || `Erro ao confirmar o pedido (HTTP ${response.status}).`);
      }

      state.user = { name: payload.name, email: payload.email };
      if (data.demo) {
        state.demoOrder = {
          id: data.order.id,
          name: payload.name,
          total: data.order.total,
          payment: data.order.payment,
        };
        state.cart = [];
        state.coupon = "";
        state.checkoutKey = null;
        state.pendingPayment = null;
        saveState();
        renderCheckout();
      } else if (data.order.status === "LIBERADO") {
        state.completedOrder = {
          id: data.order.id,
          name: payload.name,
          total: data.order.total,
          payment: data.order.payment,
        };
        state.cart = [];
        state.coupon = "";
        state.checkoutKey = null;
        state.pendingPayment = null;
        saveState();
        renderCheckout();
      } else if (data.order.status === "PAGAMENTO_RECUSADO" || data.order.status === "PAGAMENTO_CANCELADO") {
        state.checkoutKey = null;
        saveState();
        showToast("O Mercado Pago não aprovou o pagamento. O pedido não foi liberado.");
      } else {
        state.pendingPayment = { order: data.order, payment: data.payment };
        saveState();
        renderCheckout();
      }
    } catch (error) {
      const message = error instanceof TypeError
        ? "Não foi possível conectar ao servidor. Verifique se o back-end está rodando e tente novamente."
        : error.message || "Erro ao confirmar o pedido.";
      showToast(message);
    } finally {
      if (confirmButton?.isConnected) {
        confirmButton.disabled = false;
        confirmButton.innerHTML = `Confirmar pedido <span aria-hidden="true">↗</span>`;
      }
    }
  }
});

document.addEventListener("input", (event) => {
  if (event.target.matches("[data-product-search]")) renderProducts(event.target.value);
  if (event.target.matches("#customer-cpf")) {
    const digits = event.target.value.replace(/\D/g, "").slice(0, 11);
    event.target.value = digits.replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  }
  if (event.target.matches("#card-number")) {
    event.target.value = event.target.value.replace(/\D/g, "").slice(0, 16).replace(/(\d{4})(?=\d)/g, "$1 ");
  }

  if (event.target.matches("#customer-cep")) {
    state.cep = event.target.value.replace(/\D/g, "").slice(0, 8);
    saveState();
    if (state.cep.length === 8) {
      buscarEnderecoPorCep(state.cep);
    } else {
      if (cepLookupController) cepLookupController.abort();
      const status = document.querySelector("[data-cep-status]");
      if (status) status.textContent = "";
    }
    const summary = document.querySelector("[data-checkout-page] .summary-panel");
    if (summary) {
      const replacement = document.createElement("div");
      replacement.innerHTML = renderSummary(true);
      summary.replaceWith(replacement.firstElementChild);
    }
  }
});

async function carregarDadosDaLoja() {
  let catalogoServidorCarregado = false;
  try {
    const response = await fetch("/api/produtos");
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok || !Array.isArray(data.products)) {
      throw new Error(data.message || "Não foi possível carregar os produtos do servidor.");
    }
    PRODUCTS = data.products.map((product) => ({
      ...product,
      id: Number(product.id),
      price: Number(product.price),
      stock: Number(product.stock),
    }));
    if (PRODUCTS.some((product) => !Number.isInteger(product.id)
      || !Number.isFinite(product.price)
      || !Number.isInteger(product.stock))) {
      throw new Error("O servidor retornou um catálogo inválido.");
    }
    catalogoCarregado = true;
    catalogoServidorCarregado = true;
  } catch (error) {
    erroCatalogo = error instanceof TypeError
      ? `Não foi possível conectar ao servidor em ${location.origin}. Inicie o back-end e abra a loja pelo mesmo endereço.`
      : error.message || "Não foi possível conectar ao catálogo da loja.";
    catalogoCarregado = false;
  }

  if (document.querySelector("[data-checkout-page]")) {
    try {
      const response = await fetch("/api/config");
      const config = await response.json().catch(() => ({}));
      if (!response.ok || !["demo", "mercado-pago"].includes(config.paymentMode)) {
        throw new Error(config.message || "Não foi possível carregar a configuração do checkout.");
      }
      paymentMode = config.paymentMode;
      checkoutConfigCarregada = true;
    } catch (error) {
      erroCheckoutConfig = error.message || "Não foi possível carregar a configuração do checkout.";
    }
  }

  if (catalogoServidorCarregado) reconcileCartWithCatalog();
  updateCartCounts();
  renderProducts(document.querySelector("[data-product-search]")?.value || "");
  renderProductDetail();
  renderCart();
  renderCheckout();
}

updateCartCounts();
renderAuth();
renderAccount();
renderProducts(document.querySelector("[data-product-search]")?.value || "");
renderProductDetail();
carregarDadosDaLoja();
carregarSessaoDaConta();

document.addEventListener("click", (event) => {
  const retryButton = event.target.closest("[data-retry-store]");
  if (!retryButton || reconexaoEmAndamento) return;

  reconexaoEmAndamento = true;
  retryButton.disabled = true;
  retryButton.textContent = "Conectando...";
  catalogoCarregado = false;
  erroCatalogo = "";
  checkoutConfigCarregada = false;
  erroCheckoutConfig = "";

  carregarDadosDaLoja()
    .then(() => {
      if (catalogoCarregado) showToast("Conexão restabelecida. Os produtos foram carregados.");
    })
    .finally(() => {
      reconexaoEmAndamento = false;
      if (retryButton.isConnected) {
        retryButton.disabled = false;
        retryButton.textContent = "Conectar novamente";
      }
    });
});