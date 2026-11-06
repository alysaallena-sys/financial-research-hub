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
  const state = {kind: "", items: [], sources: [], changes: [], request: 0, demo: false, libraryMode: null, toastTimer: null, packRequest: 0, selectedRecord: null, recordDetail: null, packPayload: null};
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
      const researchButton = element("button", "record-link-button", "关联研究 ↗");
      researchButton.type = "button";
      researchButton.setAttribute("aria-label", `关联研究：${item.title || "此记录"}`);
      researchButton.addEventListener("click", () => openResearch(item));
      meta.append(researchButton);
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

  function packBusy(active, message = "正在汇集本地资料…") {
    $("pack-load").disabled = active;
    $("pack-export").disabled = active || !state.packPayload;
    $("research-pack").setAttribute("aria-busy", String(active));
    if (active) {
      $("pack-error").hidden = true;
      $("pack-status").textContent = message;
    }
  }
  function setPackScope(kind, value = "") {
    $("pack-scope-kind").value = kind;
    $("pack-scope-input").value = value;
    const symbol = kind === "symbol";
    $("pack-scope-label").textContent = symbol ? "证券标识" : "主题关键词";
    $("pack-scope-input").placeholder = symbol ? "如 AAPL / 600519" : "输入需要关联的主题词";
    $("pack-scope-note").textContent = symbol ? "按相同证券标识关联本地记录，不触发联网采集或模型调用。" : "按给定关键词匹配本地记录。字面匹配不代表相同观点、因果关系或独立核验。";
  }
  function renderSelectedRecord(record) {
    const box = $("pack-selected"); box.replaceChildren();
    if (!record) { box.append(element("p", "pack-empty", "未选中记录。")); return; }
    const top = element("div", "result-topline");
    top.append(element("span", `kind-tag ${record.kind || ""}`, KIND[record.kind] || "资料"));
    if (record.is_demo) top.append(element("span", "demo-tag", "合成样例"));
    if (record.symbol) top.append(element("span", "symbol-tag", record.symbol));
    top.append(element("span", "source-inline", "当前研究起点"));
    const title = element("h3", "result-title"); title.append(sourceLink(record.url, record.title || "未命名记录"));
    const meta = element("div", "result-meta");
    meta.append(element("span", "", record.institution || record.source || "机构未提供"), element("span", "", dateText(record.published_at)));
    box.append(top, title, meta);
  }
  function provenanceEntry(grid, label, value, link = false) {
    if (value === undefined || value === null || value === "") return;
    const field = element("dd");
    if (link) field.append(sourceLink(value, value)); else field.textContent = cleanText(value);
    grid.append(element("dt", "", label), field);
  }
  function renderRecordDetail(payload) {
    const record = payload.record || payload.item || asList(payload)[0] || state.selectedRecord;
    if (record) { state.selectedRecord = record; renderSelectedRecord(record); }
    const provenance = payload.provenance || {};
    const metadata = record?.metadata || {};
    const grid = $("pack-provenance"); grid.replaceChildren();
    provenanceEntry(grid, "记录提供方", provenance.provider || record?.provider || "未提供");
    provenanceEntry(grid, "直接数据源", provenance.direct_provider || metadata.direct_provider || record?.provider || "未提供");
    provenanceEntry(grid, "原始发布者", provenance.original_publisher || metadata.original_publisher || record?.institution || record?.source || "未提供");
    provenanceEntry(grid, "原始来源", provenance.source_url || provenance.url || record?.url, true);
    provenanceEntry(grid, "发表时间", dateText(provenance.published_at || record?.published_at, true));
    provenanceEntry(grid, "收录时间", provenance.retrieved_at || record?.retrieved_at ? dateText(provenance.retrieved_at || record?.retrieved_at, true) : "未提供");
    provenanceEntry(grid, "记录标识", record?.id);
    provenanceEntry(grid, "内容范围", provenance.content_scope || metadata.content_scope || "本地元数据；未读取研报或文章全文");
    renderRecordHistory(payload.history || payload.changes || []);
  }
  function renderRecordHistory(payload) {
    const rows = asList(payload, ["items", "history", "changes"]);
    const list = $("pack-history"); list.replaceChildren();
    if (!rows.length) { list.append(element("li", "pack-empty", "此记录暂无已保存的更新历史。")); return; }
    const total = payload.total_matches ?? rows.length;
    rows.slice(0, 10).forEach((change) => {
      const type = change.change_type || change.type || "new";
      const li = element("li"); const label = element("div", "change-label");
      label.append(element("span", `change-badge ${type === "updated" ? "updated" : ""}`, type === "updated" ? "更新" : "首次收录"));
      label.append(element("span", "history-time", change.observed_at ? dateText(change.observed_at, true) : "观察时间未提供"));
      li.append(label);
      if (type === "updated" && change.before && change.after) {
        const fields = [["title", "标题"], ["summary", "摘要"], ["institution", "机构"], ["published_at", "发表时间"], ["metadata", "附加数据"]];
        const changed = fields.filter(([key]) => JSON.stringify(change.before[key]) !== JSON.stringify(change.after[key])).map(([, name]) => name);
        li.append(element("p", "", changed.length ? `变化字段：${changed.join("、")}。` : "此条记录的内容指纹发生变化。"));
      } else li.append(element("p", "", "这是本地首次观察记录；原始发表时间另行保留。"));
      list.append(li);
    });
    if (total > 10 || payload.truncated) list.append(element("li", "pack-empty", `当前显示 ${Math.min(rows.length, 10)} 条，本地共匹配 ${total} 条历史。`));
  }
  function renderPackCoverage(payload) {
    const box = $("pack-coverage"); box.replaceChildren();
    const coverage = payload.coverage || {};
    const returned = coverage.returned ?? asList(payload).length;
    const total = coverage.total_matches ?? returned;
    box.append(element("p", "", `本次返回 ${returned} 条，本地共匹配 ${total} 条。`));
    box.append(element("p", "", coverage.truncated ? "本地匹配结果已截断；当前资料包不含全部匹配记录。" : "本地查询未标记截断；这不表示上游资料完整。"));
    const missing = payload.missing_kinds || coverage.missing_kinds || [];
    if (Array.isArray(missing) && missing.length) box.append(element("p", "", `本次缺少：${missing.map((kind) => KIND[kind] || kind).join("、")}。`));
    if (Array.isArray(coverage.missing_publication_ids) && coverage.missing_publication_ids.length) box.append(element("p", "", `${coverage.missing_publication_ids.length} 条记录未提供原始发表时间。`));
    if (coverage.history_truncated) box.append(element("p", "", "资料包中的历史记录已截断，不能据此判断全部历史变化。"));
    const sourceCollections = coverage.provider_collections || coverage.collections || payload.collections || [];
    if (Array.isArray(sourceCollections) && sourceCollections.length) {
      const list = element("ul");
      sourceCollections.forEach((collection) => list.append(element("li", "", `${collection.provider || "来源"}：${collection.returned_records ?? "未提供"} 条；${collection.truncated === true ? "存在截断" : collection.truncated === false ? "该次未标记截断" : "完整性未知"}`)));
      box.append(list);
    }
    box.append(element("p", "", "资料包只汇集已保存的元数据。未执行联网补全、正文阅读或模型分析。"));
  }
  function packBasisText(payload) {
    const selection = payload.selection || {};
    if (selection.basis === "anchor_only") return "关联依据：仅选中记录；可填写主题关键词继续汇集";
    if (selection.basis === "missing_anchor") return "未找到选中记录，无法建立关联范围";
    if (selection.symbol && selection.q) return `关联依据：证券标识 ${selection.symbol}，且包含关键词“${selection.q}”`;
    if (selection.symbol) return `关联依据：证券标识 ${selection.symbol}`;
    if (selection.q) return `关联依据：关键词“${selection.q}”的本地字面匹配`;
    if (selection.record_id || payload.anchor) return "关联依据：选中记录及服务返回的本地匹配范围";
    return "关联依据：本次指定的本地查询范围";
  }
  function renderPack(payload) {
    state.packPayload = payload;
    const items = asList(payload, ["items", "records"]);
    $("pack-count").textContent = `${items.length} 条资料`;
    $("pack-match-note").textContent = packBasisText(payload);
    const list = $("pack-items"); list.replaceChildren();
    if (!items.length) list.append(element("li", "pack-empty", "当前范围没有本地匹配记录。请调整证券标识或主题关键词。"));
    items.forEach((item) => {
      const selected = state.selectedRecord?.id === item.id;
      const li = element("li", selected ? "pack-item-selected" : "");
      const top = element("div", "result-topline");
      top.append(element("span", `kind-tag ${item.kind || ""}`, KIND[item.kind] || "资料"));
      if (item.is_demo) top.append(element("span", "demo-tag", "合成样例"));
      if (selected) top.append(element("span", "symbol-tag", "研究起点"));
      const title = element("p", "pack-item-title"); title.append(sourceLink(item.url, item.title || "未命名记录"));
      const meta = element("div", "pack-item-meta");
      meta.append(element("span", "", item.institution || item.source || "机构未提供"), element("span", "", dateText(item.published_at)));
      if (item.symbol) meta.append(element("span", "", item.symbol));
      const actions = element("div", "pack-item-actions");
      actions.append(element("span", "pack-item-meta", `直接提供方：${item.metadata?.direct_provider || item.provider || "未提供"}`));
      const button = element("button", "text-button", selected ? "刷新来源与历史" : "以此条继续研究 ↗");
      button.type = "button"; button.addEventListener("click", () => openResearch(item)); actions.append(button);
      li.append(top, title, meta, actions, element("p", "pack-item-risk", RISK)); list.append(li);
    });
    const brief = payload.brief;
    let text = typeof brief === "string" ? brief : brief?.text || "本次资料包未提供摘要。";
    if (!text.includes(RISK)) text = `${RISK}\n\n${text}`;
    $("pack-brief-text").textContent = text;
    renderPackCoverage(payload);
    $("pack-content").hidden = false;
    const selection = payload.selection || {};
    const inPack = state.selectedRecord ? items.some((item) => item.id === state.selectedRecord.id) : true;
    const demo = items.some((item) => item.is_demo) ? " · 含合成演示数据" : "";
    const anchorExcluded = Boolean(selection.record_id) && selection.anchor_in_selection === false;
    $("pack-status").textContent = `已汇集 ${items.length} 条本地资料${demo}。${!inPack || anchorExcluded ? "选中起点不在当前匹配结果中。" : ""}`;
  }
  async function fetchPack(query, seq) {
    const payload = await request(`/api/pack?${query}`);
    if (seq !== state.packRequest) return;
    renderPack(payload);
  }
  async function openResearch(item) {
    const seq = ++state.packRequest;
    state.selectedRecord = item; state.recordDetail = null; state.packPayload = null;
    $("research-pack").hidden = false; $("pack-content").hidden = true;
    $("pack-provenance").replaceChildren(); $("pack-history").replaceChildren();
    renderSelectedRecord(item); setPackScope(item.symbol ? "symbol" : "q", item.symbol || $("query-input").value.trim());
    packBusy(true, "正在读取选中记录的来源与历史…");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    $("research-pack").scrollIntoView({behavior: reduceMotion ? "auto" : "smooth", block: "start"});
    $("pack-heading").focus({preventScroll: true});
    try {
      const detail = await request(`/api/records/${encodeURIComponent(item.id)}?history_limit=50`);
      if (seq !== state.packRequest) return;
      state.recordDetail = detail; renderRecordDetail(detail);
      const selector = detail.related_selector || {};
      if (selector.symbol) setPackScope("symbol", selector.symbol);
      else if (selector.q && !$("pack-scope-input").value.trim()) setPackScope("q", selector.q);
      await fetchPack(new URLSearchParams({record_id: item.id, limit: "100", history_limit: "20"}), seq);
    } catch (error) {
      if (seq !== state.packRequest) return;
      $("pack-error").textContent = `关联研究暂时不可用：${error.message}`; $("pack-error").hidden = false;
      $("pack-status").textContent = "未取得资料包。请调整范围后重试。";
    } finally { if (seq === state.packRequest) packBusy(false); }
  }
  async function submitPack(event) {
    event.preventDefault();
    const value = $("pack-scope-input").value.trim();
    if (!value) { $("pack-scope-input").focus(); toast("请先填写证券标识或主题关键词。"); return; }
    const seq = ++state.packRequest; state.packPayload = null;
    $("pack-content").hidden = true; packBusy(true);
    const query = new URLSearchParams({limit: "100", history_limit: "20"});
    const scopeKind = $("pack-scope-kind").value;
    query.set(scopeKind, value);
    if (state.selectedRecord?.id && (scopeKind === "q" || value === state.selectedRecord.symbol)) {
      query.set("record_id", state.selectedRecord.id);
    }
    try { await fetchPack(query, seq); }
    catch (error) {
      if (seq !== state.packRequest) return;
      $("pack-error").textContent = `资料包读取失败：${error.message}`; $("pack-error").hidden = false;
      $("pack-status").textContent = "读取失败。请检查范围后重试。";
    } finally { if (seq === state.packRequest) packBusy(false); }
  }
  function markdownText(value) {
    return cleanText(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/([\\`*_{}\[\]()#+.!|~])/g, "\\$1");
  }
  function exportPack() {
    const payload = state.packPayload;
    if (!payload) { toast("请先汇集本地资料，再导出资料包。"); return; }
    const format = $("pack-export-format").value;
    const exportPayload = {...payload, risk_notice: RISK, noncommercial: true, editor_notice_required: true};
    let text;
    if (format === "json") text = JSON.stringify(exportPayload, null, 2);
    else {
      const items = asList(payload, ["items", "records"]);
      const lines = [RISK, "", "# 关联研究资料包", "", "仅供非商用研究与学习。接收的编辑器或知识库必须在查询和分析结果中显示风险提示。", "", markdownText(packBasisText(payload)), "", `本次返回 ${items.length} 条本地元数据；${payload.coverage?.truncated ? "结果已截断" : "本地查询未标记截断，不代表上游完整覆盖"}。`, ""];
      items.forEach((item) => {
        lines.push(`## ${markdownText(item.title)}`, "", RISK, "", item.is_demo ? "**合成演示数据。**" : "原始来源与内容取用条件仍适用。", "", `- 类型：${markdownText(KIND[item.kind] || item.kind)}`, `- 标的：${markdownText(item.symbol || "未提供")}`, `- 发布机构：${markdownText(item.institution || item.source || "未提供")}`, `- 直接提供方：${markdownText(item.metadata?.direct_provider || item.provider || "未提供")}`, `- 发表时间：${markdownText(item.published_at || "未提供")}`, `- 收录时间：${markdownText(item.retrieved_at || "未提供")}`, `- 原始链接：${markdownText(safeUrl(item.url) || "链接未提供或未通过HTTPS校验")}`, "", markdownText(item.summary || "此记录仅含目录信息；未读取全文。"), "");
      });
      const brief = typeof payload.brief === "string" ? payload.brief : payload.brief?.text;
      if (brief) lines.push("## 资料摘要", "", RISK, "", markdownText(brief), "");
      text = lines.join("\n");
    }
    if (!text.includes(RISK)) { toast("资料包缺少风险提示，已阻止导出。"); return; }
    const blob = new Blob([text], {type: format === "json" ? "application/json;charset=utf-8" : "text/markdown;charset=utf-8"});
    const url = URL.createObjectURL(blob); const anchor = element("a");
    anchor.href = url; anchor.download = `${format === "json" ? "research-pack" : "research-summary"}-${new Date().toISOString().slice(0, 10)}.${format === "json" ? "json" : "md"}`;
    document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast(`${format === "json" ? "已导出本地资料包" : "已导出本地资料摘要"}。接收的编辑器必须显示风险提示。`);
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
  $("pack-form").addEventListener("submit", submitPack);
  $("pack-scope-kind").addEventListener("change", () => setPackScope($("pack-scope-kind").value, ""));
  $("pack-export").addEventListener("click", exportPack);
  $("pack-close").addEventListener("click", () => { ++state.packRequest; $("research-pack").hidden = true; packBusy(false); $("results-heading").focus({preventScroll: true}); });
  refresh();
})();
