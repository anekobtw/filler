# Resume Filler

A Firefox Manifest V3 extension that fills blank resume form inputs and native `<select>` controls from answers saved in the extension.

## Configure

Open the extension from Firefox's toolbar. On first use, the form imports values from `resume.config.json`; thereafter it uses saved browser answers. Update the questions and select **Save**. Answers are stored only in the browser profile. **Reset** clears every saved answer, and **Autofill page** fills the active tab.

Each answer maps to keywords matched against an element's label, `name`, `id`, placeholder, autocomplete token, and ARIA label. The education date questions distinguish ISO date inputs from numeric year fields. The degree and month answers can select compatible, longer native-select options.


## Outreach tools

Install [pipx](https://pipx.pypa.io/), then install this repository once from its root:

```sh
pipx install --editable .
```

Open a new terminal if `pipx` asks you to update `PATH`.

### Find associations

```sh
assoc
```

`assoc` always searches LinkedIn using your existing Firefox login. First build and load the extension as described below. Keep your usual Firefox open and signed into LinkedIn; `assoc` opens a local handoff tab in that running browser. The extension uses an existing LinkedIn tab's Firefox container and window when one is open, opens a separate search tab, returns results to your terminal, and closes only the search tab it created. No Playwright, Chromium installation, password storage, cookie copying, or CSV export is used.

For Firefox containers, leave a LinkedIn tab open in the container holding your account. The extension prefers an active LinkedIn tab, otherwise the first open LinkedIn tab, and creates its search tab in that container and window. If no LinkedIn tab exists, it uses the default container. The `cookies` permission is required by Firefox to select a tab's `cookieStoreId`; the extension does not call the cookies API or read your cookies.

The CLI-to-extension handoff uses a one-use random URL on an ephemeral `127.0.0.1` port, expires after five minutes, and closes when the result arrives or you cancel. Only search queries and profile-card results pass through it. If the handoff page stays waiting, load or reload `dist/manifest.json` in `about:debugging#/runtime/this-firefox`, then reload the waiting page. If a search has already started or expired, restart `assoc` instead.

The search checks the signed-in account's first-degree connections for the company or university keywords, then searches people using those keywords together with the configured association signals. It reads up to three pages per query and displays up to 20 unique profiles with the search-card text. These are search leads, not verified employment histories or proof you personally know someone. The applicant URL is a label; it cannot grant access to that person's connections. LinkedIn login challenges, blocks, and unrecognized result pages are reported as failures rather than “no matches.” English LinkedIn UI is required for empty-state detection.


The root `resume.config.json` supplies school, location, and `associationSignals` such as employers, roles, and organizations. If upgrading a previously installed copy, run `pipx install --force --editable .`, rebuild the extension with `npm run build`, and reload it in Firefox. Temporary extensions must be loaded again after restarting Firefox.

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