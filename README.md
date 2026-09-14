# Resume Filler

A Firefox Manifest V3 extension that fills blank resume form inputs and native `<select>` controls from answers saved in the extension.

## Configure

Open the extension from Firefox's toolbar. On first use, the form imports values from `resume.config.json`; thereafter it uses saved browser answers. Update the questions and select **Save**. Answers are stored only in the browser profile. **Reset** clears every saved answer, and **Autofill page** fills the active tab.

Each answer maps to keywords matched against an element's label, `name`, `id`, placeholder, autocomplete token, and ARIA label. The education date questions distinguish ISO date inputs from numeric year fields. The degree and month answers can select compatible, longer native-select options.


## Outreach tools

Install [pipx](https://pipx.pypa.io/), then install this repository once from its root:

```sh
pipx install .
```

Open a new terminal if `pipx` asks you to update `PATH`.

### Find associations

```sh
assoc
```

`assoc` prompts for the company and optionally an applicant LinkedIn URL. Leaving the URL blank uses the value from the root `resume.config.json`.

It searches publicly indexed LinkedIn profiles and ranks results whose search snippets match the applicant's configured association signals. Results are discovery leads; verify profile details before outreach.

### Preview and send cold emails

Create a recipients JSON file:

```json
[
  {
    "first_name": "Ada",
    "email": "ada@example.com",
    "company_name": "Company name",
    "connection": "attended the same university"
  }
]
```

Run `cold-email` and provide the recipients JSON path when prompted:

```sh
cold-email
```

It always loads the root `cold-email.txt` template and uses the configured default subject. Enter a resume attachment path and confirm sending when prompted; otherwise it previews personalized messages without sending.

To send, set SMTP credentials before launching:

```sh
export SMTP_HOST="smtp.example.com"
export SMTP_USERNAME="your-email@example.com"
export SMTP_PASSWORD="app-password"
cold-email
```

`cold-email` sends one personalized message per recipient. The sender address comes from `resume.config.json`. `SMTP_PORT` defaults to `587`; `SMTP_SECURITY` defaults to `starttls` and may be `ssl` or `none`.

## Build and load

```sh
npm install
npm run build
```

In Firefox, open `about:debugging#/runtime/this-firefox`, choose **Load Temporary Add-on**, then select `dist/manifest.json`. Open the extension from the toolbar, save your answers, then select **Autofill page**. Embedded application forms, including the Greenhouse form on Old Mission Capital's careers page, are filled too. Passwords, file controls, checkboxes, radio buttons, hidden fields, and disabled/read-only controls are never changed.