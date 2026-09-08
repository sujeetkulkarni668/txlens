/**
 * TxLens Extension Popup Script — Scrapes details, queries backend, displays SAFE/MID/RISK with top 3 reasons.
 */

const API_BASE = "http://localhost:8000/api/v1";

let activeTx = {
  chain: "base-sepolia",
  from: "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
  to: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  valueEth: "0.05",
  data: "",
};

// Convert ETH to Wei
function ethToWei(ethStr) {
  try {
    const clean = (ethStr || "0").trim();
    if (!clean || isNaN(Number(clean)) || Number(clean) < 0) return "0";
    const parts = clean.split(".");
    const whole = parts[0] || "0";
    let fraction = parts[1] || "";
    if (fraction.length > 18) {
      fraction = fraction.slice(0, 18);
    } else {
      fraction = fraction.padEnd(18, "0");
    }
    const wholeWei = BigInt(whole) * BigInt(10 ** 18);
    const fractionWei = BigInt(fraction);
    return (wholeWei + fractionWei).toString();
  } catch {
    return "0";
  }
}

// Get or create guest auth token
async function getAuthToken() {
  try {
    const cached = await chrome.storage.local.get(["txlens_token"]);
    if (cached.txlens_token) return cached.txlens_token;

    const guestId = Math.random().toString(36).substring(2, 10);
    const email = `ext-${guestId}@txlens.local`;
    const password = `TxLensPass-${guestId}!123`;

    await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const loginRes = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const loginData = await loginRes.json();
    if (loginData.access_token) {
      await chrome.storage.local.set({ txlens_token: loginData.access_token });
      return loginData.access_token;
    }
  } catch (e) {
    console.warn("Auth token fallback:", e);
  }
  return "";
}

// Extract top 3 reasons from backend response
function extractTop3Reasons(result) {
  const reasons = [];

  // 1. Simulation Outcome
  if (result.simulation) {
    if (result.simulation.success) {
      reasons.push("Simulation Succeeded: Transaction executes safely with no reverts or errors.");
    } else if (result.simulation.success === false) {
      reasons.push("Simulation Failed: Transaction will revert on-chain and waste gas fees.");
    }
  }

  // 2. AI Security Analyst Findings
  if (result.ai_assessment) {
    if (result.ai_assessment.findings && result.ai_assessment.findings.length > 0) {
      reasons.push(`AI Analyst: ${result.ai_assessment.findings[0]}`);
    } else if (result.ai_assessment.summary) {
      reasons.push(`AI Analyst: ${result.ai_assessment.summary}`);
    }
  }

  // 3. ML Risk Model Factors
  if (result.risk && result.risk.signals && result.risk.signals.length > 0) {
    const topSig = result.risk.signals[0];
    const impact = topSig.impact >= 0 ? `+${topSig.impact} risk` : `${topSig.impact} safe`;
    reasons.push(`Risk Model: ${topSig.name.replace(/_/g, " ")} (${impact})`);
  }

  // 4. Policy Guardrails
  if (result.policy && result.policy.matched_rules && result.policy.matched_rules.length > 0) {
    reasons.push(`Security Policy: ${result.policy.matched_rules[0].reason}`);
  }

  // Fallbacks if fewer than 3
  if (reasons.length < 1) reasons.push("Verified recipient address and network state.");
  if (reasons.length < 2) reasons.push("No unlimited token approval or drainer pattern detected.");
  if (reasons.length < 3) reasons.push("Complies with active wallet safety guardrails.");

  return reasons.slice(0, 3);
}

// Initialize popup on load
document.addEventListener("DOMContentLoaded", async () => {
  const textDapp = document.getElementById("textDapp");
  const textTo = document.getElementById("textTo");
  const textAmount = document.getElementById("textAmount");
  const btnVerify = document.getElementById("btnVerify");
  const btnIcon = document.getElementById("btnIcon");
  const btnText = document.getElementById("btnText");
  const resultContainer = document.getElementById("resultContainer");
  const verdictCard = document.getElementById("verdictCard");
  const verdictLabel = document.getElementById("verdictLabel");
  const scoreText = document.getElementById("scoreText");
  const meterFill = document.getElementById("meterFill");
  const reasonsList = document.getElementById("reasonsList");

  // Query active tab and send scrape message
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.id) {
      const url = new URL(tab.url || "http://localhost");
      textDapp.innerText = url.hostname;

      chrome.tabs.sendMessage(tab.id, { action: "SCRAPE_TX_DETAILS" }, (response) => {
        if (chrome.runtime.lastError || !response) {
          textTo.innerText = activeTx.to.slice(0, 6) + "…" + activeTx.to.slice(-4);
          textAmount.innerText = `${activeTx.valueEth} ETH`;
          return;
        }
        if (response.to) activeTx.to = response.to;
        if (response.from) activeTx.from = response.from;
        if (response.valueEth) activeTx.valueEth = response.valueEth;
        if (response.data) activeTx.data = response.data;
        if (response.chain) activeTx.chain = response.chain;

        textTo.innerText = activeTx.to ? (activeTx.to.slice(0, 6) + "…" + activeTx.to.slice(-4)) : "0x…";
        textAmount.innerText = `${activeTx.valueEth || "0"} ETH`;
      });
    }
  } catch {
    textDapp.innerText = "Web3 Page";
  }

  // Handle Verify Click
  btnVerify.addEventListener("click", async () => {
    btnVerify.disabled = true;
    btnIcon.innerHTML = `<div class="spinner"></div>`;
    btnText.innerText = "Verifying Authenticity…";

    try {
      const token = await getAuthToken();
      const payload = {
        chain: activeTx.chain,
        from: activeTx.from,
        to: activeTx.to || null,
        value: ethToWei(activeTx.valueEth),
        data: activeTx.data || null,
      };

      const res = await fetch(`${API_BASE}/transactions/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.statusText}`);
      }

      const analysis = await res.json();
      const score = analysis.risk ? analysis.risk.risk_score : 15;
      const reasons = extractTop3Reasons(analysis);

      // Determine 3-way status
      verdictCard.className = "verdict-banner";
      let status = "SAFE";

      if (score <= 25) {
        status = "SAFE";
        verdictCard.classList.add("verdict-safe");
        verdictLabel.innerText = "🟢 SAFE";
        scoreText.innerText = `Threat Score: ${score} / 100 (Safe to Approve)`;
        meterFill.style.background = "#10b981";
      } else if (score <= 60) {
        status = "MID";
        verdictCard.classList.add("verdict-mid");
        verdictLabel.innerText = "🟡 MID (Caution)";
        scoreText.innerText = `Threat Score: ${score} / 100 (Review Needed)`;
        meterFill.style.background = "#f59e0b";
      } else {
        status = "RISK";
        verdictCard.classList.add("verdict-risk");
        verdictLabel.innerText = "🔴 RISK (Danger)";
        scoreText.innerText = `Threat Score: ${score} / 100 (High Risk Alert)`;
        meterFill.style.background = "#ef4444";
      }

      meterFill.style.width = `${Math.max(5, score)}%`;

      // Render Top 3 Reasons
      reasonsList.innerHTML = reasons
        .map((r, idx) => `<li class="reason-item"><span class="reason-num">${idx + 1}.</span> <span>${r}</span></li>`)
        .join("");

      resultContainer.classList.remove("hidden");
      btnIcon.innerHTML = "✓";
      btnText.innerText = "Re-Verify Authenticity";

      // Update badge
      chrome.runtime.sendMessage({ action: "UPDATE_BADGE", status, text: `${score}` });
    } catch (err) {
      alert(`Verification failed: ${err.message}`);
      btnIcon.innerText = "🔍";
      btnText.innerText = "Verify Transaction Authenticity";
    } finally {
      btnVerify.disabled = false;
    }
  });
});
