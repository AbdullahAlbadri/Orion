// Orion team console. Plain JS, no build step.
// Safety: every value from the API is rendered with textContent (never innerHTML): manufacturer
// messages are untrusted input.
"use strict";

let token = null; // access token, memory only; the refresh token is an httpOnly cookie
let me = null;

// --- tiny DOM helper -----------------------------------------------------------
function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "on") for (const [ev, fn] of Object.entries(v)) node.addEventListener(ev, fn);
    else if (k === "class") node.className = v;
    else if (v !== false && v != null) node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}
const main = () => document.getElementById("main");
function show(...nodes) { main().replaceChildren(...nodes); }
const when = (iso) => (iso ? new Date(iso).toLocaleString() : "");
const errorBox = (msg) => h("p", { class: "error" }, msg);

// --- API with automatic refresh --------------------------------------------------
async function refresh() {
  const r = await fetch("/auth/refresh", {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ audience: "team" }),
  });
  if (!r.ok) return false;
  const data = await r.json();
  token = data.access_token; me = data.user;
  return true;
}

async function api(path, { method = "GET", body } = {}, retried = false) {
  const r = await fetch(path, {
    method, credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (r.status === 401 && !retried && (await refresh())) return api(path, { method, body }, true);
  if (r.status === 401) { token = null; renderLogin(); throw new Error("Please log in"); }
  const data = r.status === 204 ? null : await r.json().catch(() => null);
  if (!r.ok) throw new Error((data && data.detail && JSON.stringify(data.detail)) || `HTTP ${r.status}`);
  return data;
}

// --- login --------------------------------------------------------------------------
function renderLogin(message) {
  document.getElementById("nav").hidden = true;
  document.getElementById("who").textContent = "";
  const email = h("input", { type: "email", placeholder: "you@company.com", autocomplete: "email", required: true });
  const code = h("input", { inputmode: "numeric", placeholder: "6-digit code", maxlength: "6", hidden: true });
  const status = h("p", { class: "muted" }, message || "Team login: we email you a one-time code.");
  const button = h("button", {}, "Send code");
  let step = "email";

  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      if (step === "email") {
        const r = await fetch("/auth/email/start", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.value, audience: "team" }),
        });
        if (r.status === 429) throw new Error("Too many codes requested. Try again in an hour.");
        if (!r.ok) throw new Error("Check the email address.");
        step = "code"; code.hidden = false; code.focus(); button.textContent = "Log in";
        status.textContent = "If this email is on the team, a code is on its way (dev: printed in the API terminal).";
      } else {
        const r = await fetch("/auth/email/verify", {
          method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.value, code: code.value, audience: "team" }),
        });
        if (!r.ok) throw new Error("Wrong or expired code.");
        const data = await r.json();
        token = data.access_token; me = data.user;
        start();
      }
    } catch (e) {
      status.textContent = e.message;
    } finally {
      button.disabled = false;
    }
  });
  show(h("div", { class: "card login" }, h("h1", {}, "Log in"), email, code, button, status));
}

// --- pages --------------------------------------------------------------------------
function ordersTable(rows) {
  if (!rows.length) return h("p", { class: "muted" }, "Nothing here.");
  return h("div", { class: "table-wrap" }, h("table", {},
    h("thead", {}, h("tr", {}, ["Order", "Customer", "Product", "Qty", "Stage", "Needs a human", "Updated"].map((t) => h("th", {}, t)))),
    h("tbody", {}, rows.map((o) => h("tr", { class: "click", on: { click: () => (location.hash = `#/order/${o.id}`) } },
      h("td", {}, o.id), h("td", {}, o.customer_email || ""), h("td", {}, o.option || ""),
      h("td", {}, o.quantity ?? ""), h("td", {}, o.stage),
      h("td", {}, o.needs_human ? h("span", { class: "flag" }, o.needs_human) : ""),
      h("td", { class: "muted" }, when(o.updated_at)),
    ))),
  ));
}

async function pageAttention() {
  show(h("h1", {}, "Needs attention"), ordersTable(await api("/team/orders?needs_human=true")));
}

async function pageOrders() {
  show(h("h1", {}, "All orders"), ordersTable(await api("/team/orders")));
}

function kv(obj) {
  return h("table", {}, h("tbody", {}, Object.entries(obj || {}).map(([k, v]) =>
    h("tr", {}, h("th", {}, k), h("td", {}, typeof v === "object" ? JSON.stringify(v) : String(v))))));
}

async function pageOrder(id) {
  const o = await api(`/team/orders/${encodeURIComponent(id)}`);
  const spec = o.spec || {};
  const openTasks = (o.human_tasks || []).filter((t) => !t.resolved_at);
  const waiting = o.waiting ? (o.waiting.waiting_on === "manufacturer" ? "manufacturer" : `customer (${o.waiting.kind})`) : "nothing";

  const resolveBtn = h("button", { class: "secondary", disabled: !openTasks.length }, "Mark all as handled");
  resolveBtn.addEventListener("click", async () => { await api(`/team/orders/${encodeURIComponent(id)}/resolve`, { method: "POST" }); route(); });

  const manufacturers = (o.manufacturer_attempts || []);
  const select = h("select", {}, manufacturers.map((a) => h("option", { value: a.manufacturer_id }, `${a.name} (${a.manufacturer_id})`)));
  const text = h("textarea", { placeholder: "Paste the manufacturer's message exactly as received (Chinese is fine)" });
  const result = h("div");
  const send = h("button", { disabled: !manufacturers.length || waiting !== "manufacturer" }, "Process reply");
  send.addEventListener("click", async () => {
    send.disabled = true; result.replaceChildren(h("p", { class: "muted" }, "Reading the reply…"));
    try {
      await api(`/team/orders/${encodeURIComponent(id)}/manufacturer-replies`, { method: "POST", body: { manufacturer_id: select.value, text: text.value } });
      route();
    } catch (e) { result.replaceChildren(errorBox(e.message)); send.disabled = false; }
  });

  show(
    h("p", {}, h("a", { href: "#/attention" }, "← back")),
    h("h1", {}, `Order ${o.order_id}`),
    h("div", { class: "card" },
      h("div", { class: "row" }, h("strong", {}, "Stage:"), o.stage, h("strong", {}, "Waiting on:"), waiting),
      h("h2", {}, `Needs a human (${openTasks.length} open)`),
      (o.human_tasks || []).length
        ? h("ul", {}, o.human_tasks.map((t) => h("li", { class: t.resolved_at ? "done" : "" },
            t.reason, h("span", { class: "muted" }, ` · ${when(t.at)}${t.resolved_by ? ` · handled by ${t.resolved_by}` : ""}`))))
        : h("p", { class: "muted" }, "No flags."),
      resolveBtn,
    ),
    h("div", { class: "card" },
      h("h2", {}, "Paste a manufacturer reply"),
      waiting === "manufacturer" ? null : h("p", { class: "muted" }, "The order is not waiting on a manufacturer right now."),
      h("div", { class: "row" }, "From:", select), text, h("div", { class: "row" }, send), result,
    ),
    h("div", { class: "card" },
      h("h2", {}, "Manufacturers contacted"),
      manufacturers.length ? h("div", { class: "table-wrap" }, h("table", {},
        h("thead", {}, h("tr", {}, ["Manufacturer", "Outcome", "Contacted", "Deadline", "Reminded"].map((t) => h("th", {}, t)))),
        h("tbody", {}, manufacturers.map((a) => h("tr", {},
          h("td", {}, a.name), h("td", {}, a.outcome), h("td", {}, when(a.contacted_at)),
          h("td", {}, when(a.deadline_at)), h("td", {}, a.reminded ? "yes" : "no")))))) : h("p", { class: "muted" }, "None yet."),
      h("h2", {}, "Quotes"),
      (o.quotes || []).length ? o.quotes.map((q) => h("div", { class: "card" },
        h("div", {}, `${q.manufacturer_id}: `, q.prices.map((p) => `${p.unit_price} ${p.currency || "?"}${p.quantity ? ` @ ${p.quantity} pcs` : ""} (${p.status})`).join(", ")),
        h("div", { class: "muted" }, `MOQ ${q.moq ?? "?"} · lead time ${q.lead_time_days ?? "?"} days · expires ${when(q.expires_at)}${q.expired ? " · EXPIRED" : ""}`),
        q.sample_terms ? h("div", {}, `Samples: ${q.sample_terms}`) : null,
        h("div", { class: "muted" }, q.summary),
      )) : h("p", { class: "muted" }, "No quotes yet."),
    ),
    h("div", { class: "card" },
      h("h2", {}, `Spec (version ${spec.version ?? "-"}${spec.frozen ? ", frozen" : ""})`),
      h("div", { class: "muted" }, `${spec.option || ""} · ${spec.quantity ?? "?"} pcs`),
      kv(spec.answers),
      o.pre_receipt ? h("pre", {}, o.pre_receipt) : null,
    ),
    h("div", { class: "card" },
      h("h2", {}, "Customer conversation"),
      (o.messages || []).length ? o.messages.map((m) => h("p", {}, h("strong", {}, `${m.role}: `), m.content)) : h("p", { class: "muted" }, "No messages."),
    ),
  );
}

async function pageOutbox() {
  const messages = await api("/team/outbox");
  show(
    h("h1", {}, "Outbox"),
    h("p", { class: "muted" }, "Copy each message into WeChat (or email), send it, then mark it as sent."),
    messages.length ? messages.map((m) => {
      const copy = h("button", { class: "secondary" }, "Copy");
      copy.addEventListener("click", async () => { await navigator.clipboard.writeText(m.text); copy.textContent = "Copied"; });
      const sent = h("button", {}, "Mark as sent");
      sent.addEventListener("click", async () => { await api(`/team/outbox/${encodeURIComponent(m.id)}/sent`, { method: "POST" }); route(); });
      return h("div", { class: "card" },
        h("div", { class: "row" }, h("strong", {}, m.manufacturer), h("span", { class: "muted" }, m.contact || "no contact saved"),
          h("a", { href: `#/order/${m.order_id}` }, m.order_id), h("span", { class: "muted" }, when(m.created_at))),
        h("pre", {}, m.text), h("div", { class: "row" }, copy, sent));
    }) : h("p", { class: "muted" }, "Nothing to send."),
  );
}

async function pageManufacturers() {
  const rows = await api("/team/manufacturers");
  const f = { id: h("input", { placeholder: "id, e.g. ningbo-knit" }), name: h("input", { placeholder: "Name" }),
    contact: h("input", { placeholder: "WeChat / email" }), market: h("input", { placeholder: "market", value: "apparel" }),
    option: h("input", { placeholder: "option (empty = all)" }), rank: h("input", { type: "number", value: "1", min: "1" }) };
  const msg = h("div");
  const add = h("button", {}, "Add / update");
  add.addEventListener("click", async () => {
    try {
      await api("/team/manufacturers", { method: "POST", body: { id: f.id.value, name: f.name.value, contact: f.contact.value || null,
        market: f.market.value, option: f.option.value || null, rank: Number(f.rank.value) } });
      route();
    } catch (e) { msg.replaceChildren(errorBox(e.message)); }
  });
  show(
    h("h1", {}, "Manufacturers"),
    h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, ["Market / option", "Rank", "Id", "Name", "Contact"].map((t) => h("th", {}, t)))),
      h("tbody", {}, rows.map((r) => h("tr", {}, h("td", {}, `${r.market || "-"} / ${r.option || "*"}`), h("td", {}, r.rank ?? ""),
        h("td", {}, r.id), h("td", {}, r.name), h("td", {}, r.contact || ""))))),
    ),
    me.role === "admin" ? h("div", { class: "card" }, h("h2", {}, "Add a manufacturer (rank 1 = contacted first)"),
      h("div", { class: "row" }, ...Object.values(f), add), msg) : null,
  );
}

async function pageTeam() {
  const rows = await api("/team/members");
  const email = h("input", { type: "email", placeholder: "email" });
  const name = h("input", { placeholder: "name" });
  const role = h("select", {}, h("option", { value: "agent" }, "agent"), h("option", { value: "admin" }, "admin"));
  const msg = h("div");
  const add = h("button", {}, "Add member");
  add.addEventListener("click", async () => {
    try { await api("/team/members", { method: "POST", body: { email: email.value, name: name.value || null, role: role.value } }); route(); }
    catch (e) { msg.replaceChildren(errorBox(e.message)); }
  });
  show(
    h("h1", {}, "Team"),
    h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, ["Email", "Name", "Role", "Last login"].map((t) => h("th", {}, t)))),
      h("tbody", {}, rows.map((m) => h("tr", {}, h("td", {}, m.email), h("td", {}, m.name || ""), h("td", {}, m.role), h("td", { class: "muted" }, when(m.last_login_at))))))),
    h("div", { class: "card" }, h("h2", {}, "Add a member"), h("div", { class: "row" }, email, name, role, add), msg),
  );
}

// --- help requests ------------------------------------------------------------------------
const TOPICS = { order: "Order question", change: "Change / cancellation", price: "Price / quote", delivery: "Delivery / goods",
  account: "Account", other: "Other" };
const REQUEST_STATUS = { open: "Open (team's turn)", waiting_customer: "Waiting for the customer", resolved: "Resolved" };

async function pageSupport() {
  const rows = await api("/team/support");
  show(
    h("h1", {}, "Help requests"),
    h("p", { class: "muted" }, "Customers' questions. People answer these, never the AI. Price or change requests: never promise anything the team has not agreed."),
    rows.length ? h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, ["#", "Customer", "Topic", "Order", "Status", "Last message", "Updated"].map((t) => h("th", {}, t)))),
      h("tbody", {}, rows.map((r) => h("tr", { class: "click", on: { click: () => (location.hash = `#/request/${r.id}`) } },
        h("td", {}, r.ref), h("td", {}, r.customer_email), h("td", {}, TOPICS[r.topic] || r.topic), h("td", {}, r.order_id || ""),
        h("td", {}, r.status === "open" ? h("span", { class: "flag" }, REQUEST_STATUS[r.status]) : REQUEST_STATUS[r.status]),
        h("td", {}, `${r.last_author === "team" ? "Team: " : ""}${(r.last_message || "").slice(0, 80)}`),
        h("td", { class: "muted" }, when(r.updated_at)),
      ))),
    )) : h("p", { class: "muted" }, "No requests yet."),
  );
}

async function pageRequest(id) {
  const r = await api(`/team/support/${encodeURIComponent(id)}`);
  const body = h("textarea", { placeholder: "Reply to the customer (shown in their Messages and Help pages)" });
  const status = h("select", {}, Object.entries(REQUEST_STATUS).map(([k, v]) =>
    h("option", { value: k, selected: k === "waiting_customer" }, v)));
  const msg = h("div");
  const send = h("button", {}, "Send");
  send.addEventListener("click", async () => {
    try { await api(`/team/support/${encodeURIComponent(id)}/reply`, { method: "POST", body: { body: body.value, status: status.value } }); route(); }
    catch (e) { msg.replaceChildren(errorBox(e.message)); }
  });
  show(
    h("p", {}, h("a", { href: "#/support" }, "← back")),
    h("h1", {}, `Request #${r.ref} · ${TOPICS[r.topic] || r.topic}`),
    h("div", { class: "card" },
      h("div", { class: "row" }, h("strong", {}, "Customer:"), r.customer_email, h("strong", {}, "Status:"), REQUEST_STATUS[r.status],
        r.order_id ? h("a", { href: `#/order/${r.order_id}` }, `Order ${r.order_id}`) : null),
      Object.keys(r.context || {}).length ? kv(r.context) : null,
    ),
    h("div", { class: "card" }, r.messages.map((m) => h("div", { class: "msg" },
      h("div", { class: "muted" }, `${m.author === "team" ? "Team" : "Customer"} · ${when(m.created_at)}`), h("pre", {}, m.body)))),
    h("div", { class: "card" }, h("h2", {}, "Reply"), body, h("div", { class: "row" }, "Then mark as:", status, send), msg),
  );
}

// --- routing --------------------------------------------------------------------------
async function route() {
  if (!token) return renderLogin();
  const path = location.hash.replace(/^#/, "") || "/attention";
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${path}`));
  try {
    if (path.startsWith("/order/")) return await pageOrder(decodeURIComponent(path.slice(7)));
    if (path.startsWith("/request/")) return await pageRequest(decodeURIComponent(path.slice(9)));
    const pages = { "/attention": pageAttention, "/orders": pageOrders, "/support": pageSupport, "/outbox": pageOutbox,
      "/manufacturers": pageManufacturers, "/team": pageTeam };
    await (pages[path] || pageAttention)();
  } catch (e) {
    if (token) show(errorBox(e.message));
  }
}

function start() {
  document.getElementById("nav").hidden = false;
  document.querySelectorAll("[data-admin]").forEach((a) => (a.hidden = me.role !== "admin"));
  document.getElementById("who").textContent = `${me.email} (${me.role})`;
  route();
}

window.addEventListener("hashchange", route);
refresh().then((ok) => (ok ? start() : renderLogin()));
