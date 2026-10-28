"use strict";

const appRoot = document.getElementById("app");
const nodeElements = new Map();
const toastTimers = new Map();
let activeShortcuts = [];
let shortcutsListenerInstalled = false;
let previewPollTimer = null;
let previewPollInterval = 0;
let treeRequestPending = false;
let activeEvents = 0;

function previewToken() {
  return new URLSearchParams(window.location.hash.slice(1)).get("novaui-preview-token") || "";
}

function requestHeaders(headers = {}) {
  const result = { ...headers };
  const token = previewToken();
  if (token) result["X-NovaUI-Preview-Token"] = token;
  return result;
}

function element(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

function getElement(node, tag, className, seen) {
  const id = String(node.id ?? "");
  let el = id ? nodeElements.get(id) : null;
  if (!el || el.tagName.toLowerCase() !== tag) el = element(tag);
  el.className = [className, node.class_name || ""].filter(Boolean).join(" ");
  el.hidden = node.visible === false;
  const oldStyles = el._novaCustomStyleKeys || [];
  const nextStyles = node.styles && typeof node.styles === "object" ? node.styles : {};
  for (const name of oldStyles) {
    if (!Object.hasOwn(nextStyles, name)) el.style.removeProperty(name);
  }
  for (const [name, value] of Object.entries(nextStyles)) {
    el.style.setProperty(name, String(value));
  }
  el._novaCustomStyleKeys = Object.keys(nextStyles);
  if (id) {
    seen.add(id);
    nodeElements.set(id, el);
  }
  return el;
}

function reconcileChildren(parent, children) {
  const unchanged = parent.childNodes.length === children.length &&
    children.every((child, index) => parent.childNodes[index] === child);
  if (!unchanged) parent.replaceChildren(...children);
}

const chartPalette = ["#4f46e5", "#0e9f83", "#ed8b35", "#d94f70", "#2884c7", "#8b5cf6", "#b5a126", "#64748b"];
const svgNamespace = "http://www.w3.org/2000/svg";
let systemThemeQuery = null;
let systemThemeListener = null;

function applySystemTheme() {
  if (systemThemeQuery) {
    document.documentElement.dataset.theme = systemThemeQuery.matches ? "dark" : "light";
  }
}

function chartSvg(tag, attributes = {}) {
  const node = document.createElementNS(svgNamespace, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
  return node;
}

function renderChart(node, container, availableWidth = 0) {
  const labels = Array.isArray(node.labels) ? node.labels : [];
  const datasets = Array.isArray(node.datasets) ? node.datasets : [];
  const fallbackWidth = node.kind === "doughnut" ? 320 : node.kind === "bar" ? 480 : 640;
  const width = Math.max(220, Math.round(availableWidth || fallbackWidth));
  const height = Number(node.height) || 280;
  const colors = datasets.map((dataset, index) => dataset.color || chartPalette[index % chartPalette.length]);
  container.replaceChildren();
  container.setAttribute("role", "group");
  container.setAttribute("aria-label", node.title || `${node.kind} chart`);
  container._novaChartDrawWidth = width;

  if (!labels.length || !datasets.length || datasets.every(dataset => !dataset.values?.length)) {
    if (node.title) {
      const caption = element("figcaption", "nova-chart-title");
      caption.textContent = String(node.title);
      container.append(caption);
    }
    const empty = element("div", "nova-chart-empty");
    empty.textContent = "No chart data";
    container.append(empty);
    return;
  }

  const svg = chartSvg("svg", {
    viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: "xMidYMid meet",
    width: "100%", height, role: "img",
    "aria-label": `${node.title ? `${node.title}: ` : ""}${node.kind} chart with ${labels.length} categories`,
  });
  const title = chartSvg("title");
  title.textContent = node.title || `${node.kind} chart`;
  svg.append(title);
  if (node.title) {
    const caption = element("figcaption", "nova-chart-title");
    caption.textContent = String(node.title);
    container.append(caption);
  }
  const top = 14, bottom = height - 36;

  if (node.kind === "doughnut") {
    const values = datasets[0].values;
    const total = values.reduce((sum, value) => sum + Number(value), 0);
    if (total <= 0) {
      const empty = element("div", "nova-chart-empty");
      empty.textContent = "No chart data";
      container.append(empty);
      return;
    }
    const radius = Math.min(76, Math.max(48, (height - 54) / 2));
    const circumference = 2 * Math.PI * radius;
    let offset = 0;
    values.forEach((value, index) => {
      const length = circumference * Number(value) / total;
      const circle = chartSvg("circle", {
        cx: width / 2, cy: height / 2, r: radius,
        fill: "none", stroke: chartPalette[index % chartPalette.length], "stroke-width": 30,
        "stroke-dasharray": `${length} ${circumference - length}`,
        "stroke-dashoffset": -offset, transform: `rotate(-90 ${width / 2} ${height / 2})`,
      });
      svg.append(circle);
      offset += length;
    });
    const center = chartSvg("text", { x: width / 2, y: height / 2 + 5, "text-anchor": "middle", class: "nova-chart-center-label" });
    center.textContent = String(total);
    svg.append(center);
  } else {
    const left = 48, right = width - 14;
    const allValues = datasets.flatMap(dataset => dataset.values.map(Number));
    let min = Math.min(0, ...allValues), max = Math.max(0, ...allValues);
    if (min === max) { min -= 1; max += 1; }
    const y = value => bottom - ((value - min) / (max - min)) * (bottom - top);
    const x = index => left + (labels.length < 2 ? (right - left) / 2 : index * (right - left) / (labels.length - 1));

    for (let tick = 0; tick <= 4; tick += 1) {
      const tickY = top + (bottom - top) * tick / 4;
      svg.append(chartSvg("line", { x1: left, y1: tickY, x2: right, y2: tickY, class: "nova-chart-gridline" }));
      const tickLabel = chartSvg("text", { x: left - 8, y: tickY + 4, "text-anchor": "end", class: "nova-chart-axis-label" });
      tickLabel.textContent = String(Math.round(max - (max - min) * tick / 4));
      svg.append(tickLabel);
    }

    const stride = Math.max(1, Math.ceil(labels.length / 8));
    labels.forEach((label, index) => {
      if (index % stride !== 0 && index !== labels.length - 1) return;
      const labelX = node.kind === "bar"
        ? left + (right - left) * (index + .5) / labels.length
        : x(index);
      const tickLabel = chartSvg("text", { x: labelX, y: height - 10, "text-anchor": "middle", class: "nova-chart-axis-label" });
      tickLabel.textContent = label.length > 12 ? `${label.slice(0, 11)}…` : label;
      svg.append(tickLabel);
    });

    datasets.forEach((dataset, seriesIndex) => {
      const values = dataset.values.map(Number);
      const color = colors[seriesIndex];
      if (node.kind === "bar") {
        const band = (right - left) / Math.max(1, labels.length);
        const groupWidth = band * .72;
        const barWidth = groupWidth / datasets.length;
        const zeroY = y(0);
        values.forEach((value, index) => {
          const bar = chartSvg("rect", {
            x: left + band * index + (band - groupWidth) / 2 + seriesIndex * barWidth,
            y: Math.min(y(value), zeroY), width: Math.max(1, barWidth - 3),
            height: Math.max(1, Math.abs(zeroY - y(value))), rx: 4, fill: color,
          });
          const pointTitle = chartSvg("title");
          pointTitle.textContent = `${dataset.label} · ${labels[index]}: ${value}`;
          bar.append(pointTitle);
          svg.append(bar);
        });
      } else {
        const points = values.map((value, index) => [x(index), y(value)]);
        const pathData = points.map(([px, py], index) => `${index ? "L" : "M"}${px},${py}`).join(" ");
        if (node.kind === "area") {
          const lastPoint = points[points.length - 1];
          const area = chartSvg("path", {
            d: `${pathData} L${lastPoint[0]},${y(0)} L${points[0][0]},${y(0)} Z`,
            fill: color, class: "nova-chart-area",
          });
          svg.append(area);
        }
        svg.append(chartSvg("path", { d: pathData, fill: "none", stroke: color, class: "nova-chart-line" }));
        points.forEach(([px, py], index) => {
          const point = chartSvg("circle", { cx: px, cy: py, r: 3.5, fill: color, class: "nova-chart-point" });
          const pointTitle = chartSvg("title");
          pointTitle.textContent = `${dataset.label} · ${labels[index]}: ${values[index]}`;
          point.append(pointTitle);
          svg.append(point);
        });
      }
    });
  }

  container.append(svg);
  const legend = element("div", "nova-chart-legend");
  const legendItems = node.kind === "doughnut"
    ? labels.map((label, index) => ({ label, color: chartPalette[index % chartPalette.length], value: datasets[0].values[index] }))
    : datasets.map((dataset, index) => ({ label: dataset.label, color: colors[index] }));
  legendItems.forEach(itemData => {
    const item = element("span", "nova-chart-legend-item");
    const swatch = element("span", "nova-chart-swatch");
    swatch.style.backgroundColor = itemData.color;
    swatch.setAttribute("aria-hidden", "true");
    const label = element("span");
    label.textContent = itemData.value === undefined
      ? String(itemData.label)
      : `${itemData.label}: ${itemData.value}`;
    item.append(swatch, label);
    legend.append(item);
  });
  container.append(legend);
}

function observeChart(node, container) {
  container._novaChartData = node;
  if (container._novaChartObserver || typeof ResizeObserver !== "function") return;
  container._novaChartObserver = new ResizeObserver(entries => {
    const width = Math.round(entries[0]?.contentRect.width || 0);
    if (!width || Math.abs(width - container._novaChartDrawWidth) < 2) return;
    renderChart(container._novaChartData, container, width);
  });
  container._novaChartObserver.observe(container);
}

function applyDimensions(el, node) {
  el.style.width = node.width == null ? "" : `${node.width}px`;
  el.style.height = node.height == null ? "" : `${node.height}px`;
}

const iconPaths = {
  home: ["M3 10.8 12 3l9 7.8", "M5.5 9.5v10h13v-10", "M9.5 19.5v-6h5v6"],
  grid: ["M4 4h6v6H4z", "M14 4h6v6h-6z", "M4 14h6v6H4z", "M14 14h6v6h-6z"],
  search: ["M10.8 4a6.8 6.8 0 1 0 0 13.6 6.8 6.8 0 0 0 0-13.6Z", "m16 16 4.2 4.2"],
  settings: ["M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z", "m19.4 15 .1.1a1.7 1.7 0 0 1-2.4 2.4l-.1-.1a1.7 1.7 0 0 0-2.9 1.2v.2a1.7 1.7 0 0 1-3.4 0v-.2a1.7 1.7 0 0 0-2.9-1.2l-.1.1a1.7 1.7 0 1 1-2.4-2.4l.1-.1a1.7 1.7 0 0 0-1.2-2.9H4a1.7 1.7 0 0 1 0-3.4h.2a1.7 1.7 0 0 0 1.2-2.9l-.1-.1a1.7 1.7 0 1 1 2.4-2.4l.1.1a1.7 1.7 0 0 0 2.9-1.2V4a1.7 1.7 0 0 1 3.4 0v.2a1.7 1.7 0 0 0 2.9 1.2l.1-.1a1.7 1.7 0 1 1 2.4 2.4l-.1.1a1.7 1.7 0 0 0 1.2 2.9h.2a1.7 1.7 0 0 1 0 3.4h-.2a1.7 1.7 0 0 0-1.2.9Z"],
  plus: ["M12 5v14", "M5 12h14"], minus: ["M5 12h14"],
  arrow_right: ["M4 12h15", "m13 5 7 7-7 7"], chevron_right: ["m9 18 6-6-6-6"],
  chart: ["M4 19V5", "M4 19h17", "m7 15 4-5 3 2 5-7"],
  users: ["M16 20v-1.5a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4V20", "M10 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z", "M16 3.2a4 4 0 0 1 0 7.6", "M20 20v-1.5a4 4 0 0 0-3-3.9"],
  file: ["M13 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10z", "M13 3v7h7", "M8 14h8", "M8 18h8"],
  check: ["m5 12 4 4L19 6"], close: ["m6 6 12 12", "M18 6 6 18"],
  menu: ["M4 6h16", "M4 12h16", "M4 18h16"], sun: ["M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z", "M12 2v2", "M12 20v2", "m4.9 4.9 1.4 1.4", "m17.7 17.7 1.4 1.4", "M2 12h2", "M20 12h2", "m4.9 19.1 1.4-1.4", "m17.7 6.3 1.4-1.4"],
  moon: ["M20.5 14.3A8.5 8.5 0 0 1 9.7 3.5 8.5 8.5 0 1 0 20.5 14.3Z"],
  sparkles: ["m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z", "m19 14 1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1 1-2.5Z"],
  download: ["M12 3v12", "m7 10 5 5 5-5", "M5 20h14"], folder: ["M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"],
  heart: ["M20.8 8.8c0 5.2-8.8 10-8.8 10s-8.8-4.8-8.8-10A4.8 4.8 0 0 1 12 6.2a4.8 4.8 0 0 1 8.8 2.6Z"],
  clock: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z", "M12 6v6l4 2"],
  cube: ["m12 3 9 5v8l-9 5-9-5V8z", "m3.5 8.2 8.5 4.7 8.5-4.7", "M12 13v8", "m7.5 5.5 9 5"]
};

function createIcon(name, size = 18, className = "nova-icon-svg") {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("class", className);
  for (const d of iconPaths[name] || []) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

function syncIcon(container, name, size, className = "nova-icon-svg") {
  const signature = `${name}:${size}:${className}`;
  if (container._novaIconSignature === signature && container.firstElementChild?.tagName.toLowerCase() === "svg") return;
  container.replaceChildren(createIcon(name, size, className));
  container._novaIconSignature = signature;
}

async function sendEvent(payload) {
  activeEvents += 1;
  try {
    const response = await fetch("/api/event", {
      method: "POST",
      headers: requestHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Action failed");
    clearDiagnostic();
    renderTree(data);
  } catch (error) {
    showDiagnostic(error instanceof Error ? error.message : "The action failed. Please try again.");
    throw error;
  } finally {
    activeEvents -= 1;
  }
}

function showDiagnostic(message) {
  const diagnostic = document.getElementById("novaui-diagnostic");
  if (!diagnostic) return;
  diagnostic.textContent = `NovaUI action failed: ${message}`;
  diagnostic.hidden = false;
}

function clearDiagnostic() {
  const diagnostic = document.getElementById("novaui-diagnostic");
  if (!diagnostic) return;
  diagnostic.textContent = "";
  diagnostic.hidden = true;
}

function installShortcuts(shortcuts) {
  activeShortcuts = Array.isArray(shortcuts) ? shortcuts : [];
  if (shortcutsListenerInstalled) return;
  shortcutsListenerInstalled = true;
  document.addEventListener("keydown", event => {
    if (event.repeat) return;
    const target = event.target;
    const isTextEntry = target instanceof Element && (
      target.matches("input, textarea, select") || target.isContentEditable ||
      Boolean(target.closest("[contenteditable=true]"))
    );
    const key = event.key === " " ? "Space" : event.key.length === 1 ? event.key.toUpperCase() : event.key;
    const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
    const actualModifiers = [];
    if (event.ctrlKey) actualModifiers.push("ctrl");
    if (event.metaKey) actualModifiers.push("meta");
    if (event.altKey) actualModifiers.push("alt");
    if (event.shiftKey) actualModifiers.push("shift");
    for (const shortcut of activeShortcuts) {
      const parts = String(shortcut.key || "").split("+").map(part => part.toLowerCase());
      const expectedKey = parts.pop();
      const expectedModifiers = parts.map(part => part === "mod" ? (mac ? "meta" : "ctrl") : part);
      if (expectedKey !== key.toLowerCase()) continue;
      if (expectedModifiers.length !== actualModifiers.length ||
          expectedModifiers.some(modifier => !actualModifiers.includes(modifier))) continue;
      if (isTextEntry && !shortcut.allow_in_inputs) continue;
      if (shortcut.prevent_default) event.preventDefault();
      sendEvent({ event_id: shortcut.event_id }).catch(error => console.error(error));
      break;
    }
  });
}

function renderNode(node, seen) {
  if (!node || typeof node.type !== "string") return element("div", "error");
  let el;

  switch (node.type) {
    case "scaffold": {
      el = getElement(node, "div", "nova-scaffold", seen);
      const collapsed = el.classList.contains("is-collapsed");
      el.style.gridTemplateColumns = `${collapsed ? 72 : Number(node.sidebar_width) || 256}px minmax(0, 1fr)`;

      let aside = el.querySelector(":scope > .nova-scaffold-sidebar");
      if (!aside) aside = element("aside", "nova-scaffold-sidebar");
      let collapseButton = aside.querySelector(":scope > .nova-scaffold-collapse");
      if (!collapseButton) collapseButton = element("button", "nova-scaffold-collapse");
      collapseButton.type = "button";
      collapseButton.textContent = collapsed ? "Expand navigation" : "Collapse navigation";
      collapseButton.setAttribute("aria-label", collapseButton.textContent);
      collapseButton.setAttribute("aria-expanded", String(!collapsed));
      collapseButton.hidden = node.collapsible === false;
      collapseButton.onclick = () => {
        const nextCollapsed = !el.classList.contains("is-collapsed");
        el.classList.toggle("is-collapsed", nextCollapsed);
        el.style.gridTemplateColumns = `${nextCollapsed ? 72 : Number(node.sidebar_width) || 256}px minmax(0, 1fr)`;
        collapseButton.textContent = nextCollapsed ? "Expand navigation" : "Collapse navigation";
        collapseButton.setAttribute("aria-label", collapseButton.textContent);
        collapseButton.setAttribute("aria-expanded", String(!nextCollapsed));
      };
      let brand = aside.querySelector(":scope > .nova-scaffold-brand");
      if (!brand) brand = element("div", "nova-scaffold-brand");
      if (node.brand) {
        reconcileChildren(brand, [renderNode(node.brand, seen)]);
        brand.hidden = false;
      } else {
        reconcileChildren(brand, []);
        brand.hidden = true;
      }

      let navigation = aside.querySelector(":scope > .nova-scaffold-navigation");
      if (!navigation) navigation = element("nav", "nova-scaffold-navigation");
      navigation.setAttribute("aria-label", String(node.label || "Primary navigation"));
      const oldItems = [...navigation.querySelectorAll(":scope > .nova-scaffold-nav-item")];
      const items = (Array.isArray(node.destinations) ? node.destinations : []).map((destination, index) => {
        const button = oldItems[index] || element("button", "nova-scaffold-nav-item");
        button.type = "button";
        button.className = `nova-scaffold-nav-item${destination.active ? " active" : ""}`;
        button.title = String(destination.label || "Navigate");
        button.setAttribute("aria-label", String(destination.label || "Navigate"));
        if (destination.active) button.setAttribute("aria-current", "page");
        else button.removeAttribute("aria-current");

        let icon = button.querySelector(":scope > .nova-scaffold-nav-icon");
        if (!icon) icon = element("span", "nova-scaffold-nav-icon");
        if (destination.icon && iconPaths[destination.icon]) {
          syncIcon(icon, destination.icon, 19);
        } else {
          icon.textContent = String(destination.label || "?").trim().slice(0, 1).toUpperCase();
        }
        icon.setAttribute("aria-hidden", "true");

        let label = button.querySelector(":scope > .nova-scaffold-nav-label");
        if (!label) label = element("span", "nova-scaffold-nav-label");
        label.textContent = String(destination.label || "");
        const children = [icon, label];
        if (destination.badge !== null && destination.badge !== undefined) {
          let badge = button.querySelector(":scope > .nova-scaffold-nav-badge");
          if (!badge) badge = element("span", "nova-scaffold-nav-badge");
          badge.textContent = String(destination.badge);
          children.push(badge);
        }
        reconcileChildren(button, children);
        button.onclick = () => sendEvent({ event_id: destination.event_id }).catch(error => console.error(error));
        return button;
      });
      reconcileChildren(navigation, items);
      reconcileChildren(aside, [collapseButton, brand, navigation]);

      let header = el.querySelector(":scope > .nova-scaffold-topbar");
      if (!header) header = element("header", "nova-scaffold-topbar");
      header.hidden = !node.top_bar;
      reconcileChildren(header, node.top_bar ? [renderNode(node.top_bar, seen)] : []);

      let main = el.querySelector(":scope > .nova-scaffold-body");
      if (!main) main = element("main", "nova-scaffold-body");
      reconcileChildren(main, [renderNode(node.body, seen)]);

      let floatingAction = el.querySelector(":scope > .nova-scaffold-floating-action");
      if (!floatingAction) floatingAction = element("div", "nova-scaffold-floating-action");
      floatingAction.hidden = !node.floating_action;
      reconcileChildren(floatingAction, node.floating_action ? [renderNode(node.floating_action, seen)] : []);
      reconcileChildren(el, [aside, header, main, floatingAction]);
      return el;
    }

    case "navigation": {
      el = getElement(node, "nav", `nova-navigation orientation-${node.orientation || "horizontal"}`, seen);
      el.setAttribute("aria-label", String(node.label || "Application navigation"));
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;
    }

    case "chart":
      el = getElement(node, "figure", "nova-chart", seen);
      el.style.width = node.width == null ? "" : `${node.width}px`;
      el.style.height = "";
      renderChart(node, el, el.clientWidth ? el.clientWidth - 32 : 0);
      observeChart(node, el);
      return el;

    case "fragment":
      el = getElement(node, "div", "nova-fragment", seen);
      el.style.display = "contents";
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "dropdown": {
      el = getElement(node, "details", "nova-dropdown", seen);
      if (!el.dataset.novaInitialized) {
        el.open = Boolean(node.open);
        el.dataset.novaInitialized = "true";
      }
      let summary = el.querySelector(":scope > summary");
      if (!summary) summary = element("summary");
      summary.textContent = String(node.label || "More");
      const content = (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen));
      reconcileChildren(el, [summary, ...content]);
      return el;
    }

    case "tooltip": {
      el = getElement(node, "div", "nova-tooltip-wrap", seen);
      const child = node.children?.[0] ? renderNode(node.children[0], seen) : element("div");
      const descriptionId = `${node.id}-description`;
      const target = child.matches?.("button,input,select,textarea,a,[tabindex]") ?
        child : child.querySelector?.("button,input,select,textarea,a,[tabindex]");
      if (target) {
        target.setAttribute("aria-describedby", descriptionId);
        el.removeAttribute("tabindex");
      } else {
        child.tabIndex = 0;
        child.setAttribute("aria-describedby", descriptionId);
        el.removeAttribute("tabindex");
      }
      let description = el.querySelector(".nova-tooltip-content");
      if (!description) description = element("span", "nova-tooltip-content");
      description.id = descriptionId;
      description.setAttribute("role", "tooltip");
      description.textContent = String(node.text || "");
      reconcileChildren(el, [child, description]);
      return el;
    }

    case "context_menu": {
      el = getElement(node, "div", "nova-context-menu", seen);
      const child = node.children?.[0] ? renderNode(node.children[0], seen) : element("span");
      const target = child.matches?.("button,input,select,textarea,a,[tabindex]") ?
        child : child.querySelector?.("button,input,select,textarea,a,[tabindex]");
      const trigger = target || child;
      if (!target && !trigger.hasAttribute("tabindex")) trigger.tabIndex = 0;
      trigger.setAttribute("aria-haspopup", "menu");
      trigger.setAttribute("aria-expanded", "false");
      if (!target) trigger.setAttribute("aria-label", String(node.label || "Actions"));

      let menu = el.querySelector(".nova-context-menu-list");
      if (!menu) menu = element("div", "nova-context-menu-list");
      menu.setAttribute("role", "menu");
      menu.setAttribute("aria-label", String(node.label || "Actions"));
      menu.hidden = true;
      const buttons = (Array.isArray(node.actions) ? node.actions : []).map(action => {
        const button = element("button", "nova-context-menu-item");
        button.type = "button";
        button.setAttribute("role", "menuitem");
        button.textContent = String(action.label);
        button.onclick = async () => {
          menu.hidden = true;
          trigger.setAttribute("aria-expanded", "false");
          try {
            await sendEvent({ event_id: action.event_id });
          } catch (error) {
            console.error(error);
          }
        };
        return button;
      });
      reconcileChildren(menu, buttons);

      const openMenu = (x, y) => {
        menu.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        menu.style.left = `${Math.max(4, Math.min(x, window.innerWidth - menu.offsetWidth - 4))}px`;
        menu.style.top = `${Math.max(4, Math.min(y, window.innerHeight - menu.offsetHeight - 4))}px`;
        buttons[0]?.focus();
      };
      el.oncontextmenu = event => {
        event.preventDefault();
        openMenu(event.clientX, event.clientY);
      };
      el.onkeydown = event => {
        if (event.key === "ContextMenu" || (event.shiftKey && event.key === "F10")) {
          event.preventDefault();
          const bounds = trigger.getBoundingClientRect();
          openMenu(bounds.left, bounds.bottom);
          return;
        }
        if (menu.hidden) return;
        const index = buttons.indexOf(document.activeElement);
        if (event.key === "Escape") {
          event.preventDefault();
          menu.hidden = true;
          trigger.setAttribute("aria-expanded", "false");
          trigger.focus();
        } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
          event.preventDefault();
          const offset = event.key === "ArrowDown" ? 1 : -1;
          buttons[(index + offset + buttons.length) % buttons.length]?.focus();
        } else if (event.key === "Home") {
          event.preventDefault();
          buttons[0]?.focus();
        } else if (event.key === "End") {
          event.preventDefault();
          buttons[buttons.length - 1]?.focus();
        }
      };
      el.onfocusout = event => {
        if (!el.contains(event.relatedTarget)) {
          menu.hidden = true;
          trigger.setAttribute("aria-expanded", "false");
        }
      };
      reconcileChildren(el, [child, menu]);
      return el;
    }

    case "animated":
      el = getElement(node, "div", `nova-animated enter-${node.enter}`, seen);
      el.style.animationDuration = `${Number(node.duration) || 0}ms`;
      el.style.animationTimingFunction = node.easing || "ease-out";
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "text":
      el = getElement(node, "div", "nova-text", seen);
      applyDimensions(el, node);
      if (el.textContent !== String(node.text ?? "")) el.textContent = String(node.text ?? "");
      el.style.fontSize = Number.isFinite(node.size) ? `${node.size}px` : "";
      el.style.fontWeight = node.bold ? "700" : "";
      el.style.color = node.color || "";
      return el;

    case "icon":
      el = getElement(node, "span", "nova-icon", seen);
      syncIcon(el, String(node.name || ""), Number(node.size) || 18);
      if (node.label) {
        el.setAttribute("role", "img");
        el.setAttribute("aria-label", String(node.label));
        el.removeAttribute("aria-hidden");
      } else {
        el.setAttribute("aria-hidden", "true");
        el.removeAttribute("role");
        el.removeAttribute("aria-label");
      }
      return el;

    case "image":
      el = getElement(node, "img", "nova-image", seen);
      applyDimensions(el, node);
      el.src = String(node.src || "");
      el.alt = String(node.alt || "");
      return el;

    case "button":
      el = getElement(node, "button", `nova-button ${node.variant === "secondary" ? "secondary" : "primary"}`, seen);
      applyDimensions(el, node);
      el.type = "button";
      if (node.class_name?.split(/\s+/).includes("nova-navigation-item") &&
          node.class_name.split(/\s+/).includes("active")) {
        el.setAttribute("aria-current", "page");
      } else {
        el.removeAttribute("aria-current");
      }
      if (node.icon && iconPaths[node.icon]) {
        let icon = el.querySelector(".nova-button-icon");
        if (!icon) icon = element("span", "nova-button-icon");
        syncIcon(icon, node.icon, 17);
        icon.setAttribute("aria-hidden", "true");
        let label = el.querySelector(".nova-button-label");
        if (!label) label = element("span", "nova-button-label");
        label.textContent = String(node.label ?? "Button");
        reconcileChildren(el, [icon, label]);
      } else {
        const label = String(node.label ?? "Button");
        if (el.childNodes.length !== 1 || el.firstChild.nodeType !== Node.TEXT_NODE) {
          el.replaceChildren(document.createTextNode(label));
        } else if (el.firstChild.nodeValue !== label) {
          el.firstChild.nodeValue = label;
        }
      }
      el.disabled = Boolean(node.disabled);
      el.onclick = node.event_id ? async () => {
        el.disabled = true;
        try {
          await sendEvent({ event_id: node.event_id });
        } catch (error) {
          console.error(error);
          el.disabled = Boolean(node.disabled);
        }
      } : null;
      return el;

    case "icon_button": {
      el = getElement(node, "button", `nova-icon-button nova-button ${node.variant === "secondary" ? "secondary" : "primary"} size-${node.size || "medium"}`, seen);
      applyDimensions(el, node);
      el.type = "button";
      el.setAttribute("aria-label", String(node.label || "Action"));
      el.title = String(node.label || "Action");
      el.disabled = Boolean(node.disabled);
      let glyph = el.querySelector(".nova-icon-button-glyph");
      if (!glyph) glyph = element("span", "nova-icon-button-glyph");
      glyph.setAttribute("aria-hidden", "true");
      if (iconPaths[node.icon]) syncIcon(glyph, node.icon, 19);
      else glyph.textContent = String(node.icon || "•");
      reconcileChildren(el, [glyph]);
      el.onclick = node.event_id ? async () => {
        el.disabled = true;
        try {
          await sendEvent({ event_id: node.event_id });
        } catch (error) {
          console.error(error);
          el.disabled = Boolean(node.disabled);
        }
      } : null;
      return el;
    }

    case "badge":
      el = getElement(node, "span", `nova-badge tone-${node.tone || "neutral"}`, seen);
      el.textContent = String(node.label ?? "");
      return el;

    case "divider": {
      const vertical = node.orientation === "vertical";
      el = getElement(node, vertical ? "div" : "hr", `nova-divider orientation-${vertical ? "vertical" : "horizontal"}`, seen);
      el.setAttribute("role", "separator");
      el.setAttribute("aria-orientation", vertical ? "vertical" : "horizontal");
      return el;
    }

    case "progress_bar": {
      el = getElement(node, "div", "nova-progress", seen);
      const max = Number(node.max_value) || 100;
      const value = Number(node.value) || 0;
      const percent = Math.max(0, Math.min(100, (value / max) * 100));
      el.setAttribute("role", "progressbar");
      el.setAttribute("aria-label", String(node.label || "Progress"));
      el.setAttribute("aria-valuemin", "0");
      el.setAttribute("aria-valuemax", String(max));
      el.setAttribute("aria-valuenow", String(value));
      let track = el.querySelector(".nova-progress-track");
      if (!track) track = element("span", "nova-progress-track");
      let fill = track.querySelector(".nova-progress-fill");
      if (!fill) fill = element("span", "nova-progress-fill");
      fill.style.width = `${percent}%`;
      reconcileChildren(track, [fill]);
      const children = [track];
      if (node.show_value) {
        let valueLabel = el.querySelector(".nova-progress-value");
        if (!valueLabel) valueLabel = element("span", "nova-progress-value");
        valueLabel.setAttribute("aria-hidden", "true");
        valueLabel.textContent = `${Math.round(percent)}%`;
        children.push(valueLabel);
      }
      reconcileChildren(el, children);
      return el;
    }

    case "skeleton": {
      el = getElement(node, "div", `nova-skeleton variant-${node.variant || "text"}`, seen);
      applyDimensions(el, node);
      el.setAttribute("aria-hidden", "true");
      const lines = Array.from({ length: Math.max(1, Math.min(12, Number(node.lines) || 1)) }, (_, index) => {
        const line = element("span", "nova-skeleton-line");
        if (index === Number(node.lines) - 1 && Number(node.lines) > 1) line.classList.add("last-line");
        return line;
      });
      reconcileChildren(el, lines);
      return el;
    }

    case "input": {
      el = getElement(node, "label", "nova-field", seen);
      applyDimensions(el, node);
      let label = el.querySelector(".field-label");
      if (node.label) {
        if (!label) label = element("span", "field-label");
        label.textContent = String(node.label);
      } else if (label) {
        label.remove();
        label = null;
      }
      let input = el.querySelector("input");
      if (!input) input = element("input", "nova-input");
      input.id = `${node.id}-input`;
      el.htmlFor = node.label ? input.id : "";
      input.type = node.input_type || (node.password ? "password" : "text");
      input.name = node.name || "";
      input.placeholder = String(node.placeholder ?? "");
      input.required = Boolean(node.required);
      if (node.min_length == null) input.removeAttribute("minlength");
      else input.minLength = Number(node.min_length);
      if (node.max_length == null) input.removeAttribute("maxlength");
      else input.maxLength = Number(node.max_length);
      if (node.min_value == null) input.removeAttribute("min");
      else input.min = String(node.min_value);
      if (node.max_value == null) input.removeAttribute("max");
      else input.max = String(node.max_value);
      if (node.step == null) input.removeAttribute("step");
      else input.step = String(node.step);
      if (node.label) input.removeAttribute("aria-label");
      else input.setAttribute("aria-label", input.placeholder || "Input");
      const value = String(node.value ?? "");
      if (input.value !== value) input.value = value;
      input.disabled = Boolean(node.disabled);
      input.readOnly = Boolean(node.read_only);
      let error = el.querySelector(".field-error");
      if (node.error) {
        if (!error) error = element("span", "field-error");
        error.id = `${node.id}-error`;
        error.setAttribute("role", "alert");
        error.textContent = String(node.error);
        input.setAttribute("aria-invalid", "true");
        input.setAttribute("aria-describedby", error.id);
      } else {
        if (error) error.remove();
        input.removeAttribute("aria-invalid");
        input.removeAttribute("aria-describedby");
        error = null;
      }
      input.onchange = node.event_id ? () => {
        input._novaPendingEvent = sendEvent({ event_id: node.event_id, value: input.value }).catch(error => {
          console.error(error);
        });
      } : null;
      reconcileChildren(el, [...(label ? [label] : []), input, ...(error ? [error] : [])]);
      return el;
    }

    case "text_area": {
      el = getElement(node, "label", "nova-field", seen);
      applyDimensions(el, node);
      let label = el.querySelector(".field-label");
      if (!label) label = element("span", "field-label");
      label.textContent = String(node.label || "Text");
      let input = el.querySelector("textarea");
      if (!input) input = element("textarea", "nova-input nova-textarea");
      input.id = `${node.id}-input`;
      el.htmlFor = input.id;
      input.placeholder = String(node.placeholder ?? "");
      input.rows = Number(node.rows) || 4;
      input.required = Boolean(node.required);
      if (node.max_length == null) input.removeAttribute("maxlength");
      else input.maxLength = Number(node.max_length);
      const value = String(node.value ?? "");
      if (input.value !== value) input.value = value;
      input.disabled = Boolean(node.disabled);
      input.readOnly = Boolean(node.read_only);
      input.onchange = node.event_id ? () => {
        sendEvent({ event_id: node.event_id, value: input.value }).catch(error => console.error(error));
      } : null;
      reconcileChildren(el, [label, input]);
      return el;
    }

    case "checkbox":
    case "switch": {
      const isSwitch = node.type === "switch";
      el = getElement(node, "label", isSwitch ? "nova-checkbox nova-switch" : "nova-checkbox", seen);
      applyDimensions(el, node);
      el.classList.toggle("disabled", Boolean(node.disabled));
      let input = el.querySelector("input");
      if (!input) input = element("input");
      input.type = "checkbox";
      input.checked = Boolean(node.checked);
      input.disabled = Boolean(node.disabled);
      input.setAttribute("aria-label", String(node.label || "Toggle"));
      if (isSwitch) {
        input.setAttribute("role", "switch");
        input.setAttribute("aria-checked", input.checked ? "true" : "false");
      } else {
        input.removeAttribute("role");
        input.removeAttribute("aria-checked");
      }
      input.onchange = node.event_id ? () => {
        sendEvent({ event_id: node.event_id, value: input.checked ? "true" : "false" })
          .catch(error => console.error(error));
      } : null;
      let label = el.querySelector(".nova-checkbox-label");
      if (!label) label = element("span", "nova-checkbox-label");
      label.textContent = String(node.label || "Toggle");
      reconcileChildren(el, [input, label]);
      return el;
    }

    case "slider": {
      el = getElement(node, "label", "nova-slider", seen);
      applyDimensions(el, node);
      let label = el.querySelector(".field-label");
      if (!label) label = element("span", "field-label");
      label.textContent = String(node.label || "Value");
      let input = el.querySelector("input");
      if (!input) input = element("input", "nova-slider-input");
      input.type = "range";
      input.id = `${node.id}-range`;
      el.htmlFor = input.id;
      input.min = String(node.min_value);
      input.max = String(node.max_value);
      input.step = String(node.step ?? 1);
      input.disabled = Boolean(node.disabled);
      const value = String(node.value ?? node.min_value);
      if (input.value !== value) input.value = value;
      input.setAttribute("aria-valuetext", value);
      input.onchange = node.event_id ? () => {
        sendEvent({ event_id: node.event_id, value: input.value }).catch(error => console.error(error));
      } : null;
      let output = el.querySelector("output");
      if (!output) output = element("output", "nova-slider-output");
      output.htmlFor = input.id;
      output.textContent = value;
      reconcileChildren(el, [label, input, output]);
      return el;
    }

    case "select": {
      el = getElement(node, "label", "nova-field", seen);
      applyDimensions(el, node);
      let label = el.querySelector(".field-label");
      if (!label) label = element("span", "field-label");
      label.textContent = String(node.label || "Choose an option");
      let select = el.querySelector("select");
      if (!select) select = element("select", "nova-input nova-select");
      select.id = `${node.id}-select`;
      el.htmlFor = select.id;
      const selected = String(node.value ?? "");
      const options = (Array.isArray(node.options) ? node.options : []).map(option => {
        const item = element("option");
        item.value = String(option.value);
        item.textContent = String(option.label);
        item.selected = item.value === selected;
        return item;
      });
      select.disabled = Boolean(node.disabled);
      select.onchange = node.event_id ? () => {
        sendEvent({ event_id: node.event_id, value: select.value }).catch(error => console.error(error));
      } : null;
      reconcileChildren(select, options);
      reconcileChildren(el, [label, select]);
      return el;
    }

    case "search_field": {
      el = getElement(node, "div", "nova-search-field", seen);
      const field = node.children?.[0] ? renderNode(node.children[0], seen) : element("label", "nova-field");
      const value = node.children?.[0]?.value || "";
      const input = field.querySelector("input");
      let clear = el.querySelector(".nova-search-clear");
      if (!clear) clear = element("button", "nova-button secondary nova-search-clear");
      clear.type = "button";
      clear.textContent = "Clear";
      clear.setAttribute("aria-label", "Clear search");
      clear.hidden = !node.clear_event_id;
      clear.disabled = Boolean(node.disabled);
      clear.onclick = node.clear_event_id ? async () => {
        clear.disabled = true;
        try {
          await sendEvent({ event_id: node.clear_event_id });
        } catch (error) {
          console.error(error);
          clear.disabled = Boolean(node.disabled);
        }
      } : null;
      let submit = el.querySelector(".nova-search-submit");
      if (!submit) submit = element("button", "nova-button primary nova-search-submit");
      submit.type = "button";
      submit.textContent = "Search";
      submit.setAttribute("aria-label", "Submit search");
      submit.disabled = Boolean(node.disabled);
      submit.onclick = async () => {
        if (!node.submit_event_id) return;
        submit.disabled = true;
        try {
          await sendEvent({ event_id: node.submit_event_id });
        } catch (error) {
          console.error(error);
          submit.disabled = Boolean(node.disabled);
        }
      };
      if (input) input.onkeydown = event => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        input.dispatchEvent(new Event("change", { bubbles: true }));
        Promise.resolve(input._novaPendingEvent).then(() => submit.click());
      };
      reconcileChildren(el, [field, ...(value ? [clear] : []), submit]);
      return el;
    }

    case "radio_group": {
      el = getElement(node, "fieldset", "nova-choice-group nova-radio-group", seen);
      let legend = el.querySelector(":scope > legend");
      if (!legend) legend = element("legend");
      legend.textContent = String(node.label || "Choose an option");
      const options = (Array.isArray(node.options) ? node.options : []).map((option, index) => {
        const label = element("label", "nova-choice-option");
        const input = element("input");
        input.type = "radio";
        input.name = node.id;
        input.id = `${node.id}-option-${index}`;
        input.value = String(option.value);
        input.checked = option.value === node.value;
        input.disabled = Boolean(node.disabled);
        input.onchange = () => {
          if (option.event_id) sendEvent({ event_id: option.event_id }).catch(error => console.error(error));
        };
        const text = element("span");
        text.textContent = String(option.label);
        label.htmlFor = input.id;
        reconcileChildren(label, [input, text]);
        return label;
      });
      reconcileChildren(el, [legend, ...options]);
      return el;
    }

    case "multi_select": {
      el = getElement(node, "fieldset", "nova-choice-group nova-multi-select", seen);
      let legend = el.querySelector(":scope > legend");
      if (!legend) legend = element("legend");
      legend.textContent = String(node.label || "Choose options");
      const selected = new Set(Array.isArray(node.selected) ? node.selected : []);
      const options = (Array.isArray(node.options) ? node.options : []).map((option, index) => {
        const label = element("label", "nova-choice-option");
        const input = element("input");
        input.type = "checkbox";
        input.id = `${node.id}-option-${index}`;
        input.value = String(option.value);
        input.checked = selected.has(option.value);
        input.disabled = Boolean(node.disabled);
        input.onchange = () => {
          const values = [...el.querySelectorAll('input[type="checkbox"]:checked')].map(item => item.value);
          if (node.event_id) {
            sendEvent({ event_id: node.event_id, value: JSON.stringify(values) }).catch(error => console.error(error));
          }
        };
        const text = element("span");
        text.textContent = String(option.label);
        label.htmlFor = input.id;
        reconcileChildren(label, [input, text]);
        return label;
      });
      reconcileChildren(el, [legend, ...options]);
      return el;
    }

    case "data_table": {
      el = getElement(node, "section", "nova-data-table", seen);
      el.setAttribute("role", "region");
      el.setAttribute("aria-label", "Data table");
      const children = [];
      const toolbarItems = [];
      if (node.searchable) {
        let search = el.querySelector(".nova-table-search");
        if (!search) search = element("input", "nova-table-search");
        search.type = "search";
        search.placeholder = "Search rows";
        search.setAttribute("aria-label", "Search table rows");
        if (search.value !== String(node.search_value || "")) search.value = String(node.search_value || "");
        search.disabled = Boolean(node.loading);
        search.onchange = () => node.search_event_id && sendEvent({ event_id: node.search_event_id, value: search.value })
          .catch(error => console.error(error));
        toolbarItems.push(search);
      }
      if (node.column_controls?.length) {
        const controls = element("div", "nova-table-columns");
        controls.setAttribute("aria-label", "Column visibility");
        for (const column of node.column_controls) {
          const button = element("button", "nova-button secondary");
          button.type = "button";
          button.textContent = String(column.title);
          button.setAttribute("aria-pressed", column.visible ? "true" : "false");
          button.disabled = Boolean(node.loading || !column.event_id);
          if (column.event_id) {
            button.onclick = () => sendEvent({ event_id: column.event_id }).catch(error => console.error(error));
          }
          controls.append(button);
        }
        toolbarItems.push(controls);
      }
      for (const action of node.bulk_actions || []) {
        const button = element("button", "nova-button secondary");
        button.type = "button";
        button.textContent = String(action.label);
        button.disabled = Boolean(node.loading || !action.event_id);
        if (action.event_id) {
          button.onclick = () => sendEvent({ event_id: action.event_id }).catch(error => console.error(error));
        }
        toolbarItems.push(button);
      }
      if (node.export_event_id) {
        const button = element("button", "nova-button secondary");
        button.type = "button";
        button.textContent = "Export CSV";
        button.disabled = Boolean(node.loading);
        button.onclick = () => sendEvent({ event_id: node.export_event_id }).catch(error => console.error(error));
        toolbarItems.push(button);
      }
      if (toolbarItems.length) {
        const toolbar = element("div", "nova-table-toolbar");
        reconcileChildren(toolbar, toolbarItems);
        children.push(toolbar);
      }
      if (typeof node.export_csv === "string") {
        const blob = new Blob([node.export_csv], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = element("a");
        link.href = url;
        link.download = "novaui-export.csv";
        link.click();
        URL.revokeObjectURL(url);
      }

      let tableWrap = el.querySelector(".nova-table-scroll");
      if (!tableWrap) tableWrap = element("div", "nova-table-scroll");
      tableWrap.classList.toggle("mobile-cards", node.mobile_layout === "cards");
      let table = tableWrap.querySelector("table");
      if (!table) table = element("table", "nova-table");
      table.classList.toggle("mobile-cards", node.mobile_layout === "cards");
      table.setAttribute("aria-busy", node.loading ? "true" : "false");
      let thead = table.querySelector("thead");
      if (!thead) thead = element("thead");
      let headerRow = thead.querySelector("tr");
      if (!headerRow) headerRow = element("tr");
      const headers = [];
      if (node.selectable) {
        const th = element("th", "nova-table-select-heading");
        th.scope = "col";
        const selectAll = element("input");
        selectAll.type = "checkbox";
        selectAll.checked = Boolean(node.all_visible_selected);
        selectAll.disabled = Boolean(node.loading || !node.rows.length);
        selectAll.setAttribute("aria-label", "Select all rows on this page");
        selectAll.onchange = () => node.select_all_event_id && sendEvent({ event_id: node.select_all_event_id })
          .catch(error => console.error(error));
        th.append(selectAll);
        headers.push(th);
      }
      for (const column of node.columns) {
        const th = element("th");
        th.scope = "col";
        if (column.width) th.style.width = String(column.width);
        if (column.sort_event_id) {
          const sort = element("button", "nova-table-sort");
          sort.type = "button";
          const indicator = column.sort_direction === "asc" ? " ▲" : column.sort_direction === "desc" ? " ▼" : "";
          sort.textContent = `${String(column.title)}${indicator}`;
          sort.disabled = Boolean(node.loading);
          sort.setAttribute("aria-label", `Sort by ${column.title}`);
          th.setAttribute("aria-sort", column.sort_direction === "asc" ? "ascending" :
            column.sort_direction === "desc" ? "descending" : "none");
          sort.onclick = () => sendEvent({ event_id: column.sort_event_id }).catch(error => console.error(error));
          th.append(sort);
        } else {
          th.textContent = String(column.title);
        }
        headers.push(th);
      }
      if (node.rows.some(row => row.actions.length)) {
        const th = element("th");
        th.scope = "col";
        th.textContent = "Actions";
        headers.push(th);
      }
      reconcileChildren(headerRow, headers);
      const headRows = [headerRow];
      if (node.filterable) {
        const filters = [];
        if (node.selectable) filters.push(element("th"));
        for (const column of node.columns) {
          const th = element("th");
          let input = th.querySelector("input");
          if (!input) input = element("input", "nova-table-filter");
          input.type = "search";
          input.setAttribute("aria-label", `Filter ${column.title}`);
          input.placeholder = `Filter ${String(column.title)}`;
          if (input.value !== String(column.filter_value || "")) input.value = String(column.filter_value || "");
          input.disabled = Boolean(node.loading);
          input.onchange = () => column.filter_event_id && sendEvent({ event_id: column.filter_event_id, value: input.value })
            .catch(error => console.error(error));
          th.append(input);
          filters.push(th);
        }
        if (node.rows.some(row => row.actions.length)) filters.push(element("th"));
        const filterRow = element("tr");
        reconcileChildren(filterRow, filters);
        headRows.push(filterRow);
      }
      reconcileChildren(thead, headRows);

      let tbody = table.querySelector("tbody");
      if (!tbody) tbody = element("tbody");
      const bodyRows = [];
      for (const row of node.rows) {
        const tr = element("tr");
        tr.dataset.rowKey = String(row.key);
        tr.classList.toggle("selected", Boolean(row.selected));
        if (row.row_click_event_id) {
          tr.tabIndex = 0;
          tr.setAttribute("aria-label", `Open row ${row.cells.map(String).join(", ")}`);
          const activate = () => sendEvent({ event_id: row.row_click_event_id }).catch(error => console.error(error));
          tr.onclick = activate;
          tr.onkeydown = event => {
            if (event.target === tr && (event.key === "Enter" || event.key === " ")) {
              event.preventDefault();
              activate();
            }
          };
        }
        const cells = [];
        if (node.selectable) {
          const td = element("td", "nova-table-select-cell");
          td.dataset.label = "Select";
          const checkbox = element("input");
          checkbox.type = "checkbox";
          checkbox.checked = Boolean(row.selected);
          checkbox.disabled = Boolean(node.loading);
          checkbox.setAttribute("aria-label", `Select row ${row.cells.map(String).join(", ")}`);
          checkbox.onclick = event => event.stopPropagation();
          checkbox.onchange = () => sendEvent({ event_id: row.select_event_id }).catch(error => console.error(error));
          td.append(checkbox);
          cells.push(td);
        }
        for (const [index, value] of row.cells.entries()) {
          const td = element("td");
          td.dataset.label = String(node.columns[index]?.title || node.columns[index]?.key || "");
          td.textContent = String(value);
          cells.push(td);
        }
        if (row.actions.length) {
          const td = element("td", "nova-table-actions");
          td.dataset.label = "Actions";
          for (const action of row.actions) {
            const button = element("button", "nova-button secondary");
            button.type = "button";
            button.textContent = String(action.label);
            button.disabled = Boolean(node.loading);
            button.onclick = event => {
              event.stopPropagation();
              sendEvent({ event_id: action.event_id }).catch(error => console.error(error));
            };
            td.append(button);
          }
          cells.push(td);
        }
        reconcileChildren(tr, cells);
        bodyRows.push(tr);
      }
      if (!bodyRows.length) {
        const empty = element("tr", "nova-table-empty-row");
        const message = element("td");
        message.colSpan = node.columns.length + (node.selectable ? 1 : 0) + (node.rows.some(row => row.actions.length) ? 1 : 0);
        message.textContent = node.loading ? "Loading…" : String(node.empty_message);
        message.setAttribute("role", node.loading ? "status" : "cell");
        empty.append(message);
        bodyRows.push(empty);
      }
      reconcileChildren(tbody, bodyRows);
      reconcileChildren(table, [thead, tbody]);
      reconcileChildren(tableWrap, [table]);
      children.push(tableWrap);

      let status = el.querySelector(".nova-table-status");
      if (!status) status = element("div", "nova-table-status");
      status.setAttribute("role", "status");
      status.textContent = `${node.total_rows} rows · ${node.selected_count} selected`;
      children.push(status);

      let pagination = el.querySelector(".nova-table-pagination");
      if (!pagination) pagination = element("div", "nova-table-pagination");
      const previous = element("button", "nova-button secondary");
      previous.type = "button";
      previous.textContent = "Previous";
      previous.disabled = Boolean(node.loading || !node.previous_event_id);
      if (node.previous_event_id) previous.onclick = () => sendEvent({ event_id: node.previous_event_id }).catch(error => console.error(error));
      const pageLabel = element("span");
      pageLabel.textContent = `Page ${node.page} of ${node.page_count}`;
      const next = element("button", "nova-button secondary");
      next.type = "button";
      next.textContent = "Next";
      next.disabled = Boolean(node.loading || !node.next_event_id);
      if (node.next_event_id) next.onclick = () => sendEvent({ event_id: node.next_event_id }).catch(error => console.error(error));
      reconcileChildren(pagination, [previous, pageLabel, next]);
      children.push(pagination);
      reconcileChildren(el, children);
      return el;
    }

    case "data_grid": {
      el = getElement(node, "section", "nova-data-grid", seen);
      el.setAttribute("aria-label", "Editable data grid");
      const toolbar = element("div", "nova-grid-toolbar");
      for (const [label, eventId] of [["Undo", node.undo_event_id], ["Redo", node.redo_event_id]]) {
        const button = element("button", "nova-button secondary");
        button.type = "button";
        button.textContent = label;
        button.disabled = !eventId;
        if (eventId) button.onclick = () => sendEvent({ event_id: eventId }).catch(error => console.error(error));
        toolbar.append(button);
      }

      let table = el.querySelector("table");
      if (!table) table = element("table", "nova-grid-table");
      table.setAttribute("role", "grid");
      table.setAttribute("aria-rowcount", String(node.rows.length + 1));
      table.setAttribute("aria-colcount", String(node.columns.length));
      let thead = table.querySelector("thead");
      if (!thead) thead = element("thead");
      let headerRow = thead.querySelector("tr");
      if (!headerRow) headerRow = element("tr");
      const headers = node.columns.map(column => {
        const th = element("th");
        th.scope = "col";
        th.textContent = String(column.title);
        return th;
      });
      reconcileChildren(headerRow, headers);
      reconcileChildren(thead, [headerRow]);

      let tbody = table.querySelector("tbody");
      if (!tbody) tbody = element("tbody");
      const rows = node.rows.map((row, rowIndex) => {
        let tr = [...tbody.rows].find(item => item.dataset.rowKey === String(row.key));
        if (!tr) tr = element("tr");
        tr.dataset.rowKey = String(row.key);
        const cells = row.cells.map((cell, columnIndex) => {
          let td = tr.cells[columnIndex];
          if (!td) td = element("td");
          td.setAttribute("role", "gridcell");
          let input = td.querySelector("input");
          if (!input) {
            input = element("input", "nova-grid-cell");
            input.readOnly = true;
          }
          input.type = "text";
          input.setAttribute("aria-label", `${node.columns[columnIndex].title}, row ${rowIndex + 1}`);
          input.readOnly = !cell.editable || input.readOnly;
          if (document.activeElement !== input) input.value = String(cell.value);
          input.dataset.rowIndex = String(rowIndex);
          input.dataset.columnIndex = String(columnIndex);
          input.dataset.gridCell = "true";
          input.oncopy = event => {
            if (!event.clipboardData) return;
            if (input.selectionStart !== input.selectionEnd) return;
            event.clipboardData.setData("text/plain", input.value);
            event.preventDefault();
          };
          input.onpaste = event => {
            if (!cell.paste_event_id || !event.clipboardData) return;
            event.preventDefault();
            sendEvent({
              event_id: cell.paste_event_id,
              value: event.clipboardData.getData("text/plain"),
            }).catch(error => console.error(error));
          };
          input.onkeydown = event => {
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
              const action = event.shiftKey ? node.redo_event_id : node.undo_event_id;
              if (action) {
                event.preventDefault();
                sendEvent({ event_id: action }).catch(error => console.error(error));
              }
              return;
            }
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y" && node.redo_event_id) {
              event.preventDefault();
              sendEvent({ event_id: node.redo_event_id }).catch(error => console.error(error));
              return;
            }
            if (input.readOnly && ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) {
              event.preventDefault();
              const rowOffset = event.key === "ArrowUp" ? -1 : event.key === "ArrowDown" ? 1 : 0;
              const columnOffset = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
              const nextRow = Math.max(0, Math.min(node.rows.length - 1, rowIndex + rowOffset));
              const nextColumn = Math.max(0, Math.min(node.columns.length - 1, columnIndex + columnOffset));
              el.querySelector(`input[data-row-index="${nextRow}"][data-column-index="${nextColumn}"]`)?.focus();
            } else if (input.readOnly && (event.key === "Enter" || event.key === "F2") && cell.editable) {
              event.preventDefault();
              input.readOnly = false;
              input.select();
            } else if (!input.readOnly && event.key === "Enter") {
              event.preventDefault();
              input.blur();
            } else if (!input.readOnly && event.key === "Escape") {
              event.preventDefault();
              input.value = String(cell.value);
              input.readOnly = true;
            }
          };
          const commit = () => {
            if (input.readOnly) return;
            const value = input.value;
            input.readOnly = true;
            if (value !== String(cell.value) && cell.event_id) {
              sendEvent({ event_id: cell.event_id, value }).catch(error => console.error(error));
            } else {
              input.value = String(cell.value);
            }
          };
          input.onblur = commit;
          input.ondblclick = () => {
            if (cell.editable) {
              input.readOnly = false;
              input.focus();
            }
          };
          reconcileChildren(td, [input]);
          return td;
        });
        reconcileChildren(tr, cells);
        return tr;
      });
      reconcileChildren(tbody, rows);
      reconcileChildren(table, [thead, tbody]);
      reconcileChildren(el, [toolbar, table]);
      return el;
    }

    case "virtual_list": {
      el = getElement(node, "div", "nova-virtual-list", seen);
      el.setAttribute("role", "list");
      el.setAttribute("aria-label", String(node.label || "List"));
      el.style.height = `${Number(node.height) || 320}px`;
      const top = element("div", "nova-virtual-list-spacer");
      top.setAttribute("aria-hidden", "true");
      top.style.height = `${Number(node.top_padding) || 0}px`;
      const items = (Array.isArray(node.items) ? node.items : []).map(item => {
        const row = element("div", "nova-virtual-list-item");
        row.dataset.itemKey = String(item.key);
        row.setAttribute("role", "listitem");
        row.setAttribute("aria-posinset", String(Number(item.index) + 1));
        row.setAttribute("aria-setsize", String(node.total));
        row.style.height = `${Number(node.item_height) || 40}px`;
        row.textContent = String(item.text ?? "");
        return row;
      });
      const bottom = element("div", "nova-virtual-list-spacer");
      bottom.setAttribute("aria-hidden", "true");
      bottom.style.height = `${Number(node.bottom_padding) || 0}px`;
      reconcileChildren(el, [top, ...items, bottom]);
      el.onscroll = () => {
        if (!node.scroll_event_id || el._virtualScrollPending) return;
        clearTimeout(el._virtualScrollTimer);
        el._virtualScrollTimer = setTimeout(() => {
          if (!el.isConnected) return;
          el._virtualScrollPending = true;
          sendEvent({ event_id: node.scroll_event_id, value: String(el.scrollTop) })
            .catch(error => console.error(error))
            .finally(() => { el._virtualScrollPending = false; });
        }, 80);
      };
      return el;
    }

    case "file_upload": {
      el = getElement(node, "div", "nova-file-upload", seen);
      let label = el.querySelector("label");
      if (!label) label = element("label", "nova-file-label");
      label.textContent = String(node.label || "Choose a file");
      let input = el.querySelector('input[type="file"]');
      if (!input) input = element("input", "nova-file-input");
      input.type = "file";
      input.accept = String(node.accept || "");
      input.disabled = Boolean(node.disabled || !node.event_id);
      input.setAttribute("aria-label", String(node.label || "Choose a file"));
      let progress = el.querySelector("progress");
      if (!progress) progress = element("progress", "nova-file-progress");
      progress.max = 100;
      progress.hidden = true;
      progress.setAttribute("aria-label", "File upload progress");
      let status = el.querySelector(".nova-file-status");
      if (!status) status = element("div", "nova-file-status");
      status.setAttribute("role", "status");
      const uploadFile = file => {
        if (!file || !node.event_id) return;
        if (file.size > node.max_size) {
          status.textContent = `File exceeds the ${node.max_size}-byte size limit.`;
          status.setAttribute("role", "alert");
          input.value = "";
          return;
        }
        status.setAttribute("role", "status");
        status.textContent = "Reading file…";
        progress.hidden = false;
        progress.value = 0;
        const reader = new FileReader();
        reader.onprogress = event => {
          if (event.lengthComputable) progress.value = Math.round(event.loaded / event.total * 100);
        };
        reader.onerror = () => {
          status.textContent = "Could not read the selected file.";
          status.setAttribute("role", "alert");
          progress.hidden = true;
          input.value = "";
        };
        reader.onload = async () => {
          try {
            const result = String(reader.result || "");
            const encoded = result.slice(result.indexOf(",") + 1);
            status.textContent = "Uploading file…";
            progress.value = 100;
            await sendEvent({
              event_id: node.event_id,
              value: { name: file.name, type: file.type, content: encoded },
            });
            status.textContent = "Upload complete.";
          } catch (error) {
            console.error(error);
            status.textContent = "Upload failed. Check the file and try again.";
            status.setAttribute("role", "alert");
          } finally {
            progress.hidden = true;
            input.value = "";
          }
        };
        reader.readAsDataURL(file);
      };
      input.onchange = () => uploadFile(input.files?.[0]);
      el.ondragover = event => {
        if (node.disabled || !node.event_id) return;
        event.preventDefault();
        el.classList.add("dragover");
      };
      el.ondragleave = event => {
        if (!el.contains(event.relatedTarget)) el.classList.remove("dragover");
      };
      el.ondrop = event => {
        if (node.disabled || !node.event_id) return;
        event.preventDefault();
        el.classList.remove("dragover");
        uploadFile(event.dataTransfer?.files?.[0]);
      };
      label.htmlFor = `${node.id}-file`;
      input.id = `${node.id}-file`;
      reconcileChildren(el, [label, input, progress, status]);
      return el;
    }

    case "command_palette": {
      el = getElement(node, "section", "nova-command-palette", seen);
      el.setAttribute("aria-label", "Command palette");
      let input = el.querySelector("input");
      if (!input) input = element("input", "nova-command-search");
      input.type = "search";
      input.placeholder = String(node.placeholder || "Search commands");
      input.setAttribute("role", "combobox");
      input.setAttribute("aria-label", "Search commands");
      input.setAttribute("aria-expanded", "true");
      input.setAttribute("aria-autocomplete", "list");
      input.setAttribute("aria-controls", `${node.id}-commands`);
      let list = el.querySelector('[role="listbox"]');
      if (!list) list = element("div", "nova-command-results");
      list.id = `${node.id}-commands`;
      list.setAttribute("role", "listbox");

      const renderMatches = () => {
        const query = input.value.trim().toLocaleLowerCase();
        const matches = (node.commands || []).filter(command =>
          [command.label, command.description || "", ...(command.keywords || [])]
            .some(value => String(value).toLocaleLowerCase().includes(query)));
        const buttons = matches.map(command => {
          const button = element("button", "nova-command-option");
          button.type = "button";
          button.setAttribute("role", "option");
          button.setAttribute("aria-label", `${command.label}${command.description ? `, ${command.description}` : ""}`);
          const title = element("span");
          title.textContent = String(command.label);
          const detail = element("span", "nova-command-detail");
          detail.textContent = String(command.description || command.shortcut || "");
          button.onclick = () => sendEvent({ event_id: command.event_id }).catch(error => console.error(error));
          button.onkeydown = event => {
            if (event.key === "Escape") {
              event.preventDefault();
              input.focus();
            } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault();
              const options = [...list.querySelectorAll('[role="option"]')];
              const index = options.indexOf(button);
              options[Math.max(0, Math.min(options.length - 1, index + (event.key === "ArrowDown" ? 1 : -1)))]?.focus();
            }
          };
          reconcileChildren(button, [title, detail]);
          return button;
        });
        if (!buttons.length) {
          const empty = element("div", "nova-command-empty");
          empty.textContent = String(node.empty_message || "No matching commands.");
          empty.setAttribute("role", "status");
          buttons.push(empty);
        }
        reconcileChildren(list, buttons);
      };
      input.oninput = renderMatches;
      input.onkeydown = event => {
        const options = [...list.querySelectorAll('[role="option"]')];
        if (event.key === "ArrowDown" && options.length) {
          event.preventDefault();
          options[0].focus();
        } else if (event.key === "Enter" && options.length) {
          event.preventDefault();
          options[0].click();
        } else if (event.key === "Escape") {
          input.value = "";
          renderMatches();
        }
      };
      renderMatches();
      reconcileChildren(el, [input, list]);
      return el;
    }

    case "tree_view": {
      el = getElement(node, "nav", "nova-tree-view", seen);
      el.setAttribute("aria-label", String(node.label || "Tree"));

      const renderNodes = (nodes, role = "group") => {
        const list = element("ul", "nova-tree-list");
        list.setAttribute("role", role);
        const items = nodes.map(item => {
          const li = element("li", "nova-tree-item");
          li.setAttribute("role", "treeitem");
          li.tabIndex = 0;
          li.dataset.treeNodeKey = String(item.key);
          if (item.children.length) li.setAttribute("aria-expanded", String(Boolean(item.expanded)));
          else li.removeAttribute("aria-expanded");
          li.onkeydown = event => {
            if (event.target !== li) return;
            const visible = [...el.querySelectorAll('[role="treeitem"]')];
            const position = visible.indexOf(li);
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault();
              const next = visible[Math.max(0, Math.min(visible.length - 1, position + (event.key === "ArrowDown" ? 1 : -1)))];
              if (next) {
                visible.forEach(treeItem => { treeItem.tabIndex = -1; });
                next.tabIndex = 0;
                next.focus();
              }
            } else if (event.key === "ArrowRight" && item.children.length) {
              event.preventDefault();
              if (!item.expanded && item.toggle_event_id) {
                sendEvent({ event_id: item.toggle_event_id }).catch(error => console.error(error));
              } else {
                const child = li.querySelector('[role="treeitem"]');
                if (child) {
                  li.tabIndex = -1;
                  child.tabIndex = 0;
                  child.focus();
                }
              }
            } else if (event.key === "ArrowLeft" && item.children.length && item.expanded) {
              event.preventDefault();
              if (item.toggle_event_id) sendEvent({ event_id: item.toggle_event_id }).catch(error => console.error(error));
            } else if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              if (item.select_event_id) sendEvent({ event_id: item.select_event_id }).catch(error => console.error(error));
            }
          };
          const label = element("span", "nova-tree-label");
          label.textContent = String(item.label);
          const children = [];
          if (item.children.length) {
            const toggle = element("button", "nova-tree-toggle");
            toggle.type = "button";
            toggle.tabIndex = -1;
            toggle.textContent = item.expanded ? "−" : "+";
            toggle.setAttribute("aria-label", `${item.expanded ? "Collapse" : "Expand"} ${item.label}`);
            toggle.onclick = () => item.toggle_event_id &&
              sendEvent({ event_id: item.toggle_event_id }).catch(error => console.error(error));
            children.push(toggle);
          } else {
            const spacer = element("span", "nova-tree-toggle-spacer");
            spacer.setAttribute("aria-hidden", "true");
            children.push(spacer);
          }
          children.push(label);
          reconcileChildren(li, children);
          if (item.children.length && item.expanded) li.append(renderNodes(item.children));
          return li;
        });
        reconcileChildren(list, items);
        return list;
      };
      const activeKey = el.querySelector('[role="treeitem"]:focus')?.dataset.treeNodeKey;
      const tree = renderNodes(node.nodes || [], "tree");
      tree.setAttribute("aria-label", String(node.label || "Tree"));
      [...tree.querySelectorAll('[role="treeitem"]')].forEach((item, index) => {
        item.tabIndex = index === 0 ? 0 : -1;
      });
      reconcileChildren(el, [tree]);
      if (activeKey) {
        [...el.querySelectorAll('[role="treeitem"]')]
          .find(item => item.dataset.treeNodeKey === activeKey)?.focus();
      }
      return el;
    }

    case "toolbar":
    case "status_bar": {
      const toolbar = node.type === "toolbar";
      el = getElement(node, toolbar ? "div" : "footer",
        toolbar ? `nova-toolbar ${node.orientation || "horizontal"}` : "nova-status-bar", seen);
      el.setAttribute("role", toolbar ? "toolbar" : "status");
      el.setAttribute("aria-label", String(node.label || (toolbar ? "Toolbar" : "Status")));
      if (toolbar) el.setAttribute("aria-orientation", node.orientation || "horizontal");
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;
    }

    case "form": {
      el = getElement(node, "form", "nova-form", seen);
      el._novaSubmitEvent = node.submit_event_id;
      el._novaResetEvent = node.reset_event_id;
      el.disabled = Boolean(node.disabled || node.loading);
      el.setAttribute("aria-busy", node.loading ? "true" : "false");
      el.onsubmit = async event => {
        event.preventDefault();
        const inputs = [...el.querySelectorAll("input[name]")];
        await Promise.all(inputs.map(input => input._novaPendingEvent).filter(Boolean));
        if (!el._novaSubmitEvent || el.disabled) return;
        const values = {};
        for (const input of inputs) {
          if (!input.disabled) values[input.name] = input.value;
        }
        try {
          submit.disabled = true;
          await sendEvent({ event_id: el._novaSubmitEvent, value: values });
        } catch (error) {
          submit.disabled = Boolean(node.disabled || node.loading);
          const formStatus = el.querySelector(".nova-form-status");
          if (formStatus) {
            formStatus.textContent = error.message || "Form submission failed.";
            formStatus.setAttribute("role", "alert");
          }
        }
      };
      const children = (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen));
      let errorSummary = el.querySelector(".nova-form-error-summary");
      const errors = Array.isArray(node.error_summary) ? node.error_summary : [];
      if (errors.length) {
        if (!errorSummary) errorSummary = element("div", "nova-form-error-summary");
        errorSummary.setAttribute("role", "alert");
        errorSummary.setAttribute("aria-labelledby", `${node.id}-error-summary-title`);
        const heading = element("h2", "nova-form-error-summary-title");
        heading.id = `${node.id}-error-summary-title`;
        heading.textContent = "Please correct these fields:";
        const list = element("ul");
        for (const error of errors) {
          const item = element("li");
          item.textContent = `${String(error.label || error.name)}: ${String(error.message || "")}`;
          list.append(item);
        }
        reconcileChildren(errorSummary, [heading, list]);
      } else if (errorSummary) {
        errorSummary.remove();
        errorSummary = null;
      }
      let formStatus = el.querySelector(".nova-form-status");
      if (!formStatus) formStatus = element("div", "nova-form-status");
      formStatus.setAttribute("role", "status");
      formStatus.textContent = String(node.status || "");
      let loadingStatus = el.querySelector(".nova-form-loading");
      if (node.loading) {
        if (!loadingStatus) loadingStatus = element("div", "nova-form-loading");
        loadingStatus.setAttribute("role", "status");
        loadingStatus.textContent = "Submitting…";
      } else if (loadingStatus) {
        loadingStatus.remove();
        loadingStatus = null;
      }
      let actions = el.querySelector(".nova-form-actions");
      if (!actions) actions = element("div", "nova-form-actions");
      let submit = actions.querySelector("button[type=submit]");
      if (!submit) submit = element("button", "nova-button primary");
      submit.type = "submit";
      submit.textContent = String(node.submit_label || "Submit");
      submit.disabled = Boolean(node.disabled || node.loading);
      let reset = actions.querySelector("button[type=button]");
      if (node.reset_label) {
        if (!reset) reset = element("button", "nova-button secondary");
        reset.type = "button";
        reset.textContent = String(node.reset_label);
        reset.disabled = Boolean(node.disabled || node.loading);
        reset.onclick = async () => {
          if (!el._novaResetEvent) return;
          try {
            await sendEvent({ event_id: el._novaResetEvent });
          } catch (error) {
            console.error(error);
          }
        };
      } else if (reset) {
        reset.remove();
        reset = null;
      }
      reconcileChildren(actions, [submit, ...(reset ? [reset] : [])]);
      reconcileChildren(el, [...(errorSummary ? [errorSummary] : []), ...children,
        ...(loadingStatus ? [loadingStatus] : []), formStatus, actions]);
      return el;
    }

    case "router":
      el = getElement(node, "div", "nova-router", seen);
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "alert":
      el = getElement(node, "div", `nova-alert ${node.kind || "info"}`, seen);
      el.setAttribute("role", node.kind === "error" || node.kind === "warning" ? "alert" : "status");
      el.textContent = String(node.message ?? "");
      return el;

    case "toast": {
      el = getElement(node, "div", `nova-toast ${node.kind || "info"}`, seen);
      el.setAttribute("role", node.kind === "error" || node.kind === "warning" ? "alert" : "status");
      el.setAttribute("aria-live", node.kind === "error" || node.kind === "warning" ? "assertive" : "polite");
      const message = element("span", "nova-toast-message");
      message.textContent = String(node.message || "");
      const close = element("button", "nova-toast-dismiss");
      close.type = "button";
      close.textContent = "Dismiss";
      close.setAttribute("aria-label", "Dismiss notification");
      close.onclick = () => {
        const timer = toastTimers.get(String(node.id));
        if (timer) {
          clearTimeout(timer.handle);
          toastTimers.delete(String(node.id));
        }
        if (node.dismiss_event_id) {
          sendEvent({ event_id: node.dismiss_event_id }).catch(error => console.error(error));
        }
      };
      reconcileChildren(el, [message, close]);
      if (!node.visible || node.dismissed || !node.duration || !node.dismiss_event_id) {
        const timer = toastTimers.get(String(node.id));
        if (timer) clearTimeout(timer.handle);
        toastTimers.delete(String(node.id));
      } else {
        let timer = toastTimers.get(String(node.id));
        if (!timer) {
          timer = { handle: null, eventId: node.dismiss_event_id };
          timer.handle = setTimeout(() => {
            const current = toastTimers.get(String(node.id));
            toastTimers.delete(String(node.id));
            if (current?.eventId) sendEvent({ event_id: current.eventId }).catch(error => console.error(error));
          }, node.duration);
          toastTimers.set(String(node.id), timer);
        } else {
          timer.eventId = node.dismiss_event_id;
        }
      }
      return el;
    }

    case "toast_host":
      el = getElement(node, "div", "nova-toast-host", seen);
      el.setAttribute("role", "region");
      el.setAttribute("aria-label", String(node.label || "Notifications"));
      el.setAttribute("aria-live", "polite");
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "spinner":
      el = getElement(node, "div", "nova-spinner", seen);
      el.setAttribute("role", "status");
      let spinner = el.querySelector(".nova-spinner-mark");
      if (!spinner) spinner = element("span", "nova-spinner-mark");
      spinner.setAttribute("aria-hidden", "true");
      let spinnerLabel = el.querySelector(".nova-spinner-label");
      if (!spinnerLabel) spinnerLabel = element("span", "nova-spinner-label");
      spinnerLabel.textContent = String(node.label || "Loading");
      reconcileChildren(el, [spinner, spinnerLabel]);
      return el;

    case "dialog": {
      el = getElement(node, "dialog", "nova-dialog", seen);
      el.setAttribute("aria-labelledby", `${node.id}-title`);
      let title = el.querySelector(".nova-dialog-title");
      if (!title) title = element("h2", "nova-dialog-title");
      title.id = `${node.id}-title`;
      title.textContent = String(node.title);
      let content = el.querySelector(".nova-dialog-content");
      if (!content) content = element("div", "nova-dialog-content");
      reconcileChildren(content, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      let status = el.querySelector(".nova-dialog-status");
      if (!status) status = element("div", "nova-dialog-status");
      status.setAttribute("role", "alert");
      status.textContent = String(node.status || "");
      let actions = el.querySelector(".nova-dialog-actions");
      if (!actions) actions = element("div", "nova-dialog-actions");
      let cancel = actions.querySelector("button[data-action=cancel]");
      if (!cancel) cancel = element("button", "nova-button secondary");
      cancel.type = "button";
      cancel.dataset.action = "cancel";
      cancel.textContent = String(node.cancel_label);
      cancel.onclick = async () => {
        try {
          await sendEvent({ event_id: node.cancel_event_id });
        } catch (error) {
          console.error(error);
        }
      };
      let confirm = actions.querySelector("button[data-action=confirm]");
      if (!confirm) confirm = element("button", "nova-button primary");
      confirm.type = "button";
      confirm.dataset.action = "confirm";
      confirm.textContent = String(node.confirm_label);
      confirm.onclick = async () => {
        try {
          await sendEvent({ event_id: node.confirm_event_id });
        } catch (error) {
          console.error(error);
        }
      };
      reconcileChildren(actions, [cancel, confirm]);
      reconcileChildren(el, [title, content, status, actions]);
      el.oncancel = event => {
        event.preventDefault();
        sendEvent({ event_id: node.cancel_event_id }).catch(error => console.error(error));
      };
      if (node.open && !el.open) {
        requestAnimationFrame(() => {
          if (el.isConnected && node.open && !el.open) el.showModal();
        });
      } else if (!node.open && el.open) {
        el.close();
      }
      return el;
    }

    case "tabs": {
      el = getElement(node, "div", "nova-tabs", seen);
      let tablist = el.querySelector('[role="tablist"]');
      if (!tablist) tablist = element("div", "nova-tab-list");
      tablist.setAttribute("role", "tablist");
      const buttons = [...tablist.querySelectorAll('[role="tab"]')];
      const tabButtons = node.tabs.map((tab, index) => {
        let button = buttons[index];
        if (!button) button = element("button", "nova-tab");
        button.type = "button";
        button.id = `${node.id}-tab-${index}`;
        button.setAttribute("role", "tab");
        button.setAttribute("aria-selected", tab.active ? "true" : "false");
        button.setAttribute("aria-controls", `${node.id}-panel`);
        button.tabIndex = tab.active ? 0 : -1;
        button.classList.toggle("active", Boolean(tab.active));
        button.textContent = String(tab.label);
        button.onclick = async () => {
          try {
            await sendEvent({ event_id: tab.event_id });
          } catch (error) {
            console.error(error);
          }
        };
        return button;
      });
      reconcileChildren(tablist, tabButtons);
      let panel = el.querySelector('[role="tabpanel"]');
      if (!panel) panel = element("div", "nova-tab-panel");
      panel.id = `${node.id}-panel`;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", `${node.id}-tab-${Math.max(0, node.tabs.findIndex(tab => tab.active))}`);
      reconcileChildren(panel, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      reconcileChildren(el, [tablist, panel]);
      return el;
    }

    case "center":
      el = getElement(node, "div", "nova-center", seen);
      applyDimensions(el, node);
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "container":
      el = getElement(node, "div", "nova-container", seen);
      applyDimensions(el, node);
      el.style.padding = `${Number(node.padding) || 0}px`;
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "grid":
      el = getElement(node, "div", `nova-grid${Number.isInteger(node.column_count) ? ` columns-${node.column_count}${node.column_count > 2 ? " columns-many" : ""}` : ""}`, seen);
      applyDimensions(el, node);
      el.style.setProperty("--nova-grid-tablet-columns", String(Number(node.tablet_columns) || 2));
      el.style.setProperty("--nova-grid-mobile-columns", String(Number(node.mobile_columns) || 1));
      el.classList.toggle("has-responsive-columns", node.tablet_columns != null || node.mobile_columns != null);
      if (Number.isInteger(node.column_count)) {
        el.style.gridTemplateColumns = "";
      } else {
        el.style.gridTemplateColumns = node.columns || "repeat(2, minmax(0, 1fr))";
      }
      el.style.gap = `${Number(node.spacing) || 0}px`;
      el.style.padding = `${Number(node.padding) || 0}px`;
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "split_pane": {
      el = getElement(node, "div", `nova-split-pane orientation-${node.orientation}`, seen);
      const horizontal = node.orientation === "horizontal";
      const first = renderNode(node.children?.[0], seen);
      const second = renderNode(node.children?.[1], seen);
      let separator = el.querySelector(":scope > .nova-split-separator");
      if (!separator) separator = element("div", "nova-split-separator");
      separator.setAttribute("role", "separator");
      separator.setAttribute("tabindex", "0");
      separator.setAttribute("aria-orientation", horizontal ? "vertical" : "horizontal");
      const minimum = Number(node.min_percent) || 15;
      const maximum = Number(node.max_percent) || 85;
      const initial = Number(node.initial_percent) || 50;
      const applyPercent = value => {
        const percent = Math.max(minimum, Math.min(maximum, value));
        el.style.setProperty("--nova-split-first", `${percent}%`);
        separator.setAttribute("aria-valuemin", String(minimum));
        separator.setAttribute("aria-valuemax", String(maximum));
        separator.setAttribute("aria-valuenow", String(Math.round(percent)));
        return percent;
      };
      let ratio = Number(el.dataset.splitPercent);
      if (!Number.isFinite(ratio)) ratio = initial;
      ratio = applyPercent(ratio);
      separator.onkeydown = event => {
        if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
        event.preventDefault();
        const delta = event.key === "ArrowLeft" || event.key === "ArrowUp" ? -2 : 2;
        ratio = applyPercent(ratio + delta);
        el.dataset.splitPercent = String(ratio);
      };
      separator.onpointerdown = event => {
        if (event.button === 0) separator.setPointerCapture(event.pointerId);
      };
      separator.onpointermove = event => {
        if (!separator.hasPointerCapture(event.pointerId)) return;
        const bounds = el.getBoundingClientRect();
        const position = horizontal ? event.clientX - bounds.left : event.clientY - bounds.top;
        const extent = horizontal ? bounds.width : bounds.height;
        if (extent > 0) {
          ratio = applyPercent(position / extent * 100);
          el.dataset.splitPercent = String(ratio);
        }
      };
      separator.onpointerup = event => {
        if (separator.hasPointerCapture(event.pointerId)) separator.releasePointerCapture(event.pointerId);
      };
      reconcileChildren(el, [first, separator, second]);
      return el;
    }

    case "scroll_view":
      el = getElement(node, "div", `nova-scroll-view direction-${node.direction || "vertical"}`, seen);
      applyDimensions(el, node);
      el.style.padding = `${Number(node.padding) || 0}px`;
      el.style.overflowX = node.direction === "horizontal" || node.direction === "both" ? "auto" : "hidden";
      el.style.overflowY = node.direction === "vertical" || node.direction === "both" ? "auto" : "hidden";
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "stack":
      el = getElement(node, "div", "nova-stack", seen);
      applyDimensions(el, node);
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "wrap":
      el = getElement(node, "div", "nova-wrap", seen);
      applyDimensions(el, node);
      el.style.columnGap = `${Number(node.spacing) || 0}px`;
      el.style.rowGap = `${Number(node.run_spacing) || 0}px`;
      el.style.alignItems = node.align || "start";
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "row":
    case "column":
      el = getElement(node, "div", `nova-layout ${node.type}`, seen);
      applyDimensions(el, node);
      el.style.gap = `${Number(node.spacing) || 0}px`;
      el.style.padding = `${Number(node.padding) || 0}px`;
      el.style.alignItems = node.align || "";
      el.style.justifyContent = ({ start: "flex-start", end: "flex-end", between: "space-between",
        around: "space-around", evenly: "space-evenly" })[node.justify] || node.justify || "";
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "card":
      el = getElement(node, "section", `nova-card${node.variant && node.variant !== "auto" ? ` ${node.variant}` : ""}`, seen);
      applyDimensions(el, node);
      el.style.padding = `${Number(node.padding) || 0}px`;
      el.style.borderRadius = node.radius == null ? "var(--radius)" : `${Number(node.radius)}px`;
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

    case "spacer":
      el = getElement(node, "div", "nova-spacer", seen);
      applyDimensions(el, node);
      el.style.minHeight = node.height == null ? `${Number(node.size) || 0}px` : "";
      return el;

    default:
      return element("div", "error");
  }
}

function renderTree(tree) {
  document.title = tree.title || "NovaUI";
  syncApplicationStylesheets(tree.stylesheets);
  const theme = typeof tree.theme === "string" ? { mode: tree.theme } : (tree.theme || {});
  let themeMode = theme.mode || "light";
  if (theme.persist) {
    const storageKey = `novaui-theme:${window.location.pathname}:${tree.title || "NovaUI"}`;
    try {
      if (window._novaThemeStorageKey !== storageKey) {
        window._novaThemeStorageKey = storageKey;
        window._novaLastServerThemeMode = themeMode;
        const saved = window.localStorage.getItem(storageKey);
        if (["light", "dark", "system"].includes(saved)) themeMode = saved;
        else window.localStorage.setItem(storageKey, themeMode);
      } else {
        if (window._novaLastServerThemeMode !== themeMode) window.localStorage.setItem(storageKey, themeMode);
        window._novaLastServerThemeMode = themeMode;
        const saved = window.localStorage.getItem(storageKey);
        if (["light", "dark", "system"].includes(saved)) themeMode = saved;
      }
    } catch (error) {
      showDiagnostic("Theme preference could not be persisted in this browser.");
    }
  }
  if (themeMode === "system" && typeof window.matchMedia === "function") {
    if (!systemThemeQuery) {
      systemThemeQuery = window.matchMedia("(prefers-color-scheme: dark)");
      systemThemeListener = applySystemTheme;
      if (systemThemeQuery.addEventListener) systemThemeQuery.addEventListener("change", systemThemeListener);
      else if (systemThemeQuery.addListener) systemThemeQuery.addListener(systemThemeListener);
    }
    applySystemTheme();
  } else {
    if (systemThemeQuery && systemThemeListener) {
      if (systemThemeQuery.removeEventListener) systemThemeQuery.removeEventListener("change", systemThemeListener);
      else if (systemThemeQuery.removeListener) systemThemeQuery.removeListener(systemThemeListener);
    }
    systemThemeQuery = null;
    systemThemeListener = null;
    document.documentElement.dataset.theme = themeMode === "dark" ? "dark" : "light";
  }
  document.documentElement.dataset.appearance = theme.appearance === "glass" ? "glass" : "solid";
  document.documentElement.dataset.contrast = theme.contrast === "high" ? "high" : "normal";
  const variables = theme.variables && typeof theme.variables === "object" ? theme.variables : {};
  const oldThemeVariables = document.documentElement._novaThemeVariables || [];
  for (const name of oldThemeVariables) {
    if (!Object.hasOwn(variables, name)) document.documentElement.style.removeProperty(name);
  }
  for (const [name, value] of Object.entries(variables)) {
    if (["--primary", "--radius", "--font-family", "--bg", "--surface", "--surface-raised", "--text", "--muted", "--border", "--primary-hover", "--on-primary", "--primary-soft", "--success", "--warning", "--danger", "--info", "--glass-blur", "--glass-opacity"].includes(name)) {
      document.documentElement.style.setProperty(name, String(value));
    }
  }
  document.documentElement._novaThemeVariables = Object.keys(variables);
  const previewError = document.getElementById("novaui-preview-error");
  if (previewError) {
    const error = tree.preview_error;
    previewError.hidden = !error;
    previewError.textContent = error
      ? `${error.type}: ${error.message}${error.line ? ` (${error.file}:${error.line})` : ""}`
      : "";
  }
  setPreviewPolling(tree.preview_poll_ms);
  installShortcuts(tree.shortcuts);
  if (tree.root && tree.root.type === "router" && typeof tree.root.path === "string") {
    const current = `${window.location.pathname}${window.location.search}`;
    if (current !== tree.root.path) window.history.pushState({ novaui: true }, "", tree.root.path);
  }
  const seen = new Set();
  reconcileChildren(appRoot, [renderNode(tree.root, seen)]);
  let rootNode = tree.root;
  while (rootNode && ["router", "fragment"].includes(rootNode.type) && rootNode.children?.length === 1) {
    rootNode = rootNode.children[0];
  }
  const rootClasses = rootNode?.class_name?.split(/\s+/) || [];
  const isShellRoot = rootClasses.includes("nova-app-shell") || rootClasses.includes("nova-scaffold");
  appRoot.classList.toggle("nova-app-root-shell", Boolean(isShellRoot));
  appRoot.classList.toggle("nova-scaffold-root", rootClasses.includes("nova-scaffold"));
  for (const id of nodeElements.keys()) {
    if (!seen.has(id)) {
      nodeElements.get(id)?._novaChartObserver?.disconnect();
      nodeElements.delete(id);
      const timer = toastTimers.get(id);
      if (timer) clearTimeout(timer.handle);
      toastTimers.delete(id);
    }
  }
}

function syncApplicationStylesheets(stylesheets) {
  const paths = Array.isArray(stylesheets)
    ? stylesheets.filter(path => typeof path === "string").slice(0, 8)
    : [];
  const existing = [...document.querySelectorAll("link[data-nova-app-stylesheet]")];
  paths.forEach((path, index) => {
    let link = document.getElementById(`nova-app-stylesheet-${index}`);
    if (!link) {
      link = document.createElement("link");
      link.rel = "stylesheet";
      link.dataset.novaAppStylesheet = "true";
      link.id = `nova-app-stylesheet-${index}`;
      document.head.append(link);
    }
    const href = `/assets/${path.split("/").map(encodeURIComponent).join("/")}`;
    if (link.getAttribute("href") !== href) link.href = href;
  });
  existing.forEach(link => {
    const index = Number(link.id.slice("nova-app-stylesheet-".length));
    if (!Number.isInteger(index) || index >= paths.length) link.remove();
  });
}

function setPreviewPolling(interval) {
  const next = Number.isInteger(interval) && interval >= 250 && interval <= 5000 ? interval : 0;
  if (next === previewPollInterval) return;
  previewPollInterval = next;
  if (previewPollTimer !== null) clearInterval(previewPollTimer);
  previewPollTimer = next ? setInterval(() => loadTree(true), next) : null;
}

async function loadTree(quiet = false) {
  if (treeRequestPending || activeEvents) return;
  treeRequestPending = true;
  try {
    const route = `${window.location.pathname}${window.location.search}`;
    const response = await fetch(`/api/tree?path=${encodeURIComponent(route)}`, {
      cache: "no-store",
      headers: requestHeaders({ "X-NovaUI-Request": "tree" })
    });
    if (!response.ok) throw new Error(`Could not load the NovaUI component tree (${response.status})`);
    renderTree(await response.json());
  } catch (error) {
    if (!quiet) appRoot.textContent = "NovaUI could not load. Check the Python terminal for details.";
    console.error(error);
  } finally {
    treeRequestPending = false;
  }
}

window.addEventListener("popstate", () => loadTree());
loadTree();
