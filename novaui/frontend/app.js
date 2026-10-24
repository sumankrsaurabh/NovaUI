"use strict";

const appRoot = document.getElementById("app");
const nodeElements = new Map();
let activeShortcuts = [];
let shortcutsListenerInstalled = false;

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

function applyDimensions(el, node) {
  el.style.width = node.width == null ? "" : `${node.width}px`;
  el.style.height = node.height == null ? "" : `${node.height}px`;
}

async function sendEvent(payload) {
  const response = await fetch("/api/event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Action failed");
  renderTree(data);
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
      if (el.textContent !== String(node.label ?? "Button")) el.textContent = String(node.label ?? "Button");
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

    case "data_table": {
      el = getElement(node, "section", "nova-data-table", seen);
      el.setAttribute("role", "region");
      el.setAttribute("aria-label", "Data table");
      const children = [];
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
        children.push(search);
      }

      let tableWrap = el.querySelector(".nova-table-scroll");
      if (!tableWrap) tableWrap = element("div", "nova-table-scroll");
      let table = tableWrap.querySelector("table");
      if (!table) table = element("table", "nova-table");
      table.setAttribute("aria-busy", node.loading ? "true" : "false");
      let thead = table.querySelector("thead");
      if (!thead) thead = element("thead");
      let headerRow = thead.querySelector("tr");
      if (!headerRow) headerRow = element("tr");
      const headers = [];
      if (node.selectable) {
        const th = element("th");
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
          input.placeholder = "Filter";
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
          const td = element("td");
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
        for (const value of row.cells) {
          const td = element("td");
          td.textContent = String(value);
          cells.push(td);
        }
        if (row.actions.length) {
          const td = element("td", "nova-table-actions");
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
        const empty = element("tr");
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
          await sendEvent({ event_id: el._novaSubmitEvent, value: values });
        } catch (error) {
          const formStatus = el.querySelector(".nova-form-status");
          if (formStatus) {
            formStatus.textContent = error.message || "Form submission failed.";
            formStatus.setAttribute("role", "alert");
          }
        }
      };
      const children = (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen));
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
      reconcileChildren(el, [...children, ...(loadingStatus ? [loadingStatus] : []), formStatus, actions]);
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
      if (Number.isInteger(node.column_count)) {
        el.style.gridTemplateColumns = "";
      } else {
        el.style.gridTemplateColumns = node.columns || "repeat(2, minmax(0, 1fr))";
      }
      el.style.gap = `${Number(node.spacing) || 0}px`;
      el.style.padding = `${Number(node.padding) || 0}px`;
      reconcileChildren(el, (Array.isArray(node.children) ? node.children : []).map(child => renderNode(child, seen)));
      return el;

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
      el = getElement(node, "section", "nova-card", seen);
      applyDimensions(el, node);
      el.style.padding = `${Number(node.padding) || 0}px`;
      el.style.borderRadius = `${Number(node.radius) || 12}px`;
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
  const theme = typeof tree.theme === "string" ? { mode: tree.theme } : (tree.theme || {});
  document.documentElement.dataset.theme = theme.mode === "dark" ? "dark" : "light";
  const variables = theme.variables && typeof theme.variables === "object" ? theme.variables : {};
  const oldThemeVariables = document.documentElement._novaThemeVariables || [];
  for (const name of oldThemeVariables) {
    if (!Object.hasOwn(variables, name)) document.documentElement.style.removeProperty(name);
  }
  for (const [name, value] of Object.entries(variables)) {
    if (["--primary", "--radius", "--font-family", "--bg", "--surface", "--text", "--muted", "--border", "--primary-hover"].includes(name)) {
      document.documentElement.style.setProperty(name, String(value));
    }
  }
  document.documentElement._novaThemeVariables = Object.keys(variables);
  installShortcuts(tree.shortcuts);
  if (tree.root && tree.root.type === "router" && typeof tree.root.path === "string") {
    const current = `${window.location.pathname}${window.location.search}`;
    if (current !== tree.root.path) window.history.pushState({ novaui: true }, "", tree.root.path);
  }
  const seen = new Set();
  reconcileChildren(appRoot, [renderNode(tree.root, seen)]);
  for (const id of nodeElements.keys()) {
    if (!seen.has(id)) nodeElements.delete(id);
  }
}

async function loadTree() {
  try {
    const route = `${window.location.pathname}${window.location.search}`;
    const response = await fetch(`/api/tree?path=${encodeURIComponent(route)}`, {
      cache: "no-store",
      headers: { "X-NovaUI-Request": "tree" }
    });
    if (!response.ok) throw new Error("Could not load the NovaUI component tree");
    renderTree(await response.json());
  } catch (error) {
    appRoot.textContent = "NovaUI could not load. Check the Python terminal for details.";
    console.error(error);
  }
}

window.addEventListener("popstate", loadTree);
loadTree();
