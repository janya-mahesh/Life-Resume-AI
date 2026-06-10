let activeTabId = null;
let activeStartTime = null;
let lastUrl = "";
let usageData = [];

// Get server URL and email from storage
function getConfig(callback) {
  chrome.storage.local.get(["email", "serverUrl"], (result) => {
    callback({
      email: result.email || null,
      serverUrl: result.serverUrl || "http://localhost:5000"
    });
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
      timestamp: Date.now()
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
    getConfig((config) => {
      if (config.email) {
        fetch(`${config.serverUrl}/screen-time-data`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: config.email, usageData })
        })
          .then(() => usageData = [])
          .catch(err => console.error("Error sending data:", err));
      } else {
        console.warn("No email saved in popup");
      }
    });
  }
}, 60000);
