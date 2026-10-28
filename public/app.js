const STORAGE_KEY = "briefboard.state.v1";
const NOTES_KEY = "briefboard.notes.v1";

const state = { board: null, metrics: null, playbook: null, editing: null };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const el = (tag, props = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== null && value !== undefined && value !== false) node.setAttribute(key, value === true ? "" : value);
  }
  for (const kid of kids.flat()) {
    if (kid !== null && kid !== undefined && kid !== false) node.append(kid);
  }
  return node;
};

const debounce = (fn, wait) => {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
};

const toast = (message, error = false) => {
  const box = $("#toast");
  box.textContent = message;
  box.className = error ? "toast error" : "toast";
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (box.hidden = true), 3200);
};

const api = async (path, body, method = body ? "POST" : "GET") => {
  const response = await fetch(`/api/${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]) detail = data.detail[0].msg;
    } catch {}
    throw new Error(detail);
  }
  return response;
};

const store = {
  read(key) {
    try {
      return JSON.parse(localStorage.getItem(key));
    } catch {
      return null;
    }
  },
  write(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {}
  },
};

const persist = () => store.write(STORAGE_KEY, state.board);

const initials = (name) =>
  name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

const formatDue = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short" }).format(new Date(y, m - 1, d));
};

const isLate = (card) => {
  if (!card.due || card.column === "done") return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const [y, m, d] = card.due.split("-").map(Number);
  return new Date(y, m - 1, d) < today;
};

const renderKpis = () => {
  const m = state.metrics;
  const box = $("#kpis");
  box.replaceChildren();
  if (!m) return;
  const items = [
    ["Cards", m.total, false],
    ["Story points", m.points, false],
    ["Complete", `${m.completion}%`, false],
    ["Overdue", m.overdue, m.overdue > 0],
    ["Blocked", m.blocked, m.blocked > 0],
  ];
  for (const [label, value, alert] of items) {
    box.append(el("div", { class: alert ? "kpi alert" : "kpi" }, el("b", {}, String(value)), el("span", {}, label)));
  }
};

const cardNode = (card) => {
  const meta = [el("span", { class: card.owner ? "avatar" : "avatar none", title: card.owner || "Unassigned" }, card.owner ? initials(card.owner) : "?")];
  if (card.due) meta.push(el("span", { class: isLate(card) ? "chip due late" : "chip due" }, formatDue(card.due)));
  meta.push(el("span", { class: card.moscow === "Must" ? "chip must" : "chip" }, card.moscow));
  for (const label of card.labels.slice(0, 3)) {
    meta.push(el("span", { class: label === "blocked" ? "chip blocked" : "chip" }, label));
  }
  meta.push(el("span", { class: "chip pts", title: "Story points" }, `${card.points} pts`));

  return el(
    "article",
    {
      class: "card",
      draggable: "true",
      tabindex: "0",
      "data-id": card.id,
      "data-priority": card.priority,
      onclick: () => openEditor(card.id),
      onkeydown: (event) => {
        if (event.key === "Enter") openEditor(card.id);
      },
      ondragstart: (event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", card.id);
        event.currentTarget.classList.add("dragging");
      },
      ondragend: (event) => {
        event.currentTarget.classList.remove("dragging");
        $$(".col").forEach((col) => col.classList.remove("drop"));
        syncFromDom();
      },
    },
    el(
      "div",
      { class: "card-top" },
      el("span", { class: "card-id" }, card.id),
      el("span", { class: card.kind === "bug" ? "chip kind-bug" : "chip" }, card.kind),
    ),
    el("p", { class: "card-title" }, card.title),
    el("div", { class: "card-meta" }, meta),
  );
};

const dragAfter = (container, y) => {
  const others = [...container.querySelectorAll(".card:not(.dragging)")];
  let best = { offset: Number.NEGATIVE_INFINITY, node: null };
  for (const node of others) {
    const box = node.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > best.offset) best = { offset, node };
  }
  return best.node;
};

const renderBoard = () => {
  const board = $("#board");
  board.replaceChildren();
  if (!state.board) {
    board.append(
      el(
        "div",
        { class: "empty" },
        el("h3", {}, "No board yet"),
        el("p", {}, "Paste your meeting notes on the left and generate a board. Try one of the samples to see how it works."),
      ),
    );
    return;
  }
  const metricsByCol = new Map((state.metrics?.columns || []).map((c) => [c.id, c]));
  board.style.gridTemplateColumns = `repeat(${state.board.columns.length}, minmax(220px, 1fr))`;

  for (const column of state.board.columns) {
    const cards = state.board.cards.filter((c) => c.column === column.id);
    const over = Boolean(column.wip && cards.length > column.wip);
    const body = el("div", { class: "col-body" }, cards.map(cardNode));
    const section = el(
      "section",
      {
        class: "col",
        "data-col": column.id,
        ondragover: (event) => {
          event.preventDefault();
          section.classList.add("drop");
          const dragging = document.querySelector(".card.dragging");
          if (!dragging) return;
          const after = dragAfter(body, event.clientY);
          if (after) body.insertBefore(dragging, after);
          else body.append(dragging);
        },
        ondragleave: (event) => {
          if (!section.contains(event.relatedTarget)) section.classList.remove("drop");
        },
        ondrop: (event) => event.preventDefault(),
      },
      el(
        "div",
        { class: "col-head" },
        el("h3", {}, column.title),
        el("span", { class: over ? "count over" : "count" }, String(cards.length)),
        el("button", { class: "add", title: `Add card to ${column.title}`, "aria-label": `Add card to ${column.title}`, onclick: () => addCard(column.id) }, "+"),
      ),
      column.wip
        ? el("div", { class: over ? "wip-note over" : "wip-note" }, `WIP limit ${column.wip}${over ? " exceeded" : ""}`)
        : metricsByCol.get(column.id)
          ? el("div", { class: "wip-note" }, `${metricsByCol.get(column.id).points} pts`)
          : null,
      body,
    );
    board.append(section);
  }
};

const bars = (rows, max) =>
  rows.map(([label, value, suffix]) =>
    el(
      "div",
      { class: "bar-row" },
      el("span", {}, label),
      el("div", { class: "bar" }, el("i", { style: `width:${max ? Math.max(4, (value / max) * 100) : 0}%` })),
      el("em", {}, suffix ?? String(value)),
    ),
  );

const MOSCOW_COLORS = { Must: "#7a0f1e", Should: "#b5651d", Could: "#b89b5e", "Won't": "#b2b8bc" };
const MOSCOW_ORDER = Object.keys(MOSCOW_COLORS);

const renderInsights = () => {
  const pane = $("#pane-insights");
  pane.replaceChildren();
  const m = state.metrics;
  if (!m) {
    pane.append(el("p", { class: "hint" }, "Insights appear once a board is generated."));
    return;
  }
  const maxCol = Math.max(1, ...m.columns.map((c) => c.points));
  const maxOwner = Math.max(1, ...m.owners.map((o) => o.points));
  const moscowTotal = Object.values(m.moscow).reduce((a, b) => a + b, 0) || 1;
  const moscowEntries = MOSCOW_ORDER.filter((key) => m.moscow[key]).map((key) => [key, m.moscow[key]]);
  const stack = el(
    "div",
    { class: "stack" },
    moscowEntries.map(([key, value]) => el("i", { style: `width:${(value / moscowTotal) * 100}%;background:${MOSCOW_COLORS[key] || "#999"}` })),
  );
  const legend = el(
    "div",
    { class: "legend" },
    moscowEntries.map(([key, value]) => el("span", { style: `--c:${MOSCOW_COLORS[key] || "#999"}` }, `${key} ${value}`)),
  );

  pane.append(
    el(
      "div",
      { class: "grid" },
      el("div", { class: "tile wide" }, el("h3", {}, "Coach notes"), el("ul", { class: "advice" }, m.suggestions.map((s) => el("li", {}, s)))),
      el("div", { class: "tile" }, el("h3", {}, "Points by column"), bars(m.columns.map((c) => [c.title, c.points, `${c.points} pts`]), maxCol)),
      el(
        "div",
        { class: "tile" },
        el("h3", {}, "Open workload by owner"),
        bars(m.owners.map((o) => [o.owner, o.points, `${o.points} pts`]), maxOwner),
      ),
      el("div", { class: "tile" }, el("h3", {}, "MoSCoW scope"), stack, legend),
      state.board.method === "scrum"
        ? el(
            "div",
            { class: "tile" },
            el("h3", {}, "Sprint capacity"),
            bars([["Committed", m.committed, `${m.committed} / ${m.velocity}`]], Math.max(m.velocity, m.committed)),
          )
        : null,
    ),
  );
};

const listTile = (title, items) =>
  el("div", { class: "tile" }, el("h3", {}, title), items.length ? el("ul", {}, items.map((i) => el("li", {}, i))) : el("p", {}, "None captured."));

const renderNotes = () => {
  const pane = $("#pane-notes");
  pane.replaceChildren();
  if (!state.board) {
    pane.append(el("p", { class: "hint" }, "Decisions, risks and open questions are collected here."));
    return;
  }
  pane.append(
    el(
      "div",
      { class: "grid" },
      listTile("Decisions", state.board.decisions),
      listTile("Risks", state.board.risks),
      listTile("Open questions", state.board.questions),
    ),
  );
};

const renderPlaybook = () => {
  const pane = $("#pane-playbook");
  pane.replaceChildren();
  if (!state.playbook) return;
  pane.append(
    el(
      "div",
      { class: "grid" },
      state.playbook.map((entry) =>
        el(
          "div",
          { class: "tile" },
          el("span", { class: "tag" }, entry.tag),
          el("h3", {}, entry.title),
          el("p", {}, entry.body),
          el("ul", {}, entry.points.map((p) => el("li", {}, p))),
        ),
      ),
    ),
  );
};

const render = () => {
  renderKpis();
  renderBoard();
  renderInsights();
  renderNotes();
};

const mergeScores = (fresh) => {
  const byId = new Map(fresh.board.cards.map((c) => [c.id, c]));
  for (const card of state.board.cards) {
    const match = byId.get(card.id);
    if (match) {
      card.score = match.score;
      card.moscow = match.moscow;
    }
  }
  state.metrics = fresh.metrics;
};

const refresh = async () => {
  if (!state.board) return;
  try {
    const response = await api("refresh", state.board);
    mergeScores(await response.json());
    persist();
    render();
  } catch (error) {
    toast(error.message, true);
  }
};

const scheduleRefresh = debounce(refresh, 150);

const syncFromDom = () => {
  if (!state.board) return;
  const byId = new Map(state.board.cards.map((c) => [c.id, c]));
  const next = [];
  $$(".col").forEach((col) => {
    col.querySelectorAll(".card").forEach((node) => {
      const card = byId.get(node.dataset.id);
      if (card) {
        card.column = col.dataset.col;
        next.push(card);
      }
    });
  });
  state.board.cards = next;
  persist();
  scheduleRefresh();
};

const nextId = () => {
  const used = state.board.cards.map((c) => Number(c.id.replace(/\D/g, "")) || 0);
  return `BB-${String(Math.max(0, ...used) + 1).padStart(2, "0")}`;
};

const addCard = (columnId) => {
  const card = { id: nextId(), title: "New card", owner: null, due: null, priority: "medium", kind: "task", points: 3, column: columnId, labels: [], moscow: "Should", score: 0, source: "" };
  state.board.cards.push(card);
  persist();
  render();
  openEditor(card.id, true);
};

const editor = $("#editor");
const form = $("#editor-form");

function openEditor(id, isNew = false) {
  const card = state.board.cards.find((c) => c.id === id);
  if (!card) return;
  state.editing = { id, isNew };
  $("#editor-title").textContent = `${card.id}`;
  const select = form.elements.column;
  select.replaceChildren(...state.board.columns.map((c) => el("option", { value: c.id }, c.title)));
  form.elements.title.value = card.title;
  form.elements.owner.value = card.owner || "";
  form.elements.due.value = card.due || "";
  form.elements.priority.value = card.priority;
  form.elements.kind.value = card.kind;
  form.elements.points.value = String(card.points);
  form.elements.column.value = card.column;
  form.elements.labels.value = card.labels.join(", ");
  editor.showModal();
  form.elements.title.focus();
  form.elements.title.select();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const card = state.board.cards.find((c) => c.id === state.editing.id);
  const data = new FormData(form);
  card.title = String(data.get("title")).trim() || card.title;
  card.owner = String(data.get("owner")).trim() || null;
  card.due = String(data.get("due")) || null;
  card.priority = data.get("priority");
  card.kind = data.get("kind");
  card.points = Number(data.get("points"));
  card.column = data.get("column");
  card.labels = String(data.get("labels"))
    .split(",")
    .map((l) => l.trim().toLowerCase())
    .filter(Boolean)
    .slice(0, 5);
  editor.close();
  persist();
  render();
  scheduleRefresh();
});

$("#editor-cancel").addEventListener("click", () => {
  if (state.editing?.isNew) {
    state.board.cards = state.board.cards.filter((c) => c.id !== state.editing.id);
    persist();
    render();
  }
  editor.close();
});

$("#editor-delete").addEventListener("click", () => {
  state.board.cards = state.board.cards.filter((c) => c.id !== state.editing.id);
  editor.close();
  persist();
  render();
  scheduleRefresh();
});

const setEngine = (engine) => {
  const badge = $("#engine");
  badge.hidden = !engine;
  badge.textContent = engine === "llm" ? "LLM assisted" : "Rule engine";
};

const generate = async () => {
  const notes = $("#notes").value.trim();
  if (!notes) {
    toast("Paste some meeting notes first.", true);
    return;
  }
  const button = $("#generate");
  button.disabled = true;
  button.textContent = "Analysing...";
  try {
    const response = await api("analyze", {
      notes,
      method: $("#method").value,
      velocity: Number($("#velocity").value) || 20,
    });
    const data = await response.json();
    state.board = data.board;
    state.metrics = data.metrics;
    store.write(NOTES_KEY, notes);
    persist();
    setEngine(data.engine);
    render();
    toast(`${data.board.cards.length} cards created.`);
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "Generate board";
  }
};

const switchMethod = async () => {
  const method = $("#method").value;
  $("#velocity-field").hidden = method !== "scrum";
  if (!state.board) return;
  try {
    const response = await api("method", { board: state.board, method, velocity: Number($("#velocity").value) || 20 });
    const data = await response.json();
    state.board = data.board;
    state.metrics = data.metrics;
    persist();
    render();
  } catch (error) {
    toast(error.message, true);
  }
};

const exportBoard = async (format) => {
  if (!state.board) {
    toast("Generate a board before exporting.", true);
    return;
  }
  try {
    const response = await api("export", { board: state.board, format });
    const blob = await response.blob();
    const extension = format === "markdown" ? "md" : format;
    const link = el("a", { href: URL.createObjectURL(blob), download: `briefboard.${extension}` });
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  } catch (error) {
    toast(error.message, true);
  }
};

const loadSample = async (lang) => {
  try {
    const response = await api(`sample?lang=${lang}`);
    $("#notes").value = (await response.json()).notes;
  } catch (error) {
    toast(error.message, true);
  }
};

$("#generate").addEventListener("click", generate);
$("#method").addEventListener("change", switchMethod);
$("#velocity").addEventListener("change", switchMethod);
$("#print").addEventListener("click", () => window.print());
$$("[data-export]").forEach((b) => b.addEventListener("click", () => exportBoard(b.dataset.export)));
$$("[data-sample]").forEach((b) => b.addEventListener("click", () => loadSample(b.dataset.sample)));
$("#notes").addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") generate();
});

$$(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    $$(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    $$(".tabpane").forEach((pane) => (pane.hidden = pane.id !== `pane-${tab.dataset.tab}`));
  }),
);

const boot = async () => {
  const savedNotes = store.read(NOTES_KEY);
  if (savedNotes) $("#notes").value = savedNotes;
  const saved = store.read(STORAGE_KEY);
  if (saved && Array.isArray(saved.cards) && Array.isArray(saved.columns)) {
    state.board = saved;
    $("#method").value = saved.method;
    $("#velocity").value = saved.velocity;
    $("#velocity-field").hidden = saved.method !== "scrum";
  }
  render();
  try {
    state.playbook = await (await api("playbook")).json();
    renderPlaybook();
  } catch {}
  if (state.board) refresh();
};

boot();
