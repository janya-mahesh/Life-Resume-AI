// Load saved settings
document.addEventListener("DOMContentLoaded", () => {
  chrome.storage.local.get(["email", "serverUrl"], (result) => {
    if (result.email) document.getElementById("email").value = result.email;
    if (result.serverUrl) document.getElementById("serverUrl").value = result.serverUrl;
  });
});

// Save settings
document.getElementById("saveBtn").addEventListener("click", () => {
  const email = document.getElementById("email").value.trim();
  const serverUrl = document.getElementById("serverUrl").value.trim() || "https://life-resume-ai.onrender.com";

  if (!email) {
    document.getElementById("status").textContent = "Please enter your email.";
    return;
  }

  chrome.storage.local.set({ email, serverUrl }, () => {
    document.getElementById("status").textContent = "Settings saved!";
    setTimeout(() => { document.getElementById("status").textContent = ""; }, 2000);
  });
});
