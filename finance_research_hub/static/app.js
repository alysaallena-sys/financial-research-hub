/* Financial Research Hub — local, read-only UI. No third-party scripts. */
"use strict";
(() => {
  const RISK = "投资有风险，分析结果和查询结果不构成投资建议。";
  const KIND = {news: "公开资讯", research: "券商研报", rating: "评级变化", talk: "TED 与演讲"};
  const DATA_KIND = {price_series: "价格序列", fund_nav: "基金净值", bond_profile: "债券资料", macro_series: "宏观序列"};
  const DESCRIPTIONS = {
    "": "查看公开资讯、研报目录与评级记录，沿来源继续研究。",
    news: "查看本地收录的公开资讯，按来源与主题筛选。",
    research: "查看研报目录、发布机构与评级，打开原始来源核对。",
    rating: "查看数据源收录的机构评级事件，区分事件与市场共识。",
    talk: "查看公开演讲与 TED 条目，保留原始页面与发表时间。"
  };
  const $ = (id) => document.getElementById(id);
  const state = {kind: "", items: [], sources: [], changes: [], request: 0, demo: false, libraryMode: null, toastTimer: null, packRequest: 0, selectedRecord: null, recordDetail: null, packPayload: null, view: "records", datasets: [], datasetRequest: 0, datasetDetailRequest: 0, selectedDataset: null, datasetPayload: null, compareSelection: new Map(), compareRequest: 0};
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
    state.view = "records";
    $("data-workspace").hidden = true;
    $("record-workspace").hidden = false;
    $("record-metrics").hidden = false;
    $("data-navigation").classList.remove("is-active");
    $("data-navigation").removeAttribute("aria-current");
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
    renderResearchCatalog(payload?.research_catalog);
  }
  function renderResearchCatalog(payload, targetId = "research-catalog-list", visibleLimit = 5) {
    const entries = Array.isArray(payload) ? payload : asList(payload, ["items", "entries", "sources"]);
    const list = $(targetId); list.replaceChildren();
    if (!entries.length) { list.append(element("li", "context-empty", "当前服务尚未提供研究入口目录。")); return; }
    const labels = {manual_only: "手动入口", reference_only: "参考入口", source_reviewed: "来源已核", runtime_partial: "部分运行核验", paid_hold: "付费接入暂停", license_hold: "许可待澄清", not_integrated: "尚未接入", metadata_only: "目录元数据", integrated_bounded_live_check: "有界取数已验", integrated_source_path_runtime_unverified: "接口已接 · 取数未验", historical_candidate_not_currently_integrated: "历史候选 · 未接入", adapter_present_live_unverified: "适配器在 · 取数未验", static_review_not_installed: "源码已审 · 未安装", one_world_bank_connector_path_checked: "单连接器已验", three_isolated_security_patched_paths_checked: "三条隔离路径已验", manual_reference_no_data_api_grant: "手动参考 · 无API授权", paid_content_excluded: "付费正文不采集", commercial_connector_held: "商业接入暂缓", acquisition_paused: "采集暂停", fixed_source_review_not_bundled: "固定源码已审 · 未打包", one_public_indicator_path_checked: "单指标已验", official_documentation_not_connected: "官方文档 · 未连接", official_mcp_documented_not_connected: "官方MCP文档 · 未连接", partial_primary_review_no_integration: "部分来源已审 · 未接入", integrated_one_stock_page_checked: "单股单页已验", lead_only_no_api_integration: "线索 · 未接API", deployment_paused_in_dated_review: "历史部署暂停", connector_catalog_reference_only: "连接器目录参考", manual_reference: "手动参考"};
    const overflow = element("ul", "sources-list catalog-overflow");
    const roleLabels = {public_research: "公开研究", public_insights: "公开观点", broker_research: "券商研报", research_tool: "研究工具", data_library: "数据工具", research_workbench: "研究工作台", learning_reference: "方法参考", paid_service: "商业服务", public_news_metadata: "公开新闻目录", public_talk_metadata: "公开演讲目录", historical_public_news_candidate: "公开新闻历史候选", historical_public_talk_candidate: "公开演讲历史候选", broker_report_metadata: "券商研报目录", broker_metadata_interface_reference: "研报接口参考", optional_yahoo_rating_events: "可选机构评级事件", snapshot_and_diff_method_reference: "快照与变更方法参考", source_and_manifest_method_reference: "来源清单方法参考", discovery_first_data_tool_candidate: "按需发现的数据工具候选", typed_market_data_candidate: "结构化市场数据候选", original_macro_data_provider: "原始宏观数据源", macro_data_candidate: "宏观数据候选", macro_sources_and_vintages: "宏观来源与数据版本", macro_theme_navigation: "宏观主题入口", interface_reference_and_dataset_candidate: "界面参考与数据集候选", workbench_reference_and_connector_candidate: "工作台参考与连接器候选", manual_market_research_and_ui_reference: "市场研究与界面参考", market_navigation_and_map_embed_candidate: "市场入口与地图嵌入候选", company_ranking_navigation: "公司排名入口", company_research_navigation: "公司研究入口", etf_research_navigation: "ETF研究入口", reading_organization_reference: "阅读组织参考", manual_sqlite_maintenance_candidate: "SQLite维护候选", opinion_navigation_paid_content_held: "评论入口 · 付费正文暂停", paid_media_reference: "付费媒体参考", commercial_research_service_reference: "商业研报服务参考", community_research_leads: "社区研究线索", unverified_ai_dashboard_lead: "未验AI工作台线索"};
    entries.forEach((entry, index) => {
      const li = element("li"), heading = element("div", "source-heading");
      const status = entry.state || entry.status;
      heading.append(sourceLink(entry.url || entry.homepage || entry.source_url, entry.name || entry.title || entry.id || "研究入口"), element("span", "source-status", labels[status] || statusLabels[status] || status || "手动入口"));
      li.append(heading);
      if (entry.role) li.append(element("p", "source-description", roleLabels[entry.role] || entry.role));
      const description = entry.description || entry.scope || entry.coverage || entry.notes || entry.note;
      if (description) li.append(element("p", "source-description", cleanText(description)));
      if (entry.limitations || entry.caveats) li.append(element("p", "source-description", cleanText(entry.limitations || entry.caveats)));
      const reviewed = entry.reviewed_at || entry.review_date || entry.verified_at;
      if (reviewed) li.append(element("p", "source-description", `核查日期：${dateText(reviewed)}`));
      (index < visibleLimit ? list : overflow).append(li);
    });
    if (entries.length > visibleLimit) {
      const li = element("li", "catalog-more"), details = element("details");
      details.append(element("summary", "", `查看其余 ${entries.length - visibleLimit} 个研究入口`), overflow); li.append(details); list.append(li);
    }
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
    else { $("sources-list").replaceChildren(element("li", "context-empty", "来源状态暂时不可用。刷新后重试。")); $("research-catalog-list").replaceChildren(element("li", "context-empty", "研究入口目录暂时不可用。")); }
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
    if (state.view === "data") {
      invalidateComparison("本地库已刷新，请重新比较当前选择。");
      await Promise.all([loadDatasets(), loadContext()]);
      if (state.selectedDataset) await openDataset(state.selectedDataset.id, false);
    } else await Promise.all([loadItems(), loadContext()]);
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
    top.append(element("span", `kind-tag ${record.kind || ""}`, KIND[record.kind] || DATA_KIND[record.kind] || "资料"));
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
    box.append(element("p", "", `目录记录：本次返回 ${returned} 条，本地共匹配 ${total} 条。`));
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
    box.append(element("p", "", "资料包汇集本地记录、数值数据和有日期的目录参考。未执行联网补全、正文阅读或模型分析。"));
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
    const linkedDatasets = asList(payload.related_datasets, ["items", "datasets"]);
    const references = asList(payload.reference_entries, ["items", "entries"]);
    const hasEvidence = items.length + linkedDatasets.length + references.length > 0;
    $("pack-count").textContent = `目录 ${items.length} · 数值 ${linkedDatasets.length} · 参考 ${references.length}`;
    $("pack-match-note").textContent = packBasisText(payload);
    const list = $("pack-items"); list.replaceChildren();
    if (!items.length) list.append(element("li", hasEvidence ? "pack-section-note" : "pack-empty", hasEvidence ? "此范围未包含资讯或研报目录记录；数值数据和研究参考入口分别列出。" : "当前范围没有本地目录记录、数值数据或研究参考入口。请调整证券标识或主题关键词。"));
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
    renderPackDatasets(payload.related_datasets);
    $("pack-references-section").hidden = references.length === 0;
    if (references.length) {
      renderResearchCatalog(references, "pack-references", 20);
      $("pack-references-note").textContent = `这些是注明核查日期的目录参考，不表示已采集正文或取得数据接口授权。${payload.reference_entries?.truncated ? "参考入口结果已截断；完整目录可在研究入口中查看。" : ""}`;
    } else $("pack-references").replaceChildren();
    renderPackCoverage(payload);
    $("pack-content").hidden = false;
    const selection = payload.selection || {};
    const inPack = state.selectedRecord ? items.some((item) => item.id === state.selectedRecord.id) : true;
    const demo = [...items, ...linkedDatasets].some((item) => item.is_demo) ? " · 含合成演示数据" : "";
    const anchorExcluded = Boolean(selection.record_id) && selection.anchor_in_selection === false;
    $("pack-status").textContent = hasEvidence ? `已汇集：目录 ${items.length} / 数值 ${linkedDatasets.length} / 参考 ${references.length}${demo}。${!inPack || anchorExcluded ? "选中起点不在当前匹配结果中。" : ""}` : "当前范围没有本地目录记录、数值数据或研究参考入口。请调整标的或关键词。";
  }
  async function fetchPack(query, seq) {
    const payload = await request(`/api/pack?${query}`);
    if (seq !== state.packRequest) return;
    renderPack(payload);
  }
  async function openResearch(item) {
    const seq = ++state.packRequest;
    state.packDatasetOrigin = null;
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

  function showDataWorkspace() {
    state.view = "data";
    $("data-workspace").hidden = false;
    $("record-workspace").hidden = true;
    $("record-metrics").hidden = true;
    $("data-navigation").classList.add("is-active");
    $("data-navigation").setAttribute("aria-current", "page");
    document.querySelectorAll("[data-kind]").forEach((button) => { button.classList.remove("is-active"); button.removeAttribute("aria-current"); });
    $("page-title").textContent = "数据与图表";
    $("page-description").textContent = "把本地数值证据与资讯、研报和来源放在同一个工作空间。";
  }
  function numberText(value, digits = 4) {
    return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("zh-CN", {maximumFractionDigits: digits}) : "缺失";
  }
  function axisNumberText(value) {
    const magnitude = Math.abs(value);
    if (magnitude !== 0 && magnitude < 0.0001) return value.toExponential(2);
    return value.toLocaleString("zh-CN", {notation: "compact", maximumSignificantDigits: 4});
  }
  function valueText(value) {
    if (value === null || value === undefined || value === "") return "缺失";
    return typeof value === "number" ? numberText(value, 6) : typeof value === "boolean" ? (value ? "是" : "否") : cleanText(value);
  }
  function datasetRows(dataset) { return Array.isArray(dataset?.rows) ? dataset.rows : Array.isArray(dataset?.rows_preview) ? dataset.rows_preview : []; }
  function datasetRowCount(dataset) { return Number.isFinite(dataset?.row_count) ? dataset.row_count : datasetRows(dataset).length; }
  function datasetEligible(dataset) {
    if (!["price_series", "fund_nav"].includes(dataset.kind)) return false;
    if (dataset.columns?.[dataset.time_column] !== "date" || dataset.columns?.[dataset.value_column] !== "number") return false;
    if (datasetRowCount(dataset) < 2) return false;
    if (dataset.rows_omitted) return true; // The service validates values omitted from this catalog preview.
    return datasetRows(dataset).filter((row) => typeof row[dataset.value_column] === "number" && Number.isFinite(row[dataset.value_column]) && row[dataset.value_column] > 0).length >= 2;
  }
  function dataParams() {
    const query = new URLSearchParams({limit: "100"});
    if ($("dataset-kind-filter").value) query.set("kind", $("dataset-kind-filter").value);
    if ($("dataset-query-filter").value.trim()) query.set("q", $("dataset-query-filter").value.trim());
    return query;
  }
  function invalidateComparison(message = "选择或条件已变化，请重新比较。") {
    ++state.compareRequest;
    $("comparison-result").hidden = true;
    $("comparison-status").textContent = message;
    $("comparison-button").disabled = state.compareSelection.size < 2;
  }
  function renderCompareSelection() {
    $("comparison-selection-count").textContent = `已选 ${state.compareSelection.size} / 5`;
    const box = $("comparison-selected"); box.replaceChildren();
    if (!state.compareSelection.size) box.append(element("span", "pack-empty", "尚未选择序列。"));
    state.compareSelection.forEach((dataset, id) => {
      const chip = element("span", "comparison-chip");
      chip.append(element("span", "", dataset.title || dataset.symbol || id));
      const remove = element("button", "", "×"); remove.type = "button"; remove.setAttribute("aria-label", `移除 ${dataset.title || dataset.symbol || "序列"}`);
      remove.addEventListener("click", () => { state.compareSelection.delete(id); invalidateComparison(); renderCompareSelection(); renderDatasetList(); });
      chip.append(remove); box.append(chip);
    });
    $("comparison-button").disabled = state.compareSelection.size < 2;
    $("comparison-review-button").disabled = state.compareSelection.size === 0;
  }
  function renderDatasetList() {
    const list = $("dataset-list"); list.replaceChildren();
    if (!state.datasets.length) { list.append(element("li", "context-empty", "当前范围没有已保存的数据集。")); return; }
    state.datasets.forEach((dataset) => {
      const li = element("li");
      const label = element("label", "dataset-choice");
      const checkbox = element("input"); checkbox.type = "checkbox"; checkbox.checked = state.compareSelection.has(dataset.id);
      checkbox.disabled = !datasetEligible(dataset);
      checkbox.setAttribute("aria-label", `${dataset.title || "此数据集"}${checkbox.disabled ? "，当前不满足价格或净值比较的基本条件" : "，加入序列比较，数值与口径由服务核对"}`);
      label.title = checkbox.disabled ? "比较需要价格或净值、明确日期列与数值列、至少两行" : "选择此序列，服务将核对完整数值和比较口径";
      label.append(checkbox);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked && state.compareSelection.size >= 5) { checkbox.checked = false; toast("每次最多比较 5 组序列。请先移除一项。"); return; }
        if (checkbox.checked) state.compareSelection.set(dataset.id, dataset); else state.compareSelection.delete(dataset.id);
        invalidateComparison(); renderCompareSelection();
      });
      const body = element("div"); const top = element("div", "result-topline");
      top.append(element("span", "dataset-type-tag", DATA_KIND[dataset.kind] || dataset.kind || "数值资料"));
      if (dataset.is_demo) top.append(element("span", "demo-tag", "合成样例"));
      const title = element("button", "dataset-title-button", dataset.title || "未命名数据集"); title.type = "button"; title.addEventListener("click", () => openDataset(dataset.id));
      const meta = element("div", "dataset-card-meta");
      for (const text of [dataset.symbol, dataset.provenance?.original_publisher || dataset.provenance?.provider, `${datasetRowCount(dataset)} 行`, dataset.currency]) if (text) meta.append(element("span", "", text));
      body.append(top, title, meta);
      const view = element("button", "dataset-view-button", "查看数据 ↗"); view.type = "button"; view.addEventListener("click", () => openDataset(dataset.id));
      li.append(label, body, view); list.append(li);
    });
  }
  async function loadDatasets() {
    const seq = ++state.datasetRequest;
    $("dataset-status").textContent = "正在读取本地数据目录…";
    try {
      const payload = await request(`/api/datasets?${dataParams()}`);
      if (seq !== state.datasetRequest) return;
      state.datasets = asList(payload, ["items", "datasets"]);
      $("dataset-count").textContent = `${payload.total_matches ?? state.datasets.length} 组`;
      $("dataset-status").textContent = payload.schema_available === false ? "本地库尚无数值数据。资讯与研报功能仍可使用。" : `返回 ${state.datasets.length} 组，本地匹配 ${payload.total_matches ?? state.datasets.length} 组${payload.truncated ? "；目录结果已截断" : ""}。`;
      renderDatasetList(); renderCompareSelection();
      if (state.datasets.some((dataset) => dataset.is_demo)) { state.demo = true; updateDemoBanner(); }
    } catch (error) {
      if (seq !== state.datasetRequest) return;
      $("dataset-status").textContent = `数据目录暂时不可用：${error.message}`;
      $("dataset-count").textContent = "读取失败"; state.datasets = []; renderDatasetList();
    }
  }
  function tableContent(table, headings, rows, caption) {
    table.replaceChildren();
    if (caption) table.append(element("caption", "", caption));
    const thead = element("thead"); const tr = element("tr");
    headings.forEach((name) => { const th = element("th", "", name); th.scope = "col"; tr.append(th); });
    thead.append(tr); const tbody = element("tbody");
    rows.forEach((row) => {
      const line = element("tr");
      row.forEach((value) => { const missing = value === null || value === undefined || value === ""; line.append(element("td", missing ? "missing-value" : "", valueText(value))); });
      tbody.append(line);
    });
    if (!rows.length) { const empty = element("td", "missing-value", "暂无可展示的数值"); empty.colSpan = headings.length || 1; const line = element("tr"); line.append(empty); tbody.append(line); }
    table.append(thead, tbody);
  }
  const SVG_NS = "http://www.w3.org/2000/svg";
  function svgNode(tag, attrs = {}, text) {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
    if (text !== undefined) node.textContent = String(text);
    return node;
  }
  function drawSeriesChart(container, series, label, caption) {
    container.replaceChildren();
    const dates = [...new Set(series.flatMap((entry) => entry.points.map((point) => cleanText(point.date))))].sort();
    const numbers = series.flatMap((entry) => entry.points.map((point) => point.value)).filter((value) => typeof value === "number" && Number.isFinite(value));
    if (!dates.length || !numbers.length) { container.append(element("p", "chart-empty", "没有可绘制的数值。缺失值保留在表格中。")); return; }
    const width = 760, height = 280, left = 63, right = 31, top = 22, bottom = 43;
    let minimum = Math.min(...numbers), maximum = Math.max(...numbers);
    const padding = maximum === minimum ? Math.max(Math.abs(maximum) * 0.03, 1) : (maximum - minimum) * 0.08;
    minimum -= padding; maximum += padding;
    const x = (index) => left + (dates.length === 1 ? (width - left - right) / 2 : index / (dates.length - 1) * (width - left - right));
    const y = (value) => top + (maximum - value) / (maximum - minimum) * (height - top - bottom);
    const svg = svgNode("svg", {viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": label});
    svg.append(svgNode("title", {}, label), svgNode("desc", {}, "曲线使用编号、线型与颜色区分；下方提供对应数值表。缺失值不填补。"));
    for (let i = 0; i <= 4; i++) {
      const value = minimum + (maximum - minimum) * i / 4, yy = y(value);
      svg.append(svgNode("line", {x1: left, y1: yy, x2: width - right, y2: yy, class: "chart-gridline"}));
      svg.append(svgNode("text", {x: left - 9, y: yy + 3, "text-anchor": "end", class: "chart-axis-label"}, axisNumberText(value)));
    }
    const ticks = [...new Set([0, Math.floor((dates.length - 1) / 3), Math.floor((dates.length - 1) * 2 / 3), dates.length - 1])];
    ticks.forEach((index) => svg.append(svgNode("text", {x: x(index), y: height - 16, "text-anchor": index === 0 ? "start" : index === dates.length - 1 ? "end" : "middle", class: "chart-axis-label"}, dates[index].slice(0, 19))));
    const palette = ["#246c55", "#557ca4", "#a47a3e", "#856897", "#4c8b91"];
    const dashes = ["", "8 4", "2 4", "10 3 2 3", "4 3"];
    const legend = element("div", "chart-legend");
    series.forEach((entry, index) => {
      const color = palette[index % palette.length], dash = dashes[index % dashes.length];
      const byDate = new Map(entry.points.map((point) => [cleanText(point.date), point.value]));
      let segment = [], lastPoint = null;
      function appendSegment() {
        if (segment.length) svg.append(svgNode("polyline", {points: segment.join(" "), fill: "none", stroke: color, "stroke-width": 2.3, "stroke-dasharray": dash, "stroke-linejoin": "round", "stroke-linecap": "round"}));
        segment = [];
      }
      dates.forEach((date, dateIndex) => {
        const value = byDate.get(date);
        if (typeof value !== "number" || !Number.isFinite(value)) { appendSegment(); return; }
        const xx = x(dateIndex), yy = y(value); segment.push(`${xx.toFixed(2)},${yy.toFixed(2)}`); lastPoint = {x: xx, y: yy};
        svg.append(svgNode("circle", {cx: xx, cy: yy, r: 2.2, fill: color}));
      });
      appendSegment();
      if (lastPoint) svg.append(svgNode("text", {x: lastPoint.x + 7, y: lastPoint.y + 3, class: "chart-series-label"}, String(index + 1)));
      const item = element("span", "chart-legend-item"), sample = svgNode("svg", {viewBox: "0 0 30 12", "aria-hidden": "true"});
      sample.append(svgNode("line", {x1: 1, y1: 6, x2: 29, y2: 6, stroke: color, "stroke-width": 2.3, "stroke-dasharray": dash}));
      item.append(sample, element("span", "", `${index + 1}. ${entry.label || "未命名序列"}`)); legend.append(item);
    });
    container.append(svg, legend, element("p", "chart-caption", caption));
  }
  function renderDataset(dataset) {
    state.selectedDataset = dataset;
    const rows = datasetRows(dataset), source = dataset.provenance || {}, coverage = dataset.coverage || {};
    $("dataset-detail-heading").textContent = dataset.title || "数据详情";
    $("dataset-detail-subtitle").textContent = [DATA_KIND[dataset.kind] || dataset.kind, dataset.symbol, `${rows.length} 行`].filter(Boolean).join(" · ");
    $("dataset-detail-notice").textContent = `${dataset.is_demo ? "【合成演示数据】" : "【已保存的本地数据】"}${dataset.as_of ? `数据截至 ${dataset.as_of}。` : "未提供统一截至时间。"} 数值与来源口径保持分开；图表不代表投资判断。`;
    const grid = $("dataset-provenance"); grid.replaceChildren();
    for (const [name, value] of [["原始发布者", source.original_publisher], ["直接提供方", source.direct_provider || source.provider], ["标的", dataset.symbol], ["市场", dataset.market], ["币种", dataset.currency || "未提供"], ["单位", dataset.units || "未提供"], ["复权口径", dataset.adjustment || "未提供"], ["数据频率", dataset.frequency || "未提供"], ["时区", dataset.timezone || "未提供"], ["来源版本", source.source_version], ["收录时间", source.retrieved_at], ["身份依据", source.identity_basis]]) provenanceEntry(grid, name, value);
    provenanceEntry(grid, "来源链接", source.url || source.source_url, true);
    provenanceEntry(grid, "内容指纹", dataset.content_hash);
    provenanceEntry(grid, "指纹依据", dataset.hash_basis);
    const gaps = $("dataset-coverage"); gaps.replaceChildren();
    gaps.append(element("p", "", coverage.truncated === true ? "来源结果已截断，当前数据集不含完整来源范围。" : coverage.truncated === false ? "来源未标记截断；这不证明历史范围完整。" : "来源完整性未知。"));
    if (Array.isArray(dataset.missing_fields) && dataset.missing_fields.length) gaps.append(element("p", "", `未提供的字段：${dataset.missing_fields.join("、")}`));
    const nulls = Object.entries(dataset.null_counts || {}).filter(([, count]) => Number(count) > 0);
    gaps.append(element("p", "", nulls.length ? `缺失值：${nulls.map(([column, count]) => `${column} ${count} 项`).join("；")}` : "服务未报告列内缺失值。"));
    if (coverage.note || coverage.scope) gaps.append(element("p", "", cleanText(coverage.note || coverage.scope)));
    const columns = Object.keys(dataset.columns || {});
    const headings = columns.map((column) => `${column}${dataset.units?.[column] ? ` [${dataset.units[column]}]` : ""}`);
    tableContent($("dataset-table"), headings, rows.slice(0, 200).map((row) => columns.map((column) => row[column])), `原始字段与数值，显示 ${Math.min(rows.length, 200)} / ${rows.length} 行。缺失值不补零。`);
    if (dataset.time_column && dataset.value_column) {
      const points = rows.filter((row) => row[dataset.time_column] !== null && row[dataset.time_column] !== undefined && row[dataset.time_column] !== "").map((row) => ({date: cleanText(row[dataset.time_column]), value: row[dataset.value_column]}));
      if (new Set(points.map((point) => point.date)).size !== points.length) $("dataset-chart").replaceChildren(element("p", "chart-empty", "同一期间存在多个观测。图形未自动合并，请查看原始数值表。"));
      else drawSeriesChart($("dataset-chart"), [{label: dataset.title, points}], `${dataset.title || "所选数据集"}原始数值图`, "横轴使用原始期间标签；按标签排序，不补齐缺失日期或数值。具体单位与口径见来源说明。");
    } else $("dataset-chart").replaceChildren(element("p", "chart-empty", "该数据集未声明可绘制的时间列和数值列，请使用下方资料表查看。"));
    $("dataset-detail").hidden = false;
  }
  async function openDataset(id, scroll = true) {
    const seq = ++state.datasetDetailRequest;
    showDataWorkspace();
    $("dataset-detail").hidden = true;
    $("dataset-status").textContent = "正在读取数据详情…";
    try {
      const payload = await request(`/api/datasets/${encodeURIComponent(id)}`);
      if (seq !== state.datasetDetailRequest) return;
      const dataset = payload.dataset || asList(payload)[0];
      if (!dataset) throw new Error("本地库未找到这个数据集。");
      state.datasetPayload = payload; renderDataset(dataset);
      $("dataset-status").textContent = "数据详情已读取；没有触发外部数据采集。";
      if (dataset.is_demo) { state.demo = true; updateDemoBanner(); }
      if (!state.datasets.length) loadDatasets();
      if (scroll) { $("dataset-detail").scrollIntoView({behavior: "auto", block: "start"}); $("dataset-detail-heading").focus({preventScroll: true}); }
    } catch (error) { if (seq === state.datasetDetailRequest) $("dataset-status").textContent = `数据详情读取失败：${error.message}`; }
  }
  function downloadJson(payload, filename) {
    const value = {...payload, risk_notice: RISK, noncommercial: true, editor_notice_required: true};
    const blob = new Blob([JSON.stringify(value, null, 2)], {type: "application/json;charset=utf-8"});
    const url = URL.createObjectURL(blob), anchor = element("a"); anchor.href = url; anchor.download = filename;
    document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function exportDataset() {
    if (!state.datasetPayload) { toast("请先打开一个数据集。"); return; }
    downloadJson(state.datasetPayload, `research-dataset-${new Date().toISOString().slice(0, 10)}.json`);
    toast("数据已导出。接收的编辑器必须保留并显示风险提示。");
  }
  function renderPackDatasets(payload) {
    const list = $("pack-datasets"); list.replaceChildren();
    const datasets = asList(payload, ["items", "datasets"]);
    $("pack-datasets-section").hidden = false;
    if (!datasets.length) { list.append(element("li", "pack-empty", payload === undefined ? "当前服务尚未提供关联数据目录。" : "此关联范围暂无已保存的数值数据集。")); return; }
    datasets.forEach((dataset) => {
      const li = element("li"), button = element("button", "text-button", `${DATA_KIND[dataset.kind] || "数值资料"} · ${dataset.title || dataset.symbol || "查看数据"} ↗`);
      button.type = "button"; button.addEventListener("click", () => openDataset(dataset.id));
      li.append(button, element("p", "", `${dataset.is_demo ? "合成样例 · " : ""}${dataset.provenance?.original_publisher || dataset.provenance?.provider || "来源未提供"} · ${datasetRowCount(dataset)} 行`)); list.append(li);
    });
    if (payload?.truncated) list.append(element("li", "pack-empty", "关联数据目录已截断；可在“数据与图表”继续筛选。"));
  }
  async function openDatasetResearch() {
    const dataset = state.selectedDataset;
    if (!dataset) { toast("请先打开一个数据集。"); return; }
    const seq = ++state.packRequest; state.selectedRecord = null; state.recordDetail = null; state.packPayload = null; state.packDatasetOrigin = dataset;
    $("research-pack").hidden = false; $("pack-content").hidden = true; $("pack-error").hidden = true;
    renderSelectedRecord({...dataset, source: dataset.provenance?.original_publisher || dataset.provenance?.provider, institution: dataset.provenance?.original_publisher, url: dataset.provenance?.url || ""});
    const grid = $("pack-provenance"); grid.replaceChildren();
    provenanceEntry(grid, "起点类型", DATA_KIND[dataset.kind] || dataset.kind);
    provenanceEntry(grid, "数据提供方", dataset.provenance?.direct_provider || dataset.provenance?.provider || "未提供");
    provenanceEntry(grid, "发布者", dataset.provenance?.original_publisher || "未提供");
    provenanceEntry(grid, "来源链接", dataset.provenance?.url, true);
    $("pack-history").replaceChildren(element("li", "pack-empty", "起点为数值数据集。此区域未提供研报记录历史；数据采集范围见数据详情。"));
    const topic = Array.isArray(dataset.topics) ? dataset.topics.find((item) => typeof item === "string" && item.trim()) : "";
    const scope = dataset.symbol ? "symbol" : "q", value = dataset.symbol || topic || "";
    setPackScope(scope, value);
    $("research-pack").scrollIntoView({behavior: "auto", block: "start"}); $("pack-heading").focus({preventScroll: true});
    if (!value) { packBusy(false); $("pack-status").textContent = "数据集未提供证券标识或主题词。请填写关键词后查询本地资料。"; return; }
    packBusy(true); const query = new URLSearchParams({[scope]: value, limit: "100", history_limit: "20"});
    try { await fetchPack(query, seq); }
    catch (error) { if (seq === state.packRequest) { $("pack-error").textContent = `关联资料读取失败：${error.message}`; $("pack-error").hidden = false; } }
    finally { if (seq === state.packRequest) packBusy(false); }
  }
  function comparisonCoverage(payload) {
    const coverage = payload.coverage || {}, box = $("comparison-coverage"); box.replaceChildren();
    const common = Array.isArray(coverage.common_dates) ? coverage.common_dates.length : coverage.common_dates;
    box.append(element("p", "", `对齐方式：${coverage.alignment === "intersection" ? "只使用共同日期" : "日期完全一致"}；共同观察日期：${common ?? "未提供"}。`));
    if (coverage.requested_start || coverage.requested_end) box.append(element("p", "", `请求期间：${coverage.requested_start || "未限定"} 至 ${coverage.requested_end || "未限定"}。`));
    const excluded = coverage.excluded_dates_by_dataset || {};
    Object.entries(excluded).forEach(([id, dates]) => {
      if (Array.isArray(dates) && dates.length) {
        const curve = (payload.curves || []).find((item) => item.dataset_id === id);
        box.append(element("p", "", `${curve?.label || curve?.symbol || id} 排除的日期：${dates.join("、")}。`));
      }
    });
    Object.entries(coverage.window_excluded_dates_by_dataset || {}).forEach(([id, dates]) => {
      if (Array.isArray(dates) && dates.length) {
        const curve = (payload.curves || []).find((item) => item.dataset_id === id);
        box.append(element("p", "", `${curve?.label || curve?.symbol || id} 位于请求期间以外的日期：${dates.join("、")}。`));
      }
    });
    box.append(element("p", "", "曲线由服务归一为起点 100；最大回撤显示正的损失幅度。未换汇、未填补缺失日期。"));
    box.append(element("p", "", "回撤仅根据保留的观测点计算，可能漏掉观测之间的峰值或谷值。"));
    if (payload.methods?.return_basis) box.append(element("p", "", `收益口径：${cleanText(payload.methods.return_basis)}`));
  }
  function renderComparison(payload) {
    const curves = Array.isArray(payload.curves) ? payload.curves : [];
    drawSeriesChart($("comparison-chart"), curves.map((curve) => ({label: curve.label || curve.symbol, points: (curve.points || []).map((point) => ({date: point.date, value: point.indexed_value}))})), "已选序列起点100比较", "使用服务返回的归一数值。编号与线型对应下方指标和数值表；合成序列不代表真实表现。");
    const headings = ["序列", "开始", "结束", "观察点", "区间变化（%）", "最大回撤（%）", "币种 / 单位 / 复权"];
    tableContent($("comparison-metrics"), headings, curves.map((curve, index) => { const metric = curve.metrics || {}; return [`${index + 1}. ${curve.label || curve.symbol || "序列"}`, metric.start_date, metric.end_date, metric.point_count, metric.period_return_pct, metric.max_drawdown_pct, [curve.currency, curve.unit, curve.adjustment].filter(Boolean).join(" / ")]; }), "指标直接使用本地服务的确定性计算结果。百分比列使用百分数单位。");
    const dates = [...new Set(curves.flatMap((curve) => (curve.points || []).map((point) => point.date)))].sort();
    tableContent($("comparison-table"), ["日期", ...curves.map((curve, index) => `${index + 1}. ${curve.label || curve.symbol || "序列"}`)], dates.map((date) => [date, ...curves.map((curve) => (curve.points || []).find((point) => point.date === date)?.indexed_value ?? null)]), "归一数值：每条序列在本次实际比较起点为100。");
    comparisonCoverage(payload);
    $("comparison-result").hidden = false;
    $("comparison-status").textContent = `已比较 ${curves.length} 组本地序列${curves.some((curve) => (curve.points || []).some((point) => point.is_demo)) ? "；包含合成演示数据" : ""}。结果不构成投资建议。`;
  }
  async function compareDatasets(event) {
    event.preventDefault();
    if (state.compareSelection.size < 2) { toast("请先勾选 2 至 5 组价格或净值序列。"); return; }
    const seq = ++state.compareRequest;
    $("comparison-result").hidden = true; $("comparison-button").disabled = true;
    $("comparison-status").textContent = "正在校验日期、币种和数据口径…";
    const query = new URLSearchParams({ids: [...state.compareSelection.keys()].join(","), alignment: $("comparison-alignment").value});
    if ($("comparison-start").value) query.set("start", $("comparison-start").value);
    if ($("comparison-end").value) query.set("end", $("comparison-end").value);
    try { const payload = await request(`/api/compare?${query}`); if (seq === state.compareRequest) renderComparison(payload); }
    catch (error) { if (seq === state.compareRequest) $("comparison-status").textContent = `无法比较：${error.message}`; }
    finally { if (seq === state.compareRequest) $("comparison-button").disabled = state.compareSelection.size < 2; }
  }
  async function downloadReviewPacket(context, buttonId) {
    const query = new URLSearchParams({limit: "20"});
    if (context === "dataset") {
      if (!state.selectedDataset) { toast("请先打开一个数据集。"); return; }
      query.set("dataset_ids", state.selectedDataset.id);
    } else if (context === "comparison") {
      if (!state.compareSelection.size) { toast("请先选择需要复核的数据集。"); return; }
      query.set("dataset_ids", [...state.compareSelection.keys()].join(","));
    } else {
      const selection = state.packPayload?.selection || {};
      if (selection.record_id) query.set("record_id", selection.record_id);
      if (selection.symbol) query.set("symbol", selection.symbol);
      if (selection.q) query.set("q", selection.q);
      if (!selection.record_id && !selection.symbol && !selection.q && state.selectedRecord?.id) query.set("record_id", state.selectedRecord.id);
      if (state.packDatasetOrigin?.id) query.set("dataset_ids", state.packDatasetOrigin.id);
      if (query.size === 1) { toast("请先打开记录或汇集研究资料。"); return; }
    }
    const button = $(buttonId); button.disabled = true;
    try {
      const payload = await request(`/api/review-packet?${query}`);
      if (payload.model_calls_performed !== false || payload.local_only !== true || payload.review_status !== "not_performed") throw new Error("服务没有返回明确的本地预备材料状态，已阻止下载。");
      downloadJson(payload, `research-review-inputs-${new Date().toISOString().slice(0, 10)}.json`);
      toast(payload.ready_for_review ? "复核材料已整理；尚未执行双模型。请在明确选择的本地环境中运行。" : "已整理材料与证据缺口；当前证据不足，尚未执行双模型。");
    } catch (error) { toast(`复核材料导出失败：${error.message}`); }
    finally { button.disabled = context === "comparison" && state.compareSelection.size === 0; }
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
  $("pack-close").addEventListener("click", () => { ++state.packRequest; $("research-pack").hidden = true; packBusy(false); $(state.view === "data" ? "data-heading" : "results-heading").focus({preventScroll: true}); });
  $("data-navigation").addEventListener("click", () => { showDataWorkspace(); $("research-pack").hidden = true; loadDatasets(); $("data-heading").focus({preventScroll: true}); });
  $("dataset-search-form").addEventListener("submit", (event) => { event.preventDefault(); loadDatasets(); });
  $("dataset-kind-filter").addEventListener("change", loadDatasets);
  $("dataset-export-button").addEventListener("click", exportDataset);
  $("dataset-research-button").addEventListener("click", openDatasetResearch);
  $("dataset-review-button").addEventListener("click", () => downloadReviewPacket("dataset", "dataset-review-button"));
  $("pack-review-button").addEventListener("click", () => downloadReviewPacket("pack", "pack-review-button"));
  $("comparison-review-button").addEventListener("click", () => downloadReviewPacket("comparison", "comparison-review-button"));
  $("comparison-form").addEventListener("submit", compareDatasets);
  ["comparison-alignment", "comparison-start", "comparison-end"].forEach((id) => $(id).addEventListener("change", () => invalidateComparison()));
  renderCompareSelection();
  refresh();
})();
