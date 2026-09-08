// TxLens Extension Options Management

document.addEventListener("DOMContentLoaded", () => {
  const shieldEnabled = document.getElementById("shieldEnabled");
  const autoIntercept = document.getElementById("autoIntercept");
  const apiUrl = document.getElementById("apiUrl");
  const defaultChain = document.getElementById("defaultChain");
  const saveBtn = document.getElementById("saveBtn");
  const statusMessage = document.getElementById("statusMessage");

  // Load existing settings
  chrome.storage.local.get(
    {
      shieldEnabled: true,
      autoIntercept: true,
      apiUrl: "http://localhost:8000/api/v1",
      defaultChain: "base-sepolia",
    },
    (items) => {
      shieldEnabled.checked = items.shieldEnabled;
      autoIntercept.checked = items.autoIntercept;
      apiUrl.value = items.apiUrl;
      defaultChain.value = items.defaultChain;
    }
  );

  // Save settings
  saveBtn.addEventListener("click", () => {
    chrome.storage.local.set(
      {
        shieldEnabled: shieldEnabled.checked,
        autoIntercept: autoIntercept.checked,
        apiUrl: apiUrl.value.trim(),
        defaultChain: defaultChain.value,
      },
      () => {
        statusMessage.textContent = "✓ Settings saved successfully!";
        statusMessage.className = "status-msg status-success";
        setTimeout(() => {
          statusMessage.textContent = "";
        }, 2500);
      }
    );
  });
});
