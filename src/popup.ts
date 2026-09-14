import {
  blankConfig,
  currentConfig,
  questions,
  type ResumeConfig,
} from "./configuration";

const form = document.querySelector<HTMLFormElement>("#config-form")!;
const resetButton = document.querySelector<HTMLButtonElement>("#reset")!;
const fillButton = document.querySelector<HTMLButtonElement>("#fill")!;
const status = document.querySelector<HTMLOutputElement>("#status")!;

function render(config: ResumeConfig): void {
  for (const [index, question] of questions.entries()) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.name = String(index);
    input.type = question.type ?? "text";
    input.value = config.fields[index]?.value ?? "";
    input.autocomplete = "off";
    label.append(question.label, input);
    form.append(label);
  }
}
async function load(): Promise<void> {
  const { config } = await browser.storage.local.get("config");
  render(currentConfig(config));
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  void browser.storage.local.get("config").then(({ config: savedConfig }) => {
    const config = currentConfig(savedConfig);
    const formData = new FormData(form);
    for (const [index, field] of config.fields.entries()) {
      const value = formData.get(String(index));
      field.value = typeof value === "string" ? value.trim() : "";
    }
    return browser.storage.local.set({ config });
  }).then(() => {
    status.value = "Saved.";
  });
});

resetButton.addEventListener("click", () => {
  form.reset();
  void browser.storage.local.set({ config: blankConfig() }).then(() => {
    status.value = "Cleared.";
  });
});

fillButton.addEventListener("click", () => {
  void browser.runtime.sendMessage({ type: "autofill-active" }).then(() => {
    status.value = "Autofill requested.";
  });
});

void load();
