// Client-side validation of the contact form. The server checks the same rules again,
// plus uniqueness, which only the database can verify.
(function () {
  const form = document.querySelector("[data-contact-form]");
  if (!form) return;

  const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const PHONE_PATTERN = /^\+?\d{9,15}$/; // same rule as Contact.clean() on the server

  const fields = Array.from(form.querySelectorAll("input, select")).filter(
    (input) => input.name && input.type !== "hidden"
  );

  // Returns an error message, or "" if the value is valid
  function validate(input) {
    const value = input.value.trim();
    if (input.required && !value) {
      return "To pole jest wymagane.";
    }
    if (input.name === "email" && !EMAIL_PATTERN.test(value)) {
      return "Podaj poprawny adres e-mail, np. jan@example.com.";
    }
    if (input.name === "phone" && !PHONE_PATTERN.test(value.replace(/[\s\-()]/g, ""))) {
      return "Podaj od 9 do 15 cyfr, opcjonalnie z + na początku.";
    }
    return "";
  }

  function showResult(input, message) {
    input.classList.toggle("is-invalid", message !== "");
    input.classList.toggle("is-valid", message === "");
    document.getElementById(`${input.id}-error`).textContent = message;
  }

  fields.forEach((input) => {
    // Check a field when the user leaves it (if they typed anything)...
    input.addEventListener("blur", () => {
      if (input.value !== "") showResult(input, validate(input));
    });
    // ...and live while they are fixing an error
    input.addEventListener("input", () => {
      if (input.classList.contains("is-invalid")) showResult(input, validate(input));
    });
  });

  form.addEventListener("submit", (event) => {
    let firstInvalid = null;
    fields.forEach((input) => {
      const message = validate(input);
      showResult(input, message);
      if (message && !firstInvalid) firstInvalid = input;
    });
    if (firstInvalid) {
      event.preventDefault(); // do not send the form, show the errors instead
      firstInvalid.focus();
    }
  });
})();