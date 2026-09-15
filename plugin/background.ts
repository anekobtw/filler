import { registerAssocSearch } from "./linkedin";

registerAssocSearch();

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

let lastPageTabId: number | undefined;

async function rememberActivePage(tabId: number): Promise<void> {
  const tab = await browser.tabs.get(tabId);
  if (tab.url && !tab.url.startsWith("http://127.0.0.1/")) lastPageTabId = tab.id;
}

function isAutofillRequest(message: unknown, sender: ExtensionMessageSender): message is { type: "autofill-request"; url: string } {
  if (
    typeof message !== "object" || message === null || !("type" in message) ||
    message.type !== "autofill-request" || !("url" in message) || typeof message.url !== "string" ||
    sender.tab?.url !== message.url
  ) return false;
  try {
    const url = new URL(message.url);
    return url.protocol === "http:" && url.hostname === "127.0.0.1" &&
      /^\d+$/.test(url.port) && /^\/autofill\/[A-Za-z0-9_-]{43}$/.test(url.pathname);
  } catch {
    return false;
  }
}

browser.tabs.onActivated.addListener(({ tabId }) => {
  void rememberActivePage(tabId);
});
void browser.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
  if (tab?.id !== undefined) return rememberActivePage(tab.id);
});

browser.runtime.onMessage.addListener(async (message: unknown, sender: ExtensionMessageSender) => {
  if (!isAutofillRequest(message, sender) || lastPageTabId === undefined) return;
  try {
    const response = await fetch(message.url, { cache: "no-store" });
    const command: unknown = await response.json();
    if (
      typeof command === "object" && command !== null && "type" in command &&
      command.type === "autofill" && "token" in command && typeof command.token === "string" &&
      message.url.endsWith(`/${command.token}`)
    ) await fillAllFrames(lastPageTabId);
  } catch {
    // The one-use TUI server has expired or the request was malformed.
  }
});
