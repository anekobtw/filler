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

browser.action.onClicked.addListener((tab) => {
  if (tab.id !== undefined) void fillAllFrames(tab.id);
});
