/* SPDX-License-Identifier: MIT · Copyright (c) 2026 MS ROBOTIKA */
"use strict";
const $ = id => document.getElementById(id);
const token = new URLSearchParams(location.hash.slice(1)).get("token") || sessionStorage.getItem("ab-session") || "";
if (token) sessionStorage.setItem("ab-session", token);
history.replaceState(null, "", location.pathname);
let state = null, events = [], polling = false, pollTimer = null, busy = false, refreshing = false, closed = false;
let lastFrameKey = "", lastProfileKey = "";
let firstReadComplete = false;
const numericFields = ["port", "unit", "function", "address", "count", "timeout_ms"];

function notice(message, error = false) {
  $("notice").textContent = message;
  $("notice").classList.toggle("error", error);
}
async function api(path, body) {
  const response = await fetch(path, {method: body === undefined ? "GET" : "POST", cache: "no-store",
    headers: {"Authorization": `Bearer ${token}`, "Content-Type": "application/json"},
    body: body === undefined ? undefined : JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Error HTTP ${response.status}`);
  return result;
}
function currentProfile() {
  const profile = {name: $("profile-name").value.trim(), host: $("host").value.trim()};
  numericFields.forEach(key => {profile[key] = Number($(key).value);});
  return profile;
}
function stopPolling() {
  polling = false;
  clearTimeout(pollTimer);
  $("poll").textContent = "Repetir lectura";
}
function fillProfile(profile) {
  stopPolling();
  $("allow-lan").checked = false;
  $("host").value = profile.host;
  $("profile-name").value = profile.name;
  numericFields.forEach(key => {$(key).value = profile[key];});
  updateCountLimit();
}
function updateCountLimit() {
  const max = Number($("function").value) < 3 ? 2000 : 125;
  $("count").max = max;
  if (Number($("count").value) > max) $("count").value = max;
}
function element(tag, content, className) {
  const node = document.createElement(tag);
  if (content !== undefined) node.textContent = content;
  if (className) node.className = className;
  return node;
}
function cell(row, content, className) {row.append(element("td", content, className));}
function updateQuickstart() {
  const simulatorOn = state?.simulator_port != null;
  const stage = firstReadComplete ? 3 : (simulatorOn ? 2 : 1);
  $("primera-prueba").dataset.quickStage = String(stage);
  document.querySelectorAll("[data-quick-step]").forEach(el => {
    const index = Number(el.dataset.quickStep);
    el.classList.toggle("done", index < stage);
    el.classList.toggle("current", index === stage);
  });
  $("quick-results-link").hidden = !firstReadComplete;
  $("quick-feedback").textContent = firstReadComplete
    ? "Lectura comprobada: los registros ya están en «Datos de la última lectura». Consulta las tramas TX/RX en el monitor y prueba otros valores en el laboratorio."
    : simulatorOn
      ? "El simulador está activo. Pulsa «Probar con datos simulados» para leer ocho registros FC03 por TCP local."
      : "Pulsa el botón para ejecutar una lectura sobre 127.0.0.1. No se envían escrituras Modbus.";
  $("quick-demo").disabled = closed || busy;
}
function showValues(result) {
  const fragment = document.createDocumentFragment();
  const prefixes = {1: 0, 2: 10000, 3: 40000, 4: 30000};
  result.values.forEach((value, i) => {
    const address = result.address + i, row = element("tr");
    cell(row, address, "number");
    const reference = address < 9999 ? String(prefixes[result.function] + address + 1).padStart(5, "0") : "—";
    cell(row, reference, "number");
    cell(row, value, "number value");
    cell(row, "0x" + value.toString(16).toUpperCase().padStart(4, "0"), "number");
    const status = element("td");
    status.append(element("span", result.function < 3 ? (value ? "ON" : "OFF") : "Leído", "state-tag"));
    row.append(status); fragment.append(row);
  });
  $("values").replaceChildren(fragment);
  $("read-meta").textContent = `${result.values.length} valores · ${result.elapsed_ms} ms · TID ${result.transaction}`;
  $("result-context").textContent = `${result.host}:${result.port} · unidad ${result.unit} · FC${String(result.function).padStart(2, "0")} · ${new Date().toLocaleTimeString("es-ES")} · última lectura correcta`;
  firstReadComplete = true;
  updateQuickstart();
}
async function readOnce() {
  if (busy || closed) return;
  if (!$("read-form").reportValidity()) {stopPolling(); return;}
  busy = true;
  $("read").disabled = true;
  try {
    const result = await api("/api/read", {profile: currentProfile(), allow_lan: $("allow-lan").checked});
    showValues(result);
    notice(`Lectura completada: ${result.values.length} valores. No se ha enviado ninguna escritura.`);
  } catch (error) {
    stopPolling();
    $("read-meta").textContent = "Lectura fallida · los valores anteriores no se han actualizado";
    notice(error.message, true);
  } finally {
    busy = false;
    updateQuickstart();
    $("read").disabled = false;
    await refresh();
    if (polling) pollTimer = setTimeout(readOnce, Number($("interval").value));
  }
}
function renderFrames() {
  const filter = $("source-filter").value;
  const visible = events.filter(event => !filter || event.source === filter);
  const key = `${filter}:${events.length}:${events.at(-1)?.id || 0}`;
  if (key === lastFrameKey) return;
  lastFrameKey = key;
  $("frame-count").textContent = events.length;
  const fragment = document.createDocumentFragment();
  [...visible].reverse().forEach(event => {
    const row = element("tr");
    cell(row, event.time.slice(11, 23), "number"); cell(row, event.source);
    cell(row, event.direction, `direction ${event.direction === "ERROR" ? "error" : ""}`);
    const data = element("td", event.hex || event.detail, "frame-data");
    if (event.hex && event.detail) data.append(element("span", event.detail, "frame-detail"));
    row.append(data); fragment.append(row);
  });
  if (!visible.length) {
    const row = element("tr"), empty = element("td", "Aún no hay tráfico para este origen.", "empty");
    empty.colSpan = 4; row.append(empty); fragment.append(row);
  }
  $("frames").replaceChildren(fragment);
}
async function refresh() {
  if (refreshing || closed) return;
  refreshing = true;
  try {
    state = await api("/api/state");
    $("version").textContent = state.version;
    const running = state.simulator_port !== null;
    $("sim-status").textContent = running ? "EN MARCHA" : "DETENIDO";
    $("sim-status").classList.toggle("running", running);
    $("sim-toggle").textContent = running ? "Detener simulador" : "Iniciar simulador local";
    $("sim-port").disabled = running; $("sim-unit").disabled = running;
    $("sim-endpoint").textContent = `127.0.0.1:${state.simulator_port || $("sim-port").value}`;
    events = state.events; renderFrames();
    updateQuickstart();
    const profileKey = JSON.stringify(state.profiles);
    if (profileKey !== lastProfileKey) {
      const selected = $("profile-list").value;
      $("profile-list").replaceChildren(...state.profiles.profiles.map(profile => {
        const option = element("option", profile.name); option.value = profile.name; return option;
      }));
      if (state.profiles.profiles.some(p => p.name === selected)) $("profile-list").value = selected;
      lastProfileKey = profileKey;
    }
  } catch (error) {stopPolling(); notice(`No se pudo actualizar la sesión: ${error.message}`, true);}
  finally {refreshing = false;}
}
function download(name, data) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: "application/json"}));
  const anchor = element("a"); anchor.href = url; anchor.download = name;
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function action(id, callback) {
  $(id).addEventListener("click", async () => {
    $(id).disabled = true;
    try {await callback();} catch (error) {notice(error.message, true);}
    finally {$(id).disabled = false; if (!closed) await refresh();}
  });
}
$("read-form").addEventListener("submit", event => {event.preventDefault(); stopPolling(); readOnce();});
action("poll", async () => {
  if (polling) {stopPolling(); notice("Lectura periódica detenida."); return;}
  if (!$("read-form").reportValidity()) return;
  polling = true; $("poll").textContent = "Detener repetición"; await readOnce();
});
$("read-form").addEventListener("input", event => {
  stopPolling();
  if (["host", "port", "unit"].includes(event.target.id)) $("allow-lan").checked = false;
});
$("function").addEventListener("change", updateCountLimit);
document.addEventListener("visibilitychange", () => {if (document.hidden) stopPolling();});
action("sim-toggle", async () => {
  if (state?.simulator_port) {stopPolling(); await api("/api/simulator/stop", {}); firstReadComplete = false; notice("Simulador detenido.");}
  else {await api("/api/simulator/start", {port: Number($("sim-port").value), unit: Number($("sim-unit").value)}); notice("Simulador iniciado. Puedes leerlo desde el cliente.");}
});
$("quick-demo").addEventListener("click", () => {
  if (!$("demo").disabled && !busy && !closed) $("demo").click();
});
action("demo", async () => {
  if (busy) throw new Error("Espera a que termine la lectura en curso.");
  if (!state?.simulator_port) await api("/api/simulator/start", {port: Number($("sim-port").value), unit: Number($("sim-unit").value)});
  await refresh();
  fillProfile({name: "Laboratorio local", host: "127.0.0.1", port: state.simulator_port,
    unit: state.simulator_unit, function: 3, address: 0, count: 8, timeout_ms: 1500});
  await readOnce();
});
action("memory-edit", async () => {
  await api("/api/simulator/memory", {function: Number($("memory-function").value),
    address: Number($("memory-address").value), value: Number($("memory-value").value)});
  notice("Memoria del laboratorio actualizada. Realiza otra lectura para verla.");
});
$("source-filter").addEventListener("change", renderFrames);
action("clear-frames", async () => {await api("/api/monitor/clear", {});});
action("export-frames", async () => {download("AB-Modbus-tramas.json", {schema: 1, events});});
action("load-profile", async () => {
  const profile = state.profiles.profiles.find(p => p.name === $("profile-list").value);
  if (profile) {fillProfile(profile); notice(`Perfil cargado: ${profile.name}. Red privada desactivada.`);}
});
action("save-profile", async () => {
  const profile = currentProfile();
  const profiles = state.profiles.profiles.filter(p => p.name.toLowerCase() !== profile.name.toLowerCase());
  profiles.push(profile); await api("/api/profiles", {schema: 1, profiles}); notice("Perfil guardado en este equipo.");
});
action("export-profiles", async () => {download("AB-Modbus-perfiles.json", state.profiles);});
$("import-profiles").addEventListener("change", async event => {
  const file = event.target.files[0]; if (!file) return;
  stopPolling(); $("allow-lan").checked = false;
  try {
    if (file.size > 65536) throw new Error("El archivo supera 64 KiB.");
    await api("/api/profiles", JSON.parse(await file.text()));
    notice("Perfiles importados y validados. La lista local se ha sustituido.");
    await refresh();
  } catch (error) {notice(error.message, true);} finally {event.target.value = "";}
});
action("shutdown", async () => {
  stopPolling(); await api("/api/shutdown", {}); closed = true;
  document.querySelectorAll("button,input,select").forEach(node => {node.disabled = true;});
  notice("Aplicación cerrada. Ya puedes cerrar esta pestaña.");
});
refresh();
setInterval(refresh, 1500);
