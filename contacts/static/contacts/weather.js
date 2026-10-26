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

  function renderWeather(cell, data) {
    if (data.error) {
      const info = document.createElement("span");
      info.className = "text-body-secondary small";
      info.textContent = "brak danych";
      info.title = data.error;
      cell.replaceChildren(info);
      return;
    }
    cell.innerHTML = `
      <span class="me-2" title="Temperatura"><i class="bi bi-thermometer-half text-danger"></i> ${Math.round(data.temperature)}°C</span>
      <span class="me-2" title="Wilgotność"><i class="bi bi-droplet text-info"></i> ${Math.round(data.humidity)}%</span>
      <span title="Wiatr"><i class="bi bi-wind text-secondary"></i> ${Math.round(data.wind_speed)} km/h</span>`;
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