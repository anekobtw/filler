interface ExtensionTab {
  id?: number;
}

interface ExtensionFrame {
  frameId: number;
}

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
    sendMessage(tabId: number, message: unknown, options?: { frameId: number }): Promise<unknown>;
  };
  runtime: {
    onMessage: {
      addListener(listener: (message: unknown) => void): void;
    };
  };
};
