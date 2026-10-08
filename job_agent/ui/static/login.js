"use strict";
document.querySelector("#login-form").addEventListener("submit", async event => {
  event.preventDefault(); const button = event.target.querySelector("button"); button.disabled = true;
  try {
    const response = await fetch("/api/login", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({code: document.querySelector("#access-code").value})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    location.reload();
  } catch (error) { document.querySelector("#login-status").textContent = error.message; }
  finally { button.disabled = false; }
});
