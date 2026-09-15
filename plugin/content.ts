import {
  currentConfig,
  type FieldRule,
  type ResumeConfig,
} from "./configuration";

type FillableElement =
  | HTMLInputElement
  | HTMLTextAreaElement
  | HTMLSelectElement;

function isAutofillMessage(message: unknown): boolean {
  return (
    typeof message === "object" &&
    message !== null &&
    "type" in message &&
    message.type === "autofill"
  );
}

const elementSelector = "input, textarea, select";
const ignoredInputTypes: Record<string, true> = {
  button: true,
  checkbox: true,
  file: true,
  hidden: true,
  image: true,
  password: true,
  radio: true,
  reset: true,
  submit: true,
};

const genericMatchWords = new Set(["a", "an", "and", "degree", "of", "s", "the"]);

function normalize(value: string): string {
  return value
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function matchingOption<T>(
  options: Iterable<T>,
  value: string,
  textForOption: (option: T) => string,
  allowPartialMatch: boolean,
): T | undefined {
  const expected = normalize(value);
  const expectedWords = allowPartialMatch
    ? expected
        .split(" ")
        .filter((word) => word.length > 1 && !genericMatchWords.has(word))
    : [];
  let partial: T | undefined;
  let bestMatch: T | undefined;
  let bestScore = 0;

  for (const candidate of options) {
    const candidateText = normalize(textForOption(candidate));
    if (candidateText === expected) return candidate;
    if (!partial && candidateText.includes(expected)) partial = candidate;
    if (partial || !allowPartialMatch) continue;

    const candidateWords = candidateText
      .split(" ")
      .filter((word) => word.length > 1 && !genericMatchWords.has(word));
    const sharedWords = expectedWords.filter((word) =>
      candidateWords.includes(word),
    ).length;
    const score =
      sharedWords / Math.max(expectedWords.length, candidateWords.length);
    if (sharedWords > 0 && score > bestScore) {
      bestMatch = candidate;
      bestScore = score;
    }
  }

  return partial ?? bestMatch;
}


function textForElement(element: FillableElement): string {
  const fragments = [
    element.getAttribute("name"),
    element.id,
    element.getAttribute("placeholder"),
    element.getAttribute("autocomplete"),
    element.getAttribute("aria-label"),
  ];

  for (const label of Array.from(element.labels ?? [])) {
    fragments.push(label.textContent);
  }

  const wrapperLabel = element.closest("label");
  if (wrapperLabel) fragments.push(wrapperLabel.textContent);

  const labelledBy = element.getAttribute("aria-labelledby");
  if (labelledBy) {
    for (const id of labelledBy.split(/\s+/)) {
      fragments.push(document.getElementById(id)?.textContent ?? null);
    }
  }

  return normalize(
    fragments.filter((value): value is string => Boolean(value)).join(" "),
  );
}

function matchingRule(
  config: ResumeConfig,
  element: FillableElement,
): FieldRule | undefined {
  const fieldText = textForElement(element);
  const inputType =
    element instanceof HTMLInputElement
      ? element.type
      : element instanceof HTMLSelectElement
        ? "select"
        : "textarea";
  let winner: FieldRule | undefined;
  let winnerPriority = Number.NEGATIVE_INFINITY;
  let winnerScore = 0;

  for (const rule of config.fields) {
    if (rule.inputTypes && !rule.inputTypes.includes(inputType)) continue;
    const priority = rule.priority ?? 0;
    for (const keyword of rule.keywords) {
      const normalizedKeyword = normalize(keyword);
      if (
        normalizedKeyword &&
        fieldText.includes(normalizedKeyword) &&
        (priority > winnerPriority ||
          (priority === winnerPriority &&
            normalizedKeyword.length > winnerScore))
      ) {
        winner = rule;
        winnerPriority = priority;
        winnerScore = normalizedKeyword.length;
      }
    }
  }

  return winner;
}

function setNativeValue(
  element: HTMLInputElement | HTMLTextAreaElement,
  value: string,
): void {
  const prototype =
    element instanceof HTMLInputElement
      ? HTMLInputElement.prototype
      : HTMLTextAreaElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
  setter?.call(element, value);
  element.dispatchEvent(
    new InputEvent("input", {
      bubbles: true,
      composed: true,
      inputType: "insertText",
      data: value,
    }),
  );
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function setNativeSelectValue(element: HTMLSelectElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(
    HTMLSelectElement.prototype,
    "value",
  )?.set;
  setter?.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function fillSelect(
  element: HTMLSelectElement,
  value: string,
  allowPartialMatch: boolean,
): boolean {
  const option = matchingOption(
    element.options,
    value,
    (candidate) => `${candidate.value} ${candidate.textContent ?? ""}`,
    allowPartialMatch,
  );
  if (!option) return false;
  setNativeSelectValue(element, option.value);
  return true;
}

function canFill(config: ResumeConfig, element: FillableElement): boolean {
  if (
    element.disabled ||
    ((element instanceof HTMLInputElement ||
      element instanceof HTMLTextAreaElement) &&
      element.readOnly)
  )
    return false;
  if (element instanceof HTMLInputElement && ignoredInputTypes[element.type])
    return false;
  if (config.overwriteExisting) return true;
  return element instanceof HTMLSelectElement
    ? element.selectedIndex <= 0
    : element.value.trim() === "";
}


async function fillCombobox(
  element: HTMLInputElement,
  value: string,
  allowPartialMatch: boolean,
): Promise<boolean> {
  const control = element.closest<HTMLElement>("[class*='select__control']");
  const toggle = control?.querySelector<HTMLButtonElement>(
    "button[aria-label='Toggle flyout']",
  );
  toggle?.dispatchEvent(
    new MouseEvent("mousedown", {
      bubbles: true,
      cancelable: true,
      button: 0,
      view: window,
    }),
  );
  element.focus();
  setNativeValue(element, value);
  element.dispatchEvent(
    new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
  );
  element.dispatchEvent(
    new KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
  );
  await new Promise<void>((resolve) => window.setTimeout(resolve, 0));
  if (element.value === "") return true;
  const listboxId =
    element.getAttribute("aria-controls") ||
    (element.id ? `react-select-${element.id}-listbox` : null);
  const deadline = performance.now() + 2_000;
  let menu: HTMLElement | null = null;
  let options: HTMLElement[] = [];

  do {
    menu = listboxId ? document.getElementById(listboxId) : null;
    options = Array.from(
      menu?.querySelectorAll<HTMLElement>("[role='option']") ?? [],
    ).filter((candidate) => candidate.getAttribute("aria-disabled") !== "true");
    if (options.length > 0) break;
    await new Promise<void>((resolve) => window.setTimeout(resolve, 50));
  } while (performance.now() < deadline);

  const option = matchingOption(
    options,
    value,
    (candidate) => candidate.textContent ?? "",
    allowPartialMatch,
  );
  if (!option) return false;
  option.click();
  await new Promise<void>((resolve) => window.setTimeout(resolve, 0));
  return true;
}


async function fillElement(
  config: ResumeConfig,
  element: FillableElement,
): Promise<boolean> {
  if (!canFill(config, element)) return false;
  const rule = matchingRule(config, element);
  if (!rule) return false;

  if (element instanceof HTMLSelectElement)
    return fillSelect(element, rule.value, Boolean(rule.selectPartialMatch));
  if (
    element instanceof HTMLInputElement &&
    element.getAttribute("role") === "combobox"
  )
    return fillCombobox(element, rule.value, Boolean(rule.selectPartialMatch));
  setNativeValue(element, rule.value);
  return true;
}


async function fillDocument(config: ResumeConfig): Promise<number> {
  let filled = 0;
  for (const element of document.querySelectorAll<FillableElement>(
    elementSelector,
  )) {
    if (await fillElement(config, element)) filled += 1;
  }
  return filled;
}

async function storedConfig(): Promise<ResumeConfig> {
  const { config } = await browser.storage.local.get("config");
  return currentConfig(config);
}

browser.runtime.onMessage.addListener((message: unknown) => {
  if (!isAutofillMessage(message)) return;
  void storedConfig().then(fillDocument);
});
