document.getElementById('saveEmail').addEventListener('click', () => {
  const email = document.getElementById('email').value.trim();
  if (email) {
    chrome.storage.local.set({ email }, () => {
      document.getElementById('status').textContent = "Email saved!";
    });
  }
});

// Populate existing
chrome.storage.local.get(["email"], (res) => {
  if (res.email) {
    document.getElementById('email').value = res.email;
  }
});
