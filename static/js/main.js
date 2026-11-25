/* ============================================
   Wound Care CRM - Main JavaScript
   ============================================ */

document.addEventListener("DOMContentLoaded", function () {
  // Mobile sidebar toggle
  const mobileToggle = document.querySelector(".mobile-menu-toggle");
  const sidebar = document.querySelector(".sidebar");
  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });

    // Close on outside click
    document.addEventListener("click", function (e) {
      if (
        window.innerWidth < 1024 &&
        sidebar.classList.contains("open") &&
        !sidebar.contains(e.target) &&
        !mobileToggle.contains(e.target)
      ) {
        sidebar.classList.remove("open");
      }
    });
  }

  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.5s, transform 0.5s";
      alert.style.opacity = "0";
      alert.style.transform = "translateY(-10px)";
      setTimeout(() => alert.remove(), 500);
    }, 5000);
  });

  // Customer order: add product to cart (persisted in localStorage)
  const productPickers = document.querySelectorAll("[data-add-product]");
  const cartContainer = document.getElementById("cart-items");
  const subtotalEl = document.getElementById("subtotal");
  const taxEl = document.getElementById("tax");
  const totalEl = document.getElementById("total");
  const cartHidden = document.getElementById("cart-hidden");
  const CART_STORAGE_KEY = "woundcare_cart";

  // Load cart from localStorage so it survives page refreshes / navigation
  let cart = {};
  try {
    const saved = localStorage.getItem(CART_STORAGE_KEY);
    if (saved) {
      cart = JSON.parse(saved);
    }
  } catch (e) {
    cart = {};
  }

  function persistCart() {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
    } catch (e) {
      // ignore storage errors
    }
  }

  function clearCart() {
    cart = {};
    persistCart();
  }

  function formatNumber(num) {
    return new Intl.NumberFormat("fa-IR").format(num);
  }

  function renderCart() {
    if (!cartContainer) return;
    const products = window.__PRODUCTS__ || [];
    let html = "";
    let subtotal = 0;
    let hiddenInputs = "";

    Object.entries(cart).forEach(function ([pid, qty]) {
      const product = products.find((p) => p.id == pid);
      if (!product) return;
      const lineTotal = product.price * qty;
      subtotal += lineTotal;
      html += `
        <div class="flex items-center gap-2 text-sm py-2 border-b border-slate-100">
          <span class="text-2xl">${product.image_emoji}</span>
          <div class="flex-1 min-w-0">
            <p class="font-medium truncate text-xs">${product.name}</p>
            <p class="text-xs text-slate-500 ltr-nums">${formatNumber(product.price)} × ${qty}</p>
          </div>
          <div class="flex items-center gap-1">
            <button type="button" data-dec="${pid}" class="h-6 w-6 rounded bg-slate-100 hover:bg-slate-200 text-sm">−</button>
            <span class="w-8 text-center text-xs font-bold ltr-nums">${qty}</span>
            <button type="button" data-inc="${pid}" class="h-6 w-6 rounded bg-slate-100 hover:bg-slate-200 text-sm">+</button>
          </div>
          <button type="button" data-remove="${pid}" class="text-rose-500 hover:text-rose-700 mr-1">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
          </button>
        </div>
      `;
      hiddenInputs += `<input type="hidden" name="products" value="${pid}"><input type="hidden" name="quantities" value="${qty}">`;
    });

    if (html === "") {
      html = `
        <p class="text-center text-sm text-slate-400 py-6">
          هنوز محصولی انتخاب نشده
        </p>
      `;
    }

    cartContainer.innerHTML = html;
    if (cartHidden) cartHidden.innerHTML = hiddenInputs;

    const tax = Math.round(subtotal * 0.1);
    const total = subtotal + tax;
    if (subtotalEl) subtotalEl.textContent = formatNumber(subtotal) + " ت";
    if (taxEl) taxEl.textContent = formatNumber(tax) + " ت";
    if (totalEl) totalEl.textContent = formatNumber(total) + " ت";

    // Update badges on picker buttons
    document.querySelectorAll("[data-add-product]").forEach(function (btn) {
      const pid = btn.getAttribute("data-add-product");
      const badge = btn.querySelector("[data-qty-badge]");
      if (cart[pid]) {
        btn.classList.add("ring-2", "ring-teal-500", "bg-teal-50");
        if (badge) {
          badge.textContent = cart[pid];
          badge.classList.remove("hidden");
        }
      } else {
        btn.classList.remove("ring-2", "ring-teal-500", "bg-teal-50");
        if (badge) badge.classList.add("hidden");
      }
    });

    // Bind cart action buttons
    document.querySelectorAll("[data-inc]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const pid = btn.getAttribute("data-inc");
        cart[pid] = (cart[pid] || 0) + 1;
        persistCart();
        renderCart();
      });
    });
    document.querySelectorAll("[data-dec]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const pid = btn.getAttribute("data-dec");
        cart[pid] = Math.max(0, (cart[pid] || 0) - 1);
        if (cart[pid] === 0) delete cart[pid];
        persistCart();
        renderCart();
      });
    });
    document.querySelectorAll("[data-remove]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const pid = btn.getAttribute("data-remove");
        delete cart[pid];
        persistCart();
        renderCart();
      });
    });
  }

  productPickers.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const pid = btn.getAttribute("data-add-product");
      cart[pid] = (cart[pid] || 0) + 1;
      persistCart();
      renderCart();
    });
  });

  // Initial render so a saved cart is shown on page load
  renderCart();

  // Clear the cart after a successful order submission (server redirects on success)
  // We detect success by looking for the success alert on the redirected page.
  (function checkOrderSuccessAndClearCart() {
    const alerts = document.querySelectorAll(".alert-success, .alert");
    let shouldClear = false;
    alerts.forEach(function (a) {
      const text = (a.textContent || "").trim();
      if (text.indexOf("ثبت شد") !== -1 || text.indexOf("با موفقیت") !== -1) {
        shouldClear = true;
      }
    });
    if (shouldClear) {
      clearCart();
    }
  })();

  // Procurement priority buttons
  const priorityBtns = document.querySelectorAll("[data-priority]");
  const priorityInput = document.getElementById("priority-input");
  priorityBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      priorityBtns.forEach((b) => {
        b.classList.remove("ring-2");
        b.classList.remove(b.getAttribute("data-active-class"));
      });
      btn.classList.add("ring-2");
      btn.classList.add(btn.getAttribute("data-active-class"));
      if (priorityInput) priorityInput.value = btn.getAttribute("data-priority");
    });
  });

  // Chat: send message via AJAX
  const chatForm = document.getElementById("chat-form");
  if (chatForm) {
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const formData = new FormData(chatForm);
      const message = formData.get("message");
      if (!message || !message.trim()) return;

      fetch(chatForm.action, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": formData.get("csrfmiddlewaretoken"),
        },
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.ok) {
            // Append message to chat
            const chatContainer = document.getElementById("chat-messages");
            if (chatContainer) {
              const bubble = document.createElement("div");
              bubble.className = "flex justify-end";
              bubble.innerHTML = `
                <div class="chat-bubble operator">
                  <p>${escapeHtml(message)}</p>
                  <p class="text-[10px] mt-1 text-white/70 ltr-nums">${data.time}</p>
                </div>
              `;
              chatContainer.appendChild(bubble);
              chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            chatForm.reset();
          } else {
            alert("خطا در ارسال پیام");
          }
        })
        .catch(() => alert("خطا در ارتباط با سرور"));
    });
  }

  // Auto-scroll chat to bottom
  const chatContainer = document.getElementById("chat-messages");
  if (chatContainer) {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
});

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
