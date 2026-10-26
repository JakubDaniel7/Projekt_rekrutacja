// Fills the weather column of the contact list.
// Each unique city is requested only once per page view; the server caches the results.
(function () {
  const weatherByCity = new Map(); // lowercase city -> Promise with the JSON response

  function fetchWeather(url, city) {
    const key = city.trim().toLowerCase();
    if (!weatherByCity.has(key)) {
      const request = fetch(`${url}?city=${encodeURIComponent(city)}`)
        .then((response) => response.json())
        .catch(() => ({ error: "Brak połączenia z serwerem." }));
      weatherByCity.set(key, request);
    }
    return weatherByCity.get(key);
  }

  // WMO weather codes (returned by Open-Meteo) grouped into an icon and a Polish description
  const CONDITIONS = [
    { codes: [0], icon: "bi-sun", label: "Bezchmurnie" },
    { codes: [1, 2], icon: "bi-cloud-sun", label: "Częściowe zachmurzenie" },
    { codes: [3], icon: "bi-clouds", label: "Pochmurno" },
    { codes: [45, 48], icon: "bi-cloud-fog2", label: "Mgła" },
    { codes: [51, 53, 55, 56, 57], icon: "bi-cloud-drizzle", label: "Mżawka" },
    { codes: [61, 63, 65, 66, 67, 80, 81, 82], icon: "bi-cloud-rain", label: "Deszcz" },
    { codes: [71, 73, 75, 77, 85, 86], icon: "bi-cloud-snow", label: "Śnieg" },
    { codes: [95, 96, 99], icon: "bi-cloud-lightning-rain", label: "Burza" },
  ];

  function describe(code) {
    return CONDITIONS.find((condition) => condition.codes.includes(code))
      || { icon: "bi-cloud", label: "Pogoda" };
  }

  function renderWeather(cell, data) {
    if (data.error) {
      const info = document.createElement("span");
      info.className = "text-body-secondary";
      info.textContent = "brak danych";
      info.title = data.error;
      cell.replaceChildren(info);
      return;
    }
    const condition = describe(data.weather_code);
    cell.innerHTML = `
      <span class="me-2" title="${condition.label}">
        <i class="bi ${condition.icon} text-body-secondary"></i>
        <span class="fw-semibold">${Math.round(data.temperature)}°C</span>
      </span>
      <span class="me-2 text-body-secondary" title="Wilgotność"><i class="bi bi-droplet"></i> ${Math.round(data.humidity)}%</span>
      <span class="text-body-secondary" title="Wiatr"><i class="bi bi-wind"></i> ${Math.round(data.wind_speed)} km/h</span>`;
  }

  function loadWeather(root) {
    root.querySelectorAll("[data-weather-city]:not([data-weather-loaded])").forEach((cell) => {
      cell.dataset.weatherLoaded = "true";
      const url = cell.closest("[data-weather-url]").dataset.weatherUrl;
      fetchWeather(url, cell.dataset.weatherCity).then((data) => renderWeather(cell, data));
    });
  }

  // Runs on page load and again whenever htmx swaps in a new table (search, sorting, paging)
  htmx.onLoad(loadWeather);
})();