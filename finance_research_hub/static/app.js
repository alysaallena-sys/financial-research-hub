/* Financial Research Hub — local, read-only UI. No third-party scripts. */
"use strict";
(() => {
  const RISK = "投资有风险，分析结果和查询结果不构成投资建议。";
  const KIND = {news: "公开资讯", research: "券商研报", rating: "评级变化", talk: "TED 与演讲"};
  const DESCRIPTIONS = {
    "": "查看公开资讯、研报目录与评级记录，沿来源继续研究。",
    news: "查看本地收录的公开资讯，按来源与主题筛选。",
    research: "查看研报目录、发布机构与评级，打开原始来源核对。",
    rating: "查看数据源收录的机构评级事件，区分事件与市场共识。",
    talk: "查看公开演讲与 TED 条目，保留原始页面与发表时间。"
  };
  const $ = (id) => document.getElementById(id);
  const state = {kind: "", items: [], sources: [], changes: [], request: 0, demo: false, libraryMode: null, toastTimer: null};
  const statusLabels = {ready: "可查询", available: "接口已配置", enabled: "已配置", disabled: "未启用", candidate: "候选", demo: "合成演示", not_collected: "尚未采集", unavailable: "不可用", optional: "可选依赖", optional_dependency: "需可选依赖", reference_only: "参考入口", configured: "已配置", success: "已采集", ok: "已配置"};

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function cleanText(value, fallback = "") {
    if (value === undefined || value === null) return fallback;
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }
  function safeUrl(value) {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password ? url.href : null;
    } catch { return null; }
  }
  function sourceLink(url, text, className) {
    const href = safeUrl(url);
    const node = element(href ? "a" : "span", className, text);
    if (href) { node.href = href; node.target = "_blank"; node.rel = "noopener noreferrer"; }
    return node;
  }
  function dateText(value, detailed = false) {
    if (!value) return "发表时间未提供";
    const raw = cleanText(value);
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return raw;
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
    const options = detailed ? {year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false} : {year: "numeric", month: "2-digit", day: "2-digit"};
    return date.toLocaleString("zh-CN", options);
  }
  function asList(payload, keys = ["items", "sources", "changes", "records"]) {
    if (Array.isArray(payload)) return payload;
    for (const key of keys) if (Array.isArray(payload?.[key])) return payload[key];
    return [];
  }
  async function request(path) {
    const response = await fetch(path, {headers: {Accept: "application/json"}, credentials: "same-origin", cache: "no-store"});
    if (!response.ok) {
      let detail = "";
      try { const error = await response.json(); detail = error.error || error.message || ""; } catch {}
      throw new Error(detail || `本地服务返回 ${response.status}。请确认服务仍在运行后重试。`);
    }
    return response.json();
  }
  function toast(message) {
    clearTimeout(state.toastTimer);
    $("toast").textContent = message;
    $("toast").hidden = false;
    state.toastTimer = setTimeout(() => { $("toast").hidden = true; }, 5000);
  }
  function params() {
    const query = new URLSearchParams({limit: "100"});
    if (state.kind) query.set("kind", state.kind);
    const q = $("query-input").value.trim();
    const symbol = $("symbol-input").value.trim();
    const provider = $("provider-select").value;
    if (q) query.set("q", q);
    if (symbol) query.set("symbol", symbol);
    if (provider) query.set("provider", provider);
    return query;
  }
  function busy(active) {
    $("refresh-button").disabled = active;
    $("loading-state").hidden = !active;
    $("results-list").setAttribute("aria-busy", String(active));
    if (active) {
      $("empty-state").hidden = true;
      $("error-box").hidden = true;
      $("results-status").textContent = "正在读取本地记录…";
    }
  }
  function setKind(kind) {
    state.kind = kind;
    document.querySelectorAll("[data-kind]").forEach((button) => {
      const active = button.dataset.kind === kind;
      button.classList.toggle("is-active", active);
      if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    });
    document.querySelectorAll("[data-filter-kind]").forEach((button) => {
      const active = button.dataset.filterKind === kind;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    $("page-title").textContent = kind ? KIND[kind] : "研究总览";
    $("page-description").textContent = DESCRIPTIONS[kind];
    loadItems();
  }
  function renderItems(payload) {
    const items = asList(payload);
    state.items = items;
    const list = $("results-list");
    list.replaceChildren();
    items.forEach((item) => {
      const row = element("li", "result-item");
      const top = element("div", "result-topline");
      top.append(element("span", `kind-tag ${item.kind || ""}`, KIND[item.kind] || "资料"));
      if (item.is_demo) top.append(element("span", "demo-tag", "合成样例"));
      if (item.symbol) top.append(element("span", "symbol-tag", item.symbol));
      top.append(element("span", "source-inline", item.provider || item.source || "来源未提供"));
      const heading = element("h3", "result-title");
      heading.append(sourceLink(item.url, item.title || "未命名记录"));
      const meta = element("div", "result-meta");
      meta.append(element("span", "", item.institution || item.source || "机构未提供"));
      meta.append(element("span", "", dateText(item.published_at)));
      if (safeUrl(item.url)) meta.append(element("span", "", "原始来源 ↗"));
      row.append(top, heading, meta);
      const details = element("details", "result-details");
      details.append(element("summary", "", "摘要与来源信息"));
      const body = element("div", "detail-body");
      body.append(element("p", "", item.summary || "此记录仅含目录信息。请打开原始来源核对正文。"));
      const metadata = item.metadata && typeof item.metadata === "object" ? item.metadata : {};
      if (item.kind === "rating") {
        const from = metadata.rating_from || metadata.from_grade || metadata.from_rating || metadata.FromGrade || "未提供";
        const to = metadata.rating_to || metadata.to_grade || metadata.to_rating || metadata.ToGrade || "未提供";
        if (from !== "未提供" || to !== "未提供") body.append(element("p", "rating-delta", `评级记录：${from} → ${to}`));
      }
      const grid = element("dl", "metadata-grid");
      const fields = [["直接提供方", item.provider || "未提供"], ["原始来源", item.source || "未提供"], ["收录时间", item.retrieved_at ? dateText(item.retrieved_at, true) : "未提供"]];
      if (metadata.coverage) fields.push(["覆盖范围", metadata.coverage]);
      if (metadata.truncated !== undefined) fields.push(["结果截断", metadata.truncated ? "是，可能存在更多记录" : "未标记截断"]);
      if (metadata.adjustment) fields.push(["复权口径", metadata.adjustment]);
      for (const [label, value] of fields) { grid.append(element("dt", "", label), element("dd", "", cleanText(value))); }
      body.append(grid, element("p", "item-risk", RISK));
      details.append(body); row.append(details); list.append(row);
    });
    const count = Number.isFinite(payload?.count) ? payload.count : items.length;
    $("result-count").textContent = `${count} 条`;
    $("metric-total").textContent = String(count);
    $("metric-research").textContent = String(items.filter((x) => x.kind === "research").length);
    $("metric-rating").textContent = String(items.filter((x) => x.kind === "rating").length);
    $("metric-scope").textContent = "本次查询最多返回 100 条";
    $("results-status").textContent = count > items.length ? `显示 ${items.length} 条，共匹配 ${count} 条` : `返回 ${items.length} 条 · 每次最多 100 条`;
    $("empty-state").hidden = items.length !== 0;
    $("empty-message").textContent = params().has("q") || params().has("kind") || params().has("provider") || params().has("symbol") ? "调整关键词、来源或证券标识后重试。" : "本地库还没有记录。请先通过命令行导入演示数据或采集获准的公开来源。";
    state.demo = payload?.mode === "demo" || payload?.mode === "mixed" || payload?.is_demo === true || items.some((x) => x.is_demo) || state.libraryMode === "demo" || state.libraryMode === "mixed";
    updateDemoBanner();
    $("last-read").textContent = `读取于 ${new Date().toLocaleTimeString("zh-CN", {hour: "2-digit", minute: "2-digit", hour12: false})}`;
    updateProviders(items);
  }
  function updateProviders(items) {
    const select = $("provider-select");
    const existing = new Set([...select.options].map((x) => x.value));
    const names = new Set(items.map((item) => item.provider).filter(Boolean));
    for (const source of state.sources) if (source.id || source.provider) names.add(source.id || source.provider);
    [...names].sort().forEach((name) => {
      const source = state.sources.find((entry) => (entry.id || entry.provider) === name);
      const label = source?.name || source?.label || name;
      if (!existing.has(name)) select.append(new Option(label, name));
      else [...select.options].find((option) => option.value === name).textContent = label;
    });
  }
  async function loadItems() {
    const seq = ++state.request;
    $("brief-text").hidden = true;
    $("brief-placeholder").hidden = false;
    $("brief-placeholder").textContent = "从当前查询整理信息分布与来源记录。";
    busy(true);
    try {
      const payload = await request(`/api/items?${params()}`);
      if (seq !== state.request) return;
      $("error-box").hidden = true;
      renderItems(payload);
    } catch (error) {
      if (seq !== state.request) return;
      $("results-list").replaceChildren();
      $("empty-state").hidden = true;
      $("error-message").textContent = error.message;
      $("error-box").hidden = false;
      $("results-status").textContent = "读取失败 · 可点击重新读取";
      $("result-count").textContent = "读取失败";
      ["metric-total", "metric-research", "metric-rating"].forEach((id) => { $(id).textContent = "—"; });
      $("metric-scope").textContent = "未取得查询结果";
    } finally { if (seq === state.request) busy(false); }
  }
  function coverageText(value) {
    if (!value) return "覆盖范围尚未提供；目录不代表已采集。";
    if (typeof value === "string") return value;
    return Object.entries(value).map(([key, val]) => `${key}：${cleanText(val)}`).join("；");
  }
  function updateDemoBanner() {
    const banner = $("demo-banner");
    banner.hidden = !state.demo;
    if (state.libraryMode === "mixed") {
      banner.children[0].textContent = "本地库含合成演示数据";
      banner.children[1].textContent = "合成条目带有独立标记，请与真实来源记录分别使用。";
    } else {
      banner.children[0].textContent = "合成演示数据";
      banner.children[1].textContent = "当前内容用于演示工作流程，不代表真实新闻、机构观点或行情。";
    }
  }
  function renderSources(payload) {
    const sources = asList(payload, ["sources", "items", "providers"]);
    state.sources = sources;
    const list = $("sources-list"); list.replaceChildren();
    if (!sources.length) list.append(element("li", "context-empty", "尚未提供来源状态。"));
    sources.forEach((source) => {
      const li = element("li"); const heading = element("div", "source-heading");
      const rawStatus = source.status || (source.enabled === false ? "disabled" : "candidate");
      heading.append(element("span", "", source.name || source.label || source.id || source.provider || "未命名来源"), element("span", "source-status", statusLabels[rawStatus] || cleanText(rawStatus)));
      li.append(heading, element("p", "source-description", source.description || coverageText(source.coverage)));
      if (source.limitations || source.caveats || source.note) li.append(element("p", "source-description", cleanText(source.limitations || source.caveats || source.note)));
      const collected = source.last_collection;
      if (collected) {
        const facts = element("ul", "coverage-list");
        if (collected.observed_at) facts.append(element("li", "", `最近采集：${dateText(collected.observed_at, true)}`));
        if (Number.isFinite(collected.returned_records)) facts.append(element("li", "", `该次返回：${collected.returned_records} 条`));
        if (Number.isFinite(collected.fetched_pages)) facts.append(element("li", "", `已取 ${collected.fetched_pages} 页${Number.isFinite(collected.reported_total_pages) ? ` / 来源报告 ${collected.reported_total_pages} 页` : "，来源总页数未提供"}`));
        facts.append(element("li", "", collected.truncated === true ? "结果有截断，可能存在更多记录" : collected.truncated === false ? "本次查询未标记截断；不代表来源全量覆盖" : "完整性未知，仅覆盖本次来源窗口"));
        li.append(facts);
      } else li.append(element("p", "source-description", "尚无本地采集记录。"));
      const url = source.url || source.homepage || source.source_url;
      if (safeUrl(url)) li.append(sourceLink(url, "查看来源说明 ↗", "source-link"));
      list.append(li);
    });
    updateProviders(state.items);
  }
  function renderChanges(payload) {
    const changes = asList(payload, ["items", "changes", "records"]);
    state.changes = changes;
    const list = $("changes-list"); list.replaceChildren();
    $("metric-changes").textContent = String(payload?.count ?? changes.length);
    $("changes-count").textContent = String(payload?.count ?? changes.length);
    if (!changes.length) list.append(element("li", "context-empty", "暂无已记录的新增或更新。重复读取相同内容不会新增变更。"));
    changes.slice(0, 5).forEach((change) => {
      const item = change.item || change.record || change.current || change;
      const type = change.change_type || change.type || change.change || "new";
      const li = element("li"); const label = element("div", "change-label");
      label.append(element("span", `change-badge ${type === "updated" ? "updated" : ""}`, type === "updated" ? "更新" : type === "unchanged" ? "未变化" : "新增"));
      label.append(element("span", "", KIND[item.kind] || item.provider || "本地记录"));
      const title = element("p", "change-title"); title.append(sourceLink(item.url, item.title || change.title || item.id || "未命名记录"));
      li.append(label, title);
      const time = change.observed_at || change.detected_at || change.created_at || change.first_seen_at;
      if (time) li.append(element("span", "change-time", `观察于 ${dateText(time, true)}`));
      list.append(li);
    });
  }
  async function loadContext() {
    const results = await Promise.allSettled([request("/api/sources"), request("/api/changes"), request("/api/status")]);
    if (results[0].status === "fulfilled") renderSources(results[0].value);
    else $("sources-list").replaceChildren(element("li", "context-empty", "来源状态暂时不可用。刷新后重试。"));
    if (results[1].status === "fulfilled") renderChanges(results[1].value);
    else { $("changes-list").replaceChildren(element("li", "context-empty", "变更记录暂时不可用。")); $("metric-changes").textContent = "—"; }
    if (results[2].status === "fulfilled") {
      const status = results[2].value;
      state.libraryMode = status.mode || null;
      if (status.mode === "demo" || status.mode === "mixed" || status.is_demo === true) state.demo = true;
      updateDemoBanner();
    }
  }
  async function refresh() {
    await Promise.all([loadItems(), loadContext()]);
  }
  function clearFilters() {
    $("query-input").value = ""; $("symbol-input").value = ""; $("provider-select").value = "";
    setKind("");
  }
  async function loadBrief() {
    const button = $("brief-button"); button.disabled = true; button.textContent = "整理中…";
    const seq = state.request;
    try {
      const payload = await request(`/api/brief?${params()}`);
      if (seq !== state.request) { toast("查询条件已变化，请重新生成简报。"); return; }
      let text = typeof payload === "string" ? payload : payload.text || payload.brief || payload.markdown || payload.summary;
      if (typeof text !== "string") text = "本地简报尚未提供可展示的文本。";
      if (!text.includes(RISK)) text = `${RISK}\n\n${text}`;
      if (state.demo && !/演示|合成/.test(text)) text = `【合成演示数据】\n\n${text}`;
      $("brief-text").textContent = text; $("brief-text").hidden = false; $("brief-placeholder").hidden = true;
    } catch (error) { toast(`简报读取失败：${error.message}`); }
    finally { button.disabled = false; button.replaceChildren(document.createTextNode("更新 "), element("span", "", "↗")); }
  }
  async function exportData() {
    const button = $("export-button"); button.disabled = true;
    const format = $("export-format").value;
    try {
      const query = params(); query.set("format", format);
      const response = await fetch(`/api/export?${query}`, {credentials: "same-origin", cache: "no-store"});
      if (!response.ok) throw new Error(`导出失败（${response.status}）。请重试。`);
      const text = await response.text();
      let checkedText = text;
      if (format === "json") {
        try { checkedText = JSON.stringify(JSON.parse(text)); }
        catch { throw new Error("导出内容不是有效 JSON，已阻止下载。请重试。"); }
      }
      if (!checkedText.includes(RISK)) throw new Error("导出内容缺少风险提示，已阻止下载。请检查服务版本。");
      const mime = {json: "application/json;charset=utf-8", csv: "text/csv;charset=utf-8", markdown: "text/markdown;charset=utf-8"}[format];
      const blob = new Blob([text], {type: mime}); const url = URL.createObjectURL(blob);
      const anchor = element("a"); anchor.href = url; anchor.download = `financial-research-${new Date().toISOString().slice(0, 10)}.${format === "markdown" ? "md" : format}`;
      document.body.append(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast("已导出本次查询结果（最多 100 条）。接收的编辑器必须保留并显示风险提示。");
    } catch (error) { toast(error.message); }
    finally { button.disabled = false; }
  }

  document.querySelectorAll("[data-kind]").forEach((button) => button.addEventListener("click", () => setKind(button.dataset.kind)));
  document.querySelectorAll("[data-filter-kind]").forEach((button) => button.addEventListener("click", () => setKind(button.dataset.filterKind)));
  $("search-form").addEventListener("submit", (event) => { event.preventDefault(); loadItems(); });
  $("provider-select").addEventListener("change", loadItems);
  $("symbol-input").addEventListener("change", loadItems);
  $("clear-filters").addEventListener("click", clearFilters);
  $("empty-clear").addEventListener("click", clearFilters);
  $("refresh-button").addEventListener("click", refresh);
  $("retry-button").addEventListener("click", refresh);
  $("brief-button").addEventListener("click", loadBrief);
  $("export-button").addEventListener("click", exportData);
  refresh();
})();
