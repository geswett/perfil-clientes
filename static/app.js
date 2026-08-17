const REQUISITOS_FILAS = [
  "Formación",
  "Experiencia",
  "Experiencia en la industria",
  "Competencias Técnicas",
  "Licencia",
  "Idioma",
];

let currentTab = "audio";
let currentPerfil = null;

// ---------- Tabs ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    currentTab = btn.dataset.tab;
    document.getElementById(`tab-${currentTab}`).classList.add("active");
  });
});

// ---------- Helpers ----------
function getByPath(obj, path) {
  return path.split(".").reduce((o, k) => (o ? o[k] : undefined), obj);
}
function setByPath(obj, path, value) {
  const keys = path.split(".");
  let o = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (!o[keys[i]]) o[keys[i]] = {};
    o = o[keys[i]];
  }
  o[keys[keys.length - 1]] = value;
}

function showError(msg) {
  const box = document.getElementById("error-box");
  box.textContent = msg;
  box.hidden = false;
}
function hideError() {
  document.getElementById("error-box").hidden = true;
}

// ---------- Procesar ----------
document.getElementById("btn-procesar").addEventListener("click", async () => {
  hideError();
  const empresa = document.getElementById("empresa").value.trim();
  const cargo = document.getElementById("cargo").value.trim();

  const formData = new FormData();
  formData.append("modo", currentTab);
  formData.append("empresa", empresa);
  formData.append("cargo", cargo);

  if (currentTab === "audio") {
    const file = document.getElementById("input-audio").files[0];
    if (!file) return showError("Selecciona un archivo de audio primero.");
    formData.append("archivo", file);
  } else if (currentTab === "imagen") {
    const file = document.getElementById("input-imagen").files[0];
    if (!file) return showError("Selecciona o toma una foto primero.");
    formData.append("archivo", file);
  } else {
    const texto = document.getElementById("input-texto").value.trim();
    if (!texto) return showError("Escribe el texto de la reunión primero.");
    formData.append("texto", texto);
  }

  const btn = document.getElementById("btn-procesar");
  const loading = document.getElementById("loading");
  btn.disabled = true;
  loading.hidden = false;

  try {
    const res = await fetch("/api/procesar", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || "Ocurrió un error procesando la solicitud.");
      return;
    }
    currentPerfil = data.perfil;
    document.getElementById("transcripcion-texto").textContent = data.transcripcion || "";
    renderPerfil(currentPerfil);
    document.getElementById("paso-revision").hidden = false;
    document.getElementById("paso-revision").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    showError("No se pudo conectar con el servidor: " + err.message);
  } finally {
    btn.disabled = false;
    loading.hidden = true;
  }
});

// ---------- Render del formulario editable ----------
function renderPerfil(perfil) {
  document.querySelectorAll("[data-path]").forEach((el) => {
    const val = getByPath(perfil, el.dataset.path);
    el.value = val || "";
  });

  renderFunciones(perfil.descripcion_cargo?.funciones_cargo || []);
  renderRequisitos(perfil.requisitos || []);
  renderCompetencias(perfil.competencias || []);
}

function renderFunciones(funciones) {
  const ul = document.getElementById("lista-funciones");
  ul.innerHTML = "";
  funciones.forEach((f) => addFuncionRow(f));
  if (funciones.length === 0) addFuncionRow("");
}
function addFuncionRow(texto) {
  const ul = document.getElementById("lista-funciones");
  const li = document.createElement("li");
  const input = document.createElement("input");
  input.type = "text";
  input.value = texto;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = "✕";
  btn.addEventListener("click", () => li.remove());
  li.appendChild(input);
  li.appendChild(btn);
  ul.appendChild(li);
}
document.getElementById("btn-add-funcion").addEventListener("click", () => addFuncionRow(""));

function renderRequisitos(requisitos) {
  const tbody = document.querySelector("#tabla-requisitos tbody");
  tbody.innerHTML = "";
  const byName = {};
  requisitos.forEach((r) => (byName[(r.requerimiento || "").trim().toLowerCase()] = r));

  REQUISITOS_FILAS.forEach((nombre) => {
    const r = byName[nombre.toLowerCase()] || {};
    const tr = document.createElement("tr");

    const tdNombre = document.createElement("td");
    tdNombre.textContent = nombre;
    tdNombre.dataset.requerimiento = nombre;

    const tdExc = document.createElement("td");
    const inpExc = document.createElement("input");
    inpExc.type = "text";
    inpExc.value = r.excluyente || "";
    inpExc.dataset.field = "excluyente";
    tdExc.appendChild(inpExc);

    const tdDes = document.createElement("td");
    const inpDes = document.createElement("input");
    inpDes.type = "text";
    inpDes.value = r.deseable || "";
    inpDes.dataset.field = "deseable";
    tdDes.appendChild(inpDes);

    tr.appendChild(tdNombre);
    tr.appendChild(tdExc);
    tr.appendChild(tdDes);
    tbody.appendChild(tr);
  });
}

function renderCompetencias(competencias) {
  const tbody = document.querySelector("#tabla-competencias tbody");
  tbody.innerHTML = "";
  competencias.forEach((c) => addCompetenciaRow(c.competencia, c.definicion));
  if (competencias.length === 0) addCompetenciaRow("", "");
}
function addCompetenciaRow(nombre, definicion) {
  const tbody = document.querySelector("#tabla-competencias tbody");
  const tr = document.createElement("tr");

  const tdNombre = document.createElement("td");
  const inpNombre = document.createElement("input");
  inpNombre.type = "text";
  inpNombre.value = nombre || "";
  inpNombre.dataset.field = "competencia";
  tdNombre.appendChild(inpNombre);

  const tdDef = document.createElement("td");
  const txtDef = document.createElement("textarea");
  txtDef.rows = 2;
  txtDef.value = definicion || "";
  txtDef.dataset.field = "definicion";
  tdDef.appendChild(txtDef);

  const tdBtn = document.createElement("td");
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = "✕";
  btn.addEventListener("click", () => tr.remove());
  tdBtn.appendChild(btn);

  tr.appendChild(tdNombre);
  tr.appendChild(tdDef);
  tr.appendChild(tdBtn);
  tbody.appendChild(tr);
}
document.getElementById("btn-add-competencia").addEventListener("click", () => addCompetenciaRow("", ""));

// ---------- Recolectar datos editados ----------
function collectPerfil() {
  const perfil = JSON.parse(JSON.stringify(currentPerfil || {}));

  document.querySelectorAll("[data-path]").forEach((el) => {
    setByPath(perfil, el.dataset.path, el.value);
  });

  const funciones = Array.from(document.querySelectorAll("#lista-funciones input"))
    .map((i) => i.value.trim())
    .filter(Boolean);
  if (!perfil.descripcion_cargo) perfil.descripcion_cargo = {};
  perfil.descripcion_cargo.funciones_cargo = funciones;

  const requisitos = [];
  document.querySelectorAll("#tabla-requisitos tbody tr").forEach((tr) => {
    const nombre = tr.querySelector("td[data-requerimiento]").dataset.requerimiento;
    const excluyente = tr.querySelector('[data-field="excluyente"]').value.trim();
    const deseable = tr.querySelector('[data-field="deseable"]').value.trim();
    requisitos.push({ requerimiento: nombre, excluyente, deseable });
  });
  perfil.requisitos = requisitos;

  const competencias = [];
  document.querySelectorAll("#tabla-competencias tbody tr").forEach((tr) => {
    const competencia = tr.querySelector('[data-field="competencia"]').value.trim();
    const definicion = tr.querySelector('[data-field="definicion"]').value.trim();
    if (competencia || definicion) competencias.push({ competencia, definicion });
  });
  perfil.competencias = competencias;

  return perfil;
}

// ---------- Descargar Word ----------
document.getElementById("btn-descargar").addEventListener("click", async () => {
  hideError();
  const perfil = collectPerfil();
  const empresa = document.getElementById("empresa").value.trim();
  const cargo = document.getElementById("cargo").value.trim();
  const consultor = document.getElementById("consultor").value.trim();

  const btn = document.getElementById("btn-descargar");
  btn.disabled = true;
  btn.textContent = "Generando…";

  try {
    const res = await fetch("/api/generar-docx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ perfil, empresa, cargo, consultor }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      showError(data.error || "No se pudo generar el documento.");
      return;
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : "Perfil_Cargo.docx";

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    showError("No se pudo conectar con el servidor: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "⬇ Descargar Word (.docx)";
  }
});
