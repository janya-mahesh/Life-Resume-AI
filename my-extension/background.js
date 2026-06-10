let activeTabId = null;
let activeStartTime = null;
let lastUrl = "";
let usageData = [];

// Helper: get email from local storage
function getUserEmail(callback) {
  chrome.storage.local.get(["email"], (result) => {
    callback(result.email || null);
  });
}

// Save data before switching
function saveUsageData() {
  if (activeTabId && activeStartTime) {
    const timeSpent = (Date.now() - activeStartTime) / 1000; // seconds
    usageData.push({
      tabId: activeTabId,
      timeSpent,
      url: lastUrl,
      timestamp: Date.now()  // ✅ Required for daily analysis
    });
    activeStartTime = Date.now();
  }
}

// Track tab switches
chrome.tabs.onActivated.addListener((activeInfo) => {
  saveUsageData();
  activeTabId = activeInfo.tabId;
  activeStartTime = Date.now();
  chrome.tabs.get(activeTabId, (tab) => {
    lastUrl = tab.url;
  });
});

// Track tab reloads
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (tab.active && changeInfo.status === "complete") {
    lastUrl = tab.url;
  }
});

// Send data every 60 seconds
setInterval(() => {
  saveUsageData();
  if (usageData.length > 0) {
    getUserEmail((email) => {
      if (email) {
        fetch("http://localhost:5000/screen-time-data", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, usageData })
        })
          .then(() => usageData = [])
          .catch(err => console.error("Error sending data:", err));
      } else {
        console.warn("⚠ No email saved in popup");
      }
    });
  }
}, 60000);
