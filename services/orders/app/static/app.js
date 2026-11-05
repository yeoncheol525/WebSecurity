"use strict";

const byId = (id) => document.getElementById(id);
const money = (value) => new Intl.NumberFormat("ko-KR").format(Number(value));

function showError(message) {
  byId("page-message-text").textContent = message;
  byId("page-message").hidden = false;
}

async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers, credentials: "same-origin" });
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(response.status === 401 ? "아이디 또는 비밀번호를 확인해 주세요." : response.status === 404 ? "주문을 찾을 수 없거나 조회할 수 없습니다." : "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    error.status = response.status;
    throw error;
  }
  return payload;
}

function csrfToken() {
  const cookie = document.cookie.split("; ").find((value) => value.startsWith("minishop_csrf="));
  return cookie ? cookie.slice("minishop_csrf=".length) : "";
}

async function loadSession() {
  try {
    const { user } = await api("/session");
    byId("account-name").textContent = `${user.username}님`;
    for (const id of ["account-name", "logout-button", "orders-nav"]) byId(id).hidden = false;
    byId("login-link").hidden = true;
    return user;
  } catch (error) {
    if (error.status !== 401) throw error;
    return null;
  }
}

async function renderProducts() {
  const term = new URLSearchParams(location.search).get("q") || "";
  byId("keyword").value = term;
  const { products } = await api(`/products?${new URLSearchParams({ q: term })}`);
  byId("product-count").textContent = String(products.length);
  byId("empty-products").hidden = products.length > 0;
  for (const [index, product] of products.entries()) {
    const card = byId("product-template").content.cloneNode(true);
    card.querySelector(".product-visual").classList.add(`visual-${index % 4}`);
    card.querySelector(".product-sequence").textContent = `MINI / ${String(index + 1).padStart(2, "0")}`;
    card.querySelector("h3").textContent = product.name;
    card.querySelector(".product-price b").textContent = money(product.price);
    byId("product-grid").append(card);
  }
}

async function renderOrders() {
  const filter = new URLSearchParams(location.search).get("order_id") || "";
  byId("order_id").value = filter;
  const payload = await api("/orders");
  const orders = filter ? payload.orders.filter((order) => String(order.id) === filter) : payload.orders;
  byId("order-count").textContent = String(orders.length);
  byId("orders-table").hidden = orders.length === 0;
  byId("empty-orders").hidden = orders.length > 0;
  for (const order of orders) {
    const row = byId("order-template").content.cloneNode(true);
    row.querySelector(".order-number").textContent = `#${order.id}`;
    row.querySelector(".order-product-name").textContent = order.product_name;
    row.querySelector(".quantity").textContent = `${order.quantity}개`;
    row.querySelector(".detail-link").href = `/account/orders/${encodeURIComponent(order.id)}`;
    byId("order-list").append(row);
  }
}

async function renderOrder() {
  const { order } = await api(`/orders/${encodeURIComponent(document.body.dataset.orderId)}`);
  byId("detail-status").textContent = "주문한 상품을 확인하세요.";
  byId("detail-id").textContent = `#${order.id}`;
  byId("detail-product").textContent = order.product_name;
  byId("detail-quantity").textContent = `${order.quantity}개`;
  byId("detail-total").textContent = `${money(order.total_amount)}원`;
  byId("detail-date").textContent = new Date(order.order_date).toLocaleDateString("ko-KR");
  byId("order-detail").hidden = false;
}

async function main() {
  byId("logout-button").addEventListener("click", async () => {
    try {
      await api("/logout", { method: "POST", headers: { "X-CSRF-Token": csrfToken() } });
      location.assign("/");
    } catch (error) { showError(error.message); }
  });
  const form = byId("login-form");
  if (form) form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button");
    button.disabled = true;
    try {
      await api("/login", { method: "POST", body: JSON.stringify({ username: byId("username").value, password: byId("password").value }) });
      location.assign("/account/orders");
    } catch (error) { showError(error.message); button.disabled = false; }
  });
  const user = await loadSession();
  const page = document.body.dataset.page;
  if ((page === "orders" || page === "order") && !user) { location.replace("/login"); return; }
  if (page === "products") await renderProducts();
  if (page === "orders") await renderOrders();
  if (page === "order") await renderOrder();
}

main().catch((error) => showError(error.message || "화면을 불러오지 못했습니다."));
