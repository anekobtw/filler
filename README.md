# Resume Filler

A Firefox Manifest V3 extension that fills blank resume form inputs and native `<select>` controls from answers saved in the extension.

## Configure

Open the extension from Firefox's toolbar. On first use, the form imports values from `src/resume.config.json`; thereafter it uses saved browser answers. Update the questions and select **Save**. Answers are stored only in the browser profile. **Reset** clears every saved answer, and **Autofill page** fills the active tab.

Each answer maps to keywords matched against an element's label, `name`, `id`, placeholder, autocomplete token, and ARIA label. The education date questions distinguish ISO date inputs from numeric year fields. The degree and month answers can select compatible, longer native-select options.

## Build and load

```sh
npm install
npm run build
```

In Firefox, open `about:debugging#/runtime/this-firefox`, choose **Load Temporary Add-on**, then select `dist/manifest.json`. Open the extension from the toolbar, save your answers, then select **Autofill page**. Embedded application forms, including the Greenhouse form on Old Mission Capital's careers page, are filled too. Passwords, file controls, checkboxes, radio buttons, hidden fields, and disabled/read-only controls are never changed.