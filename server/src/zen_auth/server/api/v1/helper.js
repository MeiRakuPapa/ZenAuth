function renderErrors(errors) {
  if (!Array.isArray(errors)) return "";
  return "<ul>" + errors.map((e) => `<li>${e}</li>`).join("") + "</ul>";
}
