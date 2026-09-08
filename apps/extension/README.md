# 🛡️ TxLens Chrome Extension (Manifest V3)

A Web3 transaction safety pop-up that automatically scrapes active transaction details from dApps (e.g. Uniswap, OpenSea, or custom pages) and provides a 1-click **"Verify Transaction Authenticity"** audit.

---

## 🚀 How to Install & Load in Your Browser (Chrome / Brave / Edge / Arc)

1. Open your browser and go to the Extensions settings page:
   - **Google Chrome / Brave:** `chrome://extensions`
   - **Microsoft Edge:** `edge://extensions`
2. Toggle on **Developer mode** in the top right corner.
3. Click the **"Load unpacked"** button.
4. Select the directory:
   ```
   txlens/apps/extension
   ```
5. Pin the **TxLens Security Shield** icon (🛡️) to your browser toolbar.

---

## 💡 How it Works

1. **Transaction Phase Detection:** Whenever you are about to execute a transfer, swap, or contract call on any dApp, click the TxLens extension icon.
2. **Auto-Scraped Details:** The extension automatically scans the active tab for recipient addresses, ETH amounts, and smart contract payloads.
3. **1-Click Verification:** Click **"Verify Transaction Authenticity"**.
4. **Instant 3-State Verdict:**
   - 🟢 **SAFE:** Low threat, simulation passed, verified contract.
   - 🟡 **MID:** Caution advised, unverified contract or new address.
   - 🔴 **RISK:** High danger, possible wallet drainer, phishing attack, or simulation revert.
5. **Top 3 Reasons:** Instant summary of the top 3 safety signals evaluated by simulation, AI, and risk models.
