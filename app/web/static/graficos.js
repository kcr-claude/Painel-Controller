// Graficos (Chart.js local). Cores somente da paleta ARA.
const COR = { acento: "#FFA707", texto: "#494949", borda: "#D9D9D9", alerta: "#C00000", ok: "#008000" };
const brl = v => v == null ? "–" : "R$ " + Math.round(v).toLocaleString("pt-BR");
Chart.defaults.font.family = '"Aptos Narrow","Arial Narrow",Arial,sans-serif';
Chart.defaults.color = COR.texto;
Chart.defaults.animation = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 300 };

function eixos(fmt) {
  return {
    x: { grid: { display: false } },
    y: { grid: { color: COR.borda }, ticks: { callback: v => fmt(v) }, beginAtZero: true },
  };
}
const dica = { callbacks: { label: c => `${c.dataset.label}: ${brl(c.parsed.y)}` } };

function graficoMensal(id, dados) {
  const rot = ["", "JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];
  new Chart(document.getElementById(id), {
    data: {
      labels: dados.map(d => rot[d.mes] + (d.status === "Corrente" ? "*" : "")),
      datasets: [
        { type: "bar", label: "Receita orçada", data: dados.map(d => d.rec_orc), backgroundColor: COR.borda },
        { type: "bar", label: "Receita realizada", data: dados.map(d => d.rec_real), backgroundColor: COR.acento },
        { type: "line", label: "Custo orçado", data: dados.map(d => d.cus_orc), borderColor: COR.texto, borderDash: [4, 3], pointRadius: 2, backgroundColor: COR.texto },
        { type: "line", label: "Custo realizado", data: dados.map(d => d.cus_real), borderColor: COR.texto, pointRadius: 3, backgroundColor: COR.texto },
      ],
    },
    options: { maintainAspectRatio: false, scales: eixos(v => (v / 1e6).toLocaleString("pt-BR") + " mi"),
               plugins: { legend: { position: "bottom" }, tooltip: dica } },
  });
}

function graficoRitmo(id, dias, necessaria, media) {
  new Chart(document.getElementById(id), {
    data: {
      labels: dias.map(d => d.dia),
      datasets: [
        { type: "bar", label: "Receita do dia", data: dias.map(d => d.receita), backgroundColor: dias.map(d => d.lancado ? COR.acento : COR.borda) },
        { type: "line", label: "Média realizada", data: dias.map(() => media), borderColor: COR.texto, pointRadius: 0, borderWidth: 1.5 },
        { type: "line", label: "Necessária até o fim do mês", data: dias.map(d => d.lancado ? null : necessaria), borderColor: COR.alerta, borderDash: [5, 4], pointRadius: 0, borderWidth: 1.5 },
      ],
    },
    options: { maintainAspectRatio: false, scales: eixos(v => (v / 1e3).toLocaleString("pt-BR") + " mil"),
               plugins: { legend: { position: "bottom" }, tooltip: dica } },
  });
}

function graficoPareto(id, itens) {
  new Chart(document.getElementById(id), {
    data: {
      labels: itens.map(i => i.conta.length > 26 ? i.conta.slice(0, 25) + "…" : i.conta),
      datasets: [
        { type: "bar", label: "Impacto desfavorável", data: itens.map(i => i.impacto), backgroundColor: itens.map(i => i.pareto ? COR.alerta : COR.borda), yAxisID: "y" },
        { type: "line", label: "% acumulado", data: itens.map(i => i.acum * 100), borderColor: COR.texto, pointRadius: 2, yAxisID: "y2" },
      ],
    },
    options: { maintainAspectRatio: false,
      scales: { x: { grid: { display: false }, ticks: { autoSkip: false, maxRotation: 60, minRotation: 40 } },
                y: { grid: { color: COR.borda }, ticks: { callback: v => (v / 1e3).toLocaleString("pt-BR") + " mil" } },
                y2: { position: "right", min: 0, max: 100, grid: { display: false }, ticks: { callback: v => v + "%" } } },
      plugins: { legend: { position: "bottom" },
                 tooltip: { callbacks: { label: c => c.dataset.yAxisID === "y2" ? `Acumulado: ${c.parsed.y.toFixed(1).replace(".", ",")}%` : `Impacto: ${brl(c.parsed.y)}` } } } },
  });
}

// Filtro de linhas por classe (tela de custos unitarios)
function filtrarClasse(sel) {
  document.querySelectorAll("tr[data-classe]").forEach(tr => {
    tr.hidden = sel.value && tr.dataset.classe !== sel.value;
  });
}
