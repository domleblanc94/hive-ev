# Publish this repository yourself

The owner selected the public repository https://github.com/domleblanc94/hive-ev
on 4 November 2026. The following procedure also documents future releases. Do not add the larger investigation workspace
or any extracted Hive application files to it.

The working folder also contains Git-ignored private material. Publish tracked
Git content, or use the generated clean source archive for a web upload. Do not
drag the whole working folder into GitHub: a web upload does not inherit the
local Git ignore protection.

## Review before publishing

Read the code, [development record](docs/development-and-provenance.md) and
[validation limits](docs/testing.md). The current community release is **0.2.0**, with monitoring and optional default-off experimental
manual controls. End session may require reconnection; Pause/resume, unattended
control and automatic overnight readiness are not established.
The implementation and tests were generated with OpenAI Codex; AI-agent review is
not a substitute for your own understanding or a human security audit.

Run the checks in [CONTRIBUTING.md](CONTRIBUTING.md). Before pushing, inspect the
tracked files and diff using `git status` and `git show --stat HEAD`. Authentication
data and proprietary inspection files must remain outside the repository.

## Create the GitHub destination

Before a public release, obtain appropriate review of the implementation,
protocol documentation and embedded app-client configuration. This project has
not received legal clearance or permission from Hive. The UK's conditional
[interoperability decompilation exception](https://www.legislation.gov.uk/ukpga/1988/48/section/50B)
is not a blanket publishing licence: necessity and limits on use and disclosure
matter. This project does not determine that its specific facts satisfy that test.

Hive's [October 2026 consumer terms](https://assets.ctfassets.net/mijf9lz5yt3u/16Q4jaretKFDRef8fD8YTv/720ce72d1bd22d668f531270a4aba053/Hive_B2C_T_Cs_Update_19.10.2026.pdf),
section 11, restrict reverse engineering except where law permits it. That
qualification does not itself settle whether this project's work is permitted.
An original-code licence and Codex attribution do not grant rights to Hive's app
or service. A qualified software/IP adviser should assess the applicable terms
and publication scope. This is a review note, not legal advice or a conclusion
that publication is lawful or unlawful. Sources checked 30 October 2026.

The service is also undocumented and may change or restrict third-party clients;
technical compatibility and legal permission are separate questions.

For a new fork, create an empty repository in your own GitHub account. Choose its visibility and
name yourself. Do not initialize another README, licence or gitignore there: this
local repository already includes them. Follow GitHub's instructions for connecting
an existing repository, using the actual URL GitHub gives you:

```text
git remote add origin <YOUR_ACTUAL_GITHUB_REPOSITORY_URL>
git push -u origin main
```

The angle-bracketed text is a placeholder for forks; this project uses
https://github.com/domleblanc94/hive-ev. If you already configured an origin, inspect
it before changing anything rather than blindly adding or replacing it.

The manifest documentation and issue links point to this project. Forks must
update those links to their actual destination and verify them. Do not invent
maintainer identities, endorsement or HACS availability.

Build the clean installation ZIP (`hive-ev-0.2.0.zip`) with `python tools/build_integration_package.py`
if you want to attach it to a GitHub release. The generated `dist/` directory is
ignored by Git. Do not upload APKs, decompiled code, raw diagnostic responses or
personal screenshots as release attachments.

## Publish a release

After review, publish the actual reviewed commit and create a GitHub release for
version 0.2.0 as a normal release. Future beta tags must be marked as pre-releases; normal releases must not. Use CHANGELOG.md and the
release notes supplied with the review artifacts. Attach the clean installation
ZIP and SHA-256 checksums; attach the source archive separately if useful. This
repository does not automatically publish releases. A hosted CI run, when executed,
is separate from the local checks and must not be claimed before it runs.

Check the install archive contains controls/diagnostics modules and public
documents, but no tests, private research, diagnostics files, app material or
account data. Warn upgraders to disable experimental controls first because
existing entry options are retained. Mark the narrow End-session and one-trial
limits prominently. Do not describe a normal release as universal charger support or remove the experimental control labels without new evidence.

## Home Assistant Core is a separate contribution

The upstream implementation uses the existing Hive integration and its Python
client library. It is not this custom component copied into Core. See the
[contribution plan](docs/upstream-contribution-plan.md) and the prepared upstream
branches when available. A compatible published library release and the target
project's full checks are prerequisites for a merge-ready Core contribution.

Submit any upstream PR yourself after reviewing and understanding the complete
change. Retain the upstream template and leave human-review declarations unchecked
until you can truthfully make them. The PR description should disclose Codex's
role and distinguish real-device observations from synthetic tests.

References: GitHub's [new repository instructions](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
and [publishing existing local code](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).

## HACS custom repository

Keep `hacs.json` at the repository root in every release. This project uses source-folder installation (`content_in_root: false`, `zip_release: false`) with one integration under custom_components/hive_ev, a declared HA minimum and an actual owner in manifest codeowners. The manually downloadable install ZIP is not the HACS input. Keep [the installation guide](docs/hacs-installation.md) synchronized with releases. This project has not been submitted to the default HACS catalog or the Home Assistant brands repository.
