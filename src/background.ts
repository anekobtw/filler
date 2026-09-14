async function fillAllFrames(tabId: number): Promise<void> {
  const frames = await browser.webNavigation.getAllFrames({ tabId });
  await Promise.all(
    frames.map(async ({ frameId }) => {
      try {
        await browser.tabs.sendMessage(tabId, { type: "autofill" }, { frameId });
      } catch {
        // The frame can navigate between enumeration and delivery.
      }
    })
  );
}

function isAutofillActiveMessage(message: unknown): boolean {
  return (
    typeof message === "object" &&
    message !== null &&
    "type" in message &&
    message.type === "autofill-active"
  );
}

browser.runtime.onMessage.addListener((message: unknown) => {
  if (!isAutofillActiveMessage(message)) return;
  void browser.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
    if (tab?.id !== undefined) return fillAllFrames(tab.id);
  });
});
