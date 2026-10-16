// Ask before submitting forms marked with data-confirm (delete, remove member, ...).
document.addEventListener("submit", (event) => {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});

// Copy buttons: <button data-copy="#selector">
document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const text = document.querySelector(button.dataset.copy).textContent.trim();
    try {
      await navigator.clipboard.writeText(text);
      const original = button.textContent;
      button.textContent = "کاپی شد ✓";
      setTimeout(() => (button.textContent = original), 1500);
    } catch {
      window.prompt("کد را کاپی کنید:", text);
    }
  });
});

// Charts on the dashboard.
const chartDataEl = document.getElementById("chart-data");
if (chartDataEl && window.Chart) {
  const data = JSON.parse(chartDataEl.textContent);
  const css = getComputedStyle(document.documentElement);
  const muted = css.getPropertyValue("--muted").trim();
  const border = css.getPropertyValue("--border").trim();
  const fa = (n) => Number(n).toLocaleString("fa-IR");

  Chart.defaults.font.family = "Vazirmatn, Tahoma, sans-serif";
  Chart.defaults.color = muted;

  new Chart(document.getElementById("categoryChart"), {
    type: "doughnut",
    data: {
      labels: data.categories.map((c) => c.label),
      datasets: [{
        data: data.categories.map((c) => c.value),
        backgroundColor: data.categories.map((c) => c.color),
        borderColor: "rgba(255, 255, 255, .9)",
        borderWidth: 3,
        hoverOffset: 8,
      }],
    },
    options: {
      maintainAspectRatio: false,
      cutout: "58%",
      plugins: {
        legend: { position: "bottom", rtl: true, labels: { usePointStyle: true, padding: 14 } },
        tooltip: {
          rtl: true,
          callbacks: {
            label: (ctx) => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = Math.round((ctx.parsed * 100) / total);
              return ` ${ctx.label}: ${fa(ctx.parsed)} ؋ (${fa(pct)}٪)`;
            },
          },
        },
      },
    },
  });

  new Chart(document.getElementById("dailyChart"), {
    type: "bar",
    data: {
      labels: data.dayLabels,
      datasets: [{
        data: data.daily,
        // Lapis bars fading toward saffron at the top.
        backgroundColor: (ctx) => {
          const { chartArea, ctx: c } = ctx.chart;
          if (!chartArea) return "#2c55c9";
          const g = c.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
          g.addColorStop(0, "#1d3b8f");
          g.addColorStop(1, "#f2a541");
          return g;
        },
        borderRadius: 6,
        maxBarThickness: 22,
      }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          rtl: true,
          callbacks: {
            title: (items) => `روز ${items[0].label}`,
            label: (ctx) => ` ${fa(ctx.parsed.y)} ؋`,
          },
        },
      },
      scales: {
        x: { reverse: true, grid: { display: false } },
        y: { beginAtZero: true, position: "right", grid: { color: border }, ticks: { callback: (v) => fa(v) } },
      },
    },
  });
}
