// Replaces the browser's confirm() dialog with a Bootstrap modal for buttons that have hx-confirm.
(function () {
  const element = document.getElementById("delete-modal");
  const modal = new bootstrap.Modal(element);
  let issuePendingRequest = null;

  // htmx fires htmx:confirm before every request; detail.question holds the hx-confirm text
  document.body.addEventListener("htmx:confirm", (event) => {
    if (!event.detail.question) return; // no hx-confirm on this element - let the request go
    event.preventDefault(); // hold the request until the user decides
    element.querySelector("[data-delete-question]").textContent = event.detail.question;
    issuePendingRequest = event.detail.issueRequest;
    modal.show();
  });

  element.querySelector("[data-delete-confirm]").addEventListener("click", () => {
    modal.hide();
    if (issuePendingRequest) issuePendingRequest(true); // true = skip the native confirm()
    issuePendingRequest = null;
  });

  // Closing the modal any other way (Cancel, Esc, click outside) drops the request
  element.addEventListener("hidden.bs.modal", () => {
    issuePendingRequest = null;
  });
})();