/**
 * TxLens Background Service Worker — Handles state, badges, and notification routing.
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log("TxLens Web3 Security Shield extension installed.");
});

// Update extension icon badge depending on safety verdict
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "UPDATE_BADGE") {
    const { status, text } = message;
    if (status === "SAFE") {
      chrome.action.setBadgeBackgroundColor({ color: "#10b981" });
      chrome.action.setBadgeText({ text: text || "✓" });
    } else if (status === "MID") {
      chrome.action.setBadgeBackgroundColor({ color: "#f59e0b" });
      chrome.action.setBadgeText({ text: text || "!" });
    } else if (status === "RISK") {
      chrome.action.setBadgeBackgroundColor({ color: "#ef4444" });
      chrome.action.setBadgeText({ text: text || "✕" });
    } else {
      chrome.action.setBadgeText({ text: "" });
    }
    sendResponse({ ok: true });
  }
  return true;
});
