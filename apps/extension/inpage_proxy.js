/**
 * TxLens In-Page EIP-1193 Web3 Provider Interceptor
 * Intercepts eth_sendTransaction & eth_signTypedData on external dApps.
 */

(function () {
  let interceptedCounter = 0;

  function wrapProvider(provider) {
    if (!provider || provider.__txlens_wrapped) return provider;

    const originalRequest = provider.request ? provider.request.bind(provider) : null;
    if (!originalRequest) return provider;

    provider.request = async function (args) {
      if (!args || !args.method) return originalRequest(args);

      const method = args.method;

      // Intercept transaction and signature requests
      if (
        method === "eth_sendTransaction" ||
        method === "eth_signTypedData_v4" ||
        method === "eth_signTypedData"
      ) {
        const txParams = Array.isArray(args.params) ? args.params[0] : args.params;
        const requestId = `txlens-req-${Date.now()}-${++interceptedCounter}`;

        // Notify content script to display in-page Pop-Up Shield
        const shouldProceed = await new Promise((resolve) => {
          const detail = {
            id: requestId,
            method,
            params: txParams,
            origin: window.location.origin,
            title: document.title,
          };

          window.dispatchEvent(
            new CustomEvent("txlens:intercept-transaction", { detail })
          );

          // Handler for user decision from TxLens in-page pop-up
          function onDecision(event) {
            if (event.detail && event.detail.id === requestId) {
              window.removeEventListener("txlens:decision", onDecision);
              resolve(event.detail.approved);
            }
          }

          window.addEventListener("txlens:decision", onDecision);

          // Fallback timeout (3 minutes)
          setTimeout(() => {
            window.removeEventListener("txlens:decision", onDecision);
            resolve(true); // Allow fallback if timeout
          }, 180000);
        });

        if (!shouldProceed) {
          throw new Error("Transaction rejected by TxLens Security Shield.");
        }
      }

      return originalRequest(args);
    };

    provider.__txlens_wrapped = true;
    return provider;
  }

  // Wrap window.ethereum when available
  if (window.ethereum) {
    wrapProvider(window.ethereum);
  } else {
    let currentEthereum = undefined;
    Object.defineProperty(window, "ethereum", {
      configurable: true,
      enumerable: true,
      get: () => currentEthereum,
      set: (val) => {
        currentEthereum = wrapProvider(val);
      },
    });
  }
})();
