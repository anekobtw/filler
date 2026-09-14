function setAssocStatus(message: string): void {
  const status = document.getElementById("assoc-status");
  if (status) status.textContent = message;
}

if (
  window === window.top &&
  location.protocol === "http:" &&
  location.hostname === "127.0.0.1" &&
  /^\d+$/.test(location.port) &&
  /^\/assoc\/[A-Za-z0-9_-]{43}$/.test(location.pathname) &&
  !location.search && !location.hash
) {
  setAssocStatus("Searching LinkedIn using your signed-in Firefox session. Keep Firefox open; results will appear in assoc.");
  void browser.runtime.sendMessage({ type: "assoc-search", url: location.href }).then(
    (response: unknown) => {
      if (typeof response === "object" && response !== null && "error" in response && typeof response.error === "string") {
        setAssocStatus(`LinkedIn search failed: ${response.error}`);
      } else if (typeof response === "object" && response !== null && "status" in response && response.status === "complete") {
        setAssocStatus("LinkedIn search complete. Return to assoc for the results. You may close this handoff tab.");
      } else {
        setAssocStatus("The extension did not accept the assoc handoff. Reload the extension and restart assoc to retry.");
      }
    },
    (error: unknown) => {
      setAssocStatus(`Could not contact the extension: ${error instanceof Error ? error.message : String(error)}. Reload the extension and restart assoc to retry.`);
    },
  );
}
