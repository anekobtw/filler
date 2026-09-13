# Resume Filler

A Firefox Manifest V3 extension that fills blank resume form inputs and native `<select>` controls from local keyword rules when you press its toolbar button.

## Configure

Create your local configuration from the committed template, then edit only the local copy:

```sh
cp src/resume.config.example.json src/resume.config.json
```

`src/resume.config.json` is ignored by Git because it contains personal data. Each field maps one value to keywords matched against an element's label, `name`, `id`, placeholder, autocomplete token, and ARIA label. `inputTypes` restricts a rule to compatible controls: the supplied education date rules use it to distinguish ISO date inputs from numeric year fields. `priority` resolves overlapping matches; a higher value wins before keyword length is considered. `selectPartialMatch` is enabled for the degree rule so a generic value such as `Bachelor's Degree` can choose a compatible option such as `Bachelor of Science`. Set `overwriteExisting` to `true` only when existing form values should be replaced.

## Build and load

```sh
npm install
npm run build
```

In Firefox, open `about:debugging#/runtime/this-firefox`, choose **Load Temporary Add-on**, then select `dist/manifest.json`. Open an application page and press the **Autofill this website** toolbar button to fill matching blank fields. Embedded application forms, including the Greenhouse form on Old Mission Capital's careers page, are filled too. Passwords, file controls, checkboxes, radio buttons, hidden fields, and disabled/read-only controls are never changed.