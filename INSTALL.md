# Installing CTIS Skills

Choose your client first and run the two commands in order. The plugin id stays `ctis@ctis-skills` in both clients.

## Requirements

- GitHub access and a working `git` client.
- `claude` for Claude Code, or `codex` for Codex.
- A new client session opened after installation.

Check the version with `claude --version` or `codex --version`. If the command form does not appear in the local help, update the client through its own official distribution channel.

## Claude Code

1. Add the marketplace.

   ```text
   claude plugin marketplace add onurcangnc/ctis_skills
   ```

2. Install the plugin.

   ```text
   claude plugin install ctis@ctis-skills
   ```

## Codex

1. Add the `main` branch of the marketplace.

   ```text
   codex plugin marketplace add onurcangnc/ctis_skills --ref main
   ```

2. Install the plugin.

   ```text
   codex plugin add ctis@ctis-skills
   ```

## Verify and invoke

Check the installed list with `claude plugin list` or `codex plugin list`. Open a new session after installing; invoke `/ctis` in Claude Code and `$ctis` in Codex. If an open session does not see the new plugin, close and restart the client.

## Update

Claude Code:

```text
claude plugin marketplace update ctis-skills
claude plugin update ctis@ctis-skills
```

Claude's help output states that applying an update needs a restart.

Codex:

```text
codex plugin marketplace upgrade ctis-skills
codex plugin remove ctis@ctis-skills
codex plugin add ctis@ctis-skills
```

Codex refreshes the marketplace; the remove and add rebuild the installed copy from the new snapshot.

## Uninstall

Claude Code:

```text
claude plugin uninstall ctis@ctis-skills
```

Codex:

```text
codex plugin remove ctis@ctis-skills
```

If you also want to remove the marketplace record, first check the name form in the `plugin marketplace remove --help` output of the relevant client.

## Installing from local packages

Three files live in the distribution directory: [ctis.skill](dist/ctis.skill), [ctis-codex-plugin.zip](dist/ctis-codex-plugin.zip), and [ctis-claude-plugin.zip](dist/ctis-claude-plugin.zip).

For Claude Code, extract `ctis-claude-plugin.zip`. Add the unpacked `ctis` directory as a local marketplace source, then run the normal `ctis@ctis-skills` install. For Codex, `ctis-codex-plugin.zip` is a portable plugin tree. If you need only the skill without a marketplace, open `ctis.skill` as a ZIP and copy the `ctis` directory inside into the local skills root used by your Codex configuration.

Before installing a local package, compare the SHA-256 value in the README using `Get-FileHash -Algorithm SHA256` or `sha256sum`. Do not rename the archive root; the relative skill path in the manifests depends on it.

## Troubleshooting

1. If `ctis@ctis-skills` is not found, check the marketplace list and update the marketplace.
2. If the invocation does not appear, open a new session; for a Claude update, restart the client.
3. If the local ZIP is rejected, extract the archive and select the inner `ctis` root as the source.
4. If the hash mismatches, do not use the file; download the published package again.
5. If behavior diverges, run the [examples/index.json](examples/index.json) records in both clients with the same prompt and add the client version to the issue.