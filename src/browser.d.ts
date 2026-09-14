interface ExtensionTab {
  id?: number;
}

interface ExtensionFrame {
  frameId: number;
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
    query(queryInfo: { active: boolean; currentWindow: boolean }): Promise<ExtensionTab[]>;
    sendMessage(tabId: number, message: unknown, options?: { frameId: number }): Promise<unknown>;
  };
  storage: {
    local: {
      get(key: string): Promise<StoredValues>;
      set(items: StoredValues): Promise<void>;
      remove(key: string): Promise<void>;
    };
  };
  runtime: {
    onMessage: {
      addListener(listener: (message: unknown) => void): void;
    };
    sendMessage(message: unknown): Promise<unknown>;
  };
};
