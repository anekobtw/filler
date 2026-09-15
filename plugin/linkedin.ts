export interface AssocQuery {
  keywords: string;
  direct: boolean;
}

export interface AssocResult {
  name: string;
  url: string;
  snippet: string;
  direct: boolean;
}

type PageResult =
  | { status: "pending" }
  | { status: "error"; error: string }
  | {
      status: "ready";
      results: Omit<AssocResult, "direct">[];
      hasNext: boolean;
    };

const signInHelp = "Sign into LinkedIn in Firefox, complete any security challenge, and retry.";

export function validateAssocJob(value: unknown): AssocQuery[] {
  if (
    typeof value !== "object" || value === null ||
    !("queries" in value) || !Array.isArray(value.queries) ||
    value.queries.length < 1 || value.queries.length > 2
  ) {
    throw new Error("Invalid assoc search job: expected one or two queries.");
  }
  return value.queries.map((query: unknown) => {
    if (
      typeof query !== "object" || query === null ||
      !("keywords" in query) || typeof query.keywords !== "string" ||
      query.keywords.trim().length === 0 || query.keywords.length > 500 ||
      /[\u0000-\u001f\u007f]/.test(query.keywords) ||
      !("direct" in query) || typeof query.direct !== "boolean"
    ) {
      throw new Error("Invalid assoc search job: malformed keywords or direct flag.");
    }
    return { keywords: query.keywords.trim(), direct: query.direct };
  });
}

export function linkedInSearchUrl(query: AssocQuery, page: number): string {
  const url = new URL("https://www.linkedin.com/search/results/people/");
  url.searchParams.set("keywords", query.keywords);
  if (query.direct) url.searchParams.set("network", JSON.stringify(["F"]));
  url.searchParams.set("page", String(page));
  return url.href;
}

// Self-contained: Firefox serializes this function into the isolated page world.
export function extractLinkedInPage(): PageResult {
  const help = "Sign into LinkedIn in Firefox, complete any security challenge, and retry.";
  const text = document.body?.innerText ?? document.body?.textContent ?? "";
  if (
    /\/(?:login|uas|authwall|checkpoint|challenge)(?:\/|$)/i.test(location.pathname) ||
    document.querySelector('form[action*="login"], input[type="password"], iframe[src*="captcha"], iframe[src*="challenge"]') ||
    /(?:security verification|verify your identity|let.s do a quick security check|sign in to (?:linkedin|view))/i.test(text)
  ) {
    return { status: "error", error: help };
  }
  const isLinkedInHost = location.hostname === "linkedin.com" || location.hostname.endsWith(".linkedin.com");
  const isPeopleSearch = location.pathname.replace(/\/+$/, "") === "/search/results/people";
  if (!isLinkedInHost || !isPeopleSearch) {
    return { status: "error", error: `LinkedIn did not open the people search. ${help}` };
  }
  if (/(?:something went wrong|temporarily unavailable|too many requests|commercial use limit|search limit|try again later)/i.test(text)) {
    return { status: "error", error: "LinkedIn search is unavailable or rate-limited. Check LinkedIn in Firefox and retry later." };
  }

  const main = document.querySelector("main") ?? document;
  const cards = new Set<Element>(main.querySelectorAll(
    'li.reusable-search__result-container, .entity-result, [data-chameleon-result-urn], [data-view-name="search-entity-result-universal-template"], [data-view-name="people-search-result"]',
  ));
  // Some LinkedIn layouts replace entity-result classes with semantic list items.
  for (const anchor of main.querySelectorAll('a[href*="/in/"]')) {
    const card = anchor.closest('li, article, [role="listitem"]');
    if (card) cards.add(card);
  }
  const results: Omit<AssocResult, "direct">[] = [];
  const seen = new Set<string>();
  for (const card of cards) {
    const anchors = card.querySelectorAll<HTMLAnchorElement>('a[href*="/in/"]');
    for (const anchor of anchors) {
      let url: URL;
      try {
        url = new URL(anchor.href, location.href);
      } catch {
        continue;
      }
      if (
        url.protocol !== "https:" ||
        !(url.hostname === "linkedin.com" || url.hostname.endsWith(".linkedin.com")) ||
        !/^\/in\/[^/]+\/?$/.test(url.pathname)
      ) continue;
      const nameElement = anchor.querySelector('[aria-hidden="true"]') ?? anchor;
      const name = (nameElement instanceof HTMLElement ? nameElement.innerText : nameElement.textContent ?? "")
        .split("\n")[0].replace(/\s*[•·]\s*(?:1st|2nd|3rd\+?).*$/, "").trim();
      if (!name || /^(?:view|visit)\s+(?:profile|.+profile)$/i.test(name)) continue;
      const profileUrl = `https://www.linkedin.com${url.pathname.replace(/\/$/, "")}/`;
      if (!seen.has(profileUrl)) {
        seen.add(profileUrl);
        results.push({
          name: name.slice(0, 300),
          url: profileUrl,
          snippet: (card instanceof HTMLElement ? card.innerText : card.textContent ?? "")
            .replace(/\s+/g, " ").trim().slice(0, 2000),
        });
      }
      break;
    }
  }
  if (results.length > 0) {
    const next = main.querySelector<HTMLButtonElement>('button[aria-label="Next"], button.artdeco-pagination__button--next');
    return {
      status: "ready",
      results,
      // Missing pagination can mean lazy rendering; a bounded next URL is safe.
      hasNext: !next || (!next.disabled && next.getAttribute("aria-disabled") !== "true"),
    };
  }
  if (/(?:no results found|no results for|we (?:couldn.t|could not) find any results|no matching results|no people found)/i.test(text)) {
    return { status: "ready", results: [], hasNext: false };
  }
  return { status: "pending" };
}

async function waitForLinkedInPage(tabId: number): Promise<Extract<PageResult, { status: "ready" }>> {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    const tab = await browser.tabs.get(tabId);
    if (tab.status === "complete" && tab.url) {
      let url: URL;
      try {
        url = new URL(tab.url);
      } catch {
        throw new Error(`LinkedIn redirected or blocked the search. ${signInHelp}`);
      }
      if (!(url.hostname === "linkedin.com" || url.hostname.endsWith(".linkedin.com"))) {
        if (url.protocol !== "about:") {
          throw new Error(`LinkedIn redirected or blocked the search. ${signInHelp}`);
        }
      } else {
        const [injection] = await browser.scripting.executeScript({
          target: { tabId },
          world: "ISOLATED",
          func: extractLinkedInPage,
        });
        if (injection?.error) throw new Error(`Cannot read LinkedIn search: ${String(injection.error)}. ${signInHelp}`);
        const page = injection?.result;
        if (page?.status === "error") throw new Error(page.error);
        if (page?.status === "ready") return page;
      }
    }
    // Promise.withResolvers is unavailable in the project's ES2022 / Firefox 121 target.
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`LinkedIn did not display result cards or an explicit empty result within 30 seconds. ${signInHelp}`);
}

export async function searchLinkedIn(queries: AssocQuery[]): Promise<AssocResult[]> {
  const existingTabs = await browser.tabs.query({ url: ["https://linkedin.com/*", "https://*.linkedin.com/*"] });
  const sessionTab = existingTabs.find((tab) => tab.active) ?? existingTabs[0];
  const firstUrl = linkedInSearchUrl(queries[0], 1);
  const searchTab = await browser.tabs.create({
    url: firstUrl,
    active: true,
    // Firefox requires the cookies permission to select a container; no cookie API is used.
    ...(sessionTab?.cookieStoreId ? { cookieStoreId: sessionTab.cookieStoreId } : {}),
    ...(sessionTab?.windowId !== undefined ? { windowId: sessionTab.windowId } : {}),
  });
  if (searchTab.id === undefined) throw new Error("Firefox did not return a search tab ID.");
  const tabId = searchTab.id;
  try {
    const results: AssocResult[] = [];
    for (const [queryIndex, query] of queries.entries()) {
      // Keep direct and unrestricted searches distinct so relationship evidence survives.
      const seen = new Set<string>();
      for (let pageNumber = 1; pageNumber <= 3; pageNumber++) {
        const url = linkedInSearchUrl(query, pageNumber);
        if (queryIndex !== 0 || pageNumber !== 1) {
          await browser.tabs.update(tabId, { url });
        }
        const page = await waitForLinkedInPage(tabId);
        for (const result of page.results) {
          if (seen.has(result.url)) continue;
          seen.add(result.url);
          results.push({ ...result, direct: query.direct });
        }
        if (page.results.length === 0 || !page.hasNext) break;
      }
    }
    return results;
  } finally {
    // The user may already have closed this tab. Never remove any existing tab.
    await browser.tabs.remove(tabId).catch(() => undefined);
  }
}

export function validateAssocHandoff(message: unknown, sender: ExtensionMessageSender): string | undefined {
  if (
    typeof message !== "object" || message === null ||
    !("type" in message) || message.type !== "assoc-search" ||
    !("url" in message) || typeof message.url !== "string" ||
    !Number.isInteger(sender.tab?.id) || (sender.tab?.id ?? -1) < 0 ||
    sender.frameId !== 0 || sender.id !== browser.runtime.id ||
    sender.url !== message.url
  ) return;
  try {
    const url = new URL(message.url);
    if (
      url.protocol !== "http:" || url.hostname !== "127.0.0.1" ||
      !/^\d+$/.test(url.port) || Number(url.port) < 1 ||
      url.username || url.password || url.search || url.hash ||
      !/^\/assoc\/[A-Za-z0-9_-]{43}$/.test(url.pathname) ||
      url.href !== message.url
    ) return;
    return url.href;
  } catch {
    return;
  }
}

async function runAssocHandoff(baseUrl: string): Promise<{ status: "complete" } | { error: string }> {
  let accepted = false;
  const post = async (body: { results: AssocResult[] } | { error: string }): Promise<void> => {
    const response = await fetch(`${baseUrl}/result`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "omit",
      redirect: "error",
      signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) throw new Error(`Assoc CLI rejected the result (HTTP ${response.status}).`);
  };
  try {
    const response = await fetch(`${baseUrl}/job`, {
      credentials: "omit",
      redirect: "error",
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) throw new Error(`Cannot claim assoc job (HTTP ${response.status}). Restart assoc and retry.`);
    accepted = true;
    const queries = validateAssocJob(await response.json());
    const results = await searchLinkedIn(queries);
    accepted = false;
    await post({ results });
    return { status: "complete" };
  } catch (cause) {
    const error = cause instanceof Error ? cause.message : String(cause);
    if (accepted) {
      try {
        await post({ error });
      } catch (deliveryError) {
        return { error: `${error} Could not notify assoc CLI: ${deliveryError instanceof Error ? deliveryError.message : String(deliveryError)}` };
      }
    }
    return { error };
  }
}

export function registerAssocSearch(): void {
  browser.runtime.onMessage.addListener((message, sender) => {
    const baseUrl = validateAssocHandoff(message, sender);
    if (baseUrl) return runAssocHandoff(baseUrl);
  });
}
