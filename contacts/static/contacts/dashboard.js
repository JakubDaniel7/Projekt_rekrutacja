// Dashboard charts (Chart.js). Data comes from the page as JSON (Django's json_script filter).
(function () {
  const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const readData = (id) => JSON.parse(document.getElementById(id).textContent);

  // Draws each bar's value just past its end, so no value axis is needed
  const valueLabels = {
    id: "valueLabels",
    afterDatasetsDraw(chart) {
      const { ctx } = chart;
      ctx.save();
      ctx.fillStyle = cssVar("--bs-body-color");
      ctx.font = `600 12px ${cssVar("--bs-body-font-family")}`;
      ctx.textBaseline = "middle";
      chart.getDatasetMeta(0).data.forEach((bar, index) => {
        ctx.fillText(chart.data.datasets[0].data[index], bar.x + 6, bar.y);
      });
      ctx.restore();
    },
  };

  function barChart(canvasId, items, colors) {
    return new Chart(document.getElementById(canvasId), {
      type: "bar",
      data: {
        labels: items.map((item) => item.label),
        datasets: [{
          data: items.map((item) => item.count),
          backgroundColor: colors,
          borderRadius: 4,
          borderSkipped: "start", // rounded at the value end, square at the baseline
          maxBarThickness: 24,
        }],
      },
      options: {
        indexAxis: "y", // horizontal bars - long city names stay readable
        maintainAspectRatio: false,
        layout: { padding: { right: 32 } }, // room for the value labels
        plugins: {
          legend: { display: false }, // one series - the card title says what is shown
          tooltip: { callbacks: { label: (context) => `Kontakty: ${context.parsed.x}` } },
        },
        scales: {
          x: { display: false, beginAtZero: true },
          y: {
            grid: { display: false },
            border: { display: false },
            ticks: { color: cssVar("--bs-secondary-color") },
          },
        },
      },
      plugins: [valueLabels],
    });
  }

    const cities = readData("city-data");
    const statuses = readData("status-data");
    let charts = [];

    function drawCharts() {
        charts.forEach((chart) => chart.destroy());
        charts = [
        // Cities: one color, with the "other cities" bar in gray so it reads as context
        barChart("city-chart", cities, cities.map((city) => cssVar(city.other ? "--app-muted-bar" : "--bs-primary"))),
        // Statuses: the same colors as their badges in the contact list
        barChart("status-chart", statuses, statuses.map((status) => cssVar(`--bs-${status.color}`))),
        ];
    }

    drawCharts();
    // Colors are read from CSS variables, so redraw when the user switches light/dark theme
    document.addEventListener("themechange", drawCharts);
})();