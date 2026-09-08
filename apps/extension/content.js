/**
 * TxLens Content Script — Auto-Scrapes Web3 Transaction Parameters from Active dApp Pages.
 */

function scrapeTransactionDetails() {
  const result = {
    found: false,
    from: "",
    to: "",
    valueEth: "0",
    data: "",
    chain: "base-sepolia",
    dappName: window.location.hostname || "Web3 dApp",
    pageTitle: document.title || "dApp Interaction",
  };

  // 1. Scan for Ethereum / EVM Addresses in Inputs or Text
  const ethAddressRegex = /0x[a-fA-F0-9]{40}/g;

  // Search input fields
  const inputs = Array.from(document.querySelectorAll("input, textarea"));
  for (const input of inputs) {
    const val = (input.value || "").trim();
    const placeholder = (input.placeholder || "").toLowerCase();
    const name = (input.name || "").toLowerCase();
    const id = (input.id || "").toLowerCase();

    // Check for recipient / contract address
    if (ethAddressRegex.test(val)) {
      if (!result.to && (name.includes("to") || name.includes("recipient") || name.includes("contract") || placeholder.includes("0x") || id.includes("to") || id.includes("recipient"))) {
        result.to = val.match(ethAddressRegex)[0];
        result.found = true;
      } else if (!result.from && (name.includes("from") || name.includes("sender") || placeholder.includes("sender") || id.includes("from"))) {
        result.from = val.match(ethAddressRegex)[0];
        result.found = true;
      } else if (!result.to) {
        result.to = val.match(ethAddressRegex)[0];
        result.found = true;
      }
    }

    // Check for amount / value
    if (name.includes("amount") || name.includes("value") || placeholder.includes("0.0") || placeholder.includes("amount") || id.includes("amount")) {
      if (val && !isNaN(Number(val)) && Number(val) > 0) {
        result.valueEth = val;
        result.found = true;
      }
    }

    // Check for calldata / payload
    if ((name.includes("data") || name.includes("payload") || placeholder.includes("calldata")) && val.startsWith("0x")) {
      result.data = val;
      result.found = true;
    }
  }

  // 2. Scan for connected wallet in window or document text
  if (!result.from) {
    const bodyText = document.body.innerText || "";
    const matches = bodyText.match(ethAddressRegex);
    if (matches && matches.length > 0) {
      if (!result.to) {
        result.to = matches[0];
        result.found = true;
      } else if (result.to !== matches[0]) {
        result.from = matches[0];
        result.found = true;
      }
    }
  }

  // 3. Fallback defaults if on TxLens or standard dApp
  if (!result.from) {
    result.from = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e";
  }

  return result;
}

// Listen for messages from extension popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "SCRAPE_TX_DETAILS") {
    const scraped = scrapeTransactionDetails();
    sendResponse(scraped);
  }
  return true;
});
