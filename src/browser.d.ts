interface ExtensionTab {
  id?: number;
  active?: boolean;
  url?: string;
  status?: string;
  cookieStoreId?: string;
  windowId?: number;
}

interface ExtensionFrame {
  frameId: number;
}

interface ExtensionMessageSender {
  id?: string;
  tab?: ExtensionTab;
  frameId?: number;
  url?: string;
}

type StoredValues = Record<string, unknown>;

declare const browser: {
  action: {
    onClicked: {
      addListener(listener: (tab: ExtensionTab) => void): void;
    };
  };
  webNavigation: {
    getAllFrames(details: { tabId: number }): Promise<ExtensionFrame[]>;
  };
  tabs: {
    query(queryInfo: { active?: boolean; currentWindow?: boolean; url?: string | string[] }): Promise<ExtensionTab[]>;
    get(tabId: number): Promise<ExtensionTab>;
    create(properties: { url: string; active: boolean; cookieStoreId?: string; windowId?: number }): Promise<ExtensionTab>;
    update(tabId: number, properties: { url: string }): Promise<ExtensionTab>;
    remove(tabId: number): Promise<void>;
    sendMessage(tabId: number, message: unknown, options?: { frameId: number }): Promise<unknown>;
  };
  scripting: {
    executeScript<T>(injection: {
      target: { tabId: number };
      world: "ISOLATED";
      func: () => T;
    }): Promise<{ result?: Awaited<T>; error?: unknown }[]>;
  };
  storage: {
    local: {
      get(key: string): Promise<StoredValues>;
      set(items: StoredValues): Promise<void>;
      remove(key: string): Promise<void>;
    };
  };
  runtime: {
    id: string;
    onMessage: {
      addListener(listener: (message: unknown, sender: ExtensionMessageSender) => void | Promise<unknown>): void;
    };
    sendMessage(message: unknown): Promise<unknown>;
  };
};
