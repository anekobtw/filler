# Resume Filler

Resume Filler is a Firefox Manifest V3 extension plus a keyboard-first terminal command center for preparing and autofilling job-application forms.

The extension fills empty `input`, `textarea`, and native `select` elements from `resume.config.json`. It also supports React-style comboboxes. Rules match an element's label, `name`, `id`, placeholder, autocomplete token, and ARIA labels. The packaged configuration contains common personal, education, work-authorization, and voluntary self-identification fields.

## Requirements

- Firefox
- Node.js 22 and npm
- Python 3.11–3.13
- [pipx](https://pipx.pypa.io/) for the `filler` command

## Set up

Create your local configuration from the committed example:

```sh
cp resume.config.example.json resume.config.json
```

Install the terminal command once from the repository root:

```sh
pipx install --editable .
```

Open a new terminal if `pipx` asks you to add its bin directory to `PATH`.

Install the JavaScript build dependencies:

```sh
npm ci
```

## Use the command center

Run the command from the directory containing your `resume.config.json`:

```sh
filler
```

Navigate with the arrow keys or `j`/`k`, select with Enter, and quit with `q` or Esc. It provides four actions:

- **Build and load into Firefox** — runs `npm run build` and opens Firefox's temporary-add-on page. In Firefox, choose **Load Temporary Add-on**, then select `dist/manifest.json`; temporary add-ons must be loaded again after Firefox restarts.
- **Change your info** — edits and saves the fields in `resume.config.json`.
- **Autofill the open page** — sends a one-use local request to the extension, which fills the active non-local Firefox tab and its frames.
- **Search top 10 company connections** — searches LinkedIn through the loaded extension, using your configured school, location, organization, and `associationSignals` values.

`resume.config.json` is bundled into the extension at build time. After **Change your info**, select **Build and load into Firefox** again to package the updated answers.

For LinkedIn search, sign in to LinkedIn in the same Firefox profile and complete any security challenge before running the action. Results are search candidates, not verified relationships.

## Autofill behavior

By default, Resume Filler leaves existing values intact. Set `"overwriteExisting": true` in `resume.config.json` to replace values. It never fills disabled or read-only controls, passwords, file inputs, checkboxes, radio buttons, hidden inputs, or buttons.

Native select values are matched exactly where possible. Degree and month rules allow partial matching to accommodate longer option labels.

## Configuration

`resume.config.json` contains:

- `overwriteExisting` — whether autofill may replace existing values.
- `associationSignals` — optional strings used to broaden the LinkedIn shared-association query.
- `fields` — rules with `keywords` and a `value`; optional `inputTypes`, `priority`, and `selectPartialMatch` refine matching.

Keep `resume.config.json` private; it is ignored by Git. Start from `resume.config.example.json` when sharing or recreating configuration.

## Contributing

Contributions are welcome. For substantial changes, open an issue first to agree on the direction; then submit a focused pull request with any necessary documentation updates. Before opening the pull request, run `poetry check --lock`, `poetry build --output /tmp/resume-filler-python-dist`, `npm run typecheck`, and `npm run build`. Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

This project is licensed under the [MIT License](LICENSE).

