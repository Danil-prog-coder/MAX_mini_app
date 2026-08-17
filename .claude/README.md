# Claude Code configuration

## superpowers plugin

`settings.json` enables [superpowers](https://github.com/obra/superpowers) by
Jesse Vincent (MIT) for anyone working in this repository.

It is installed from Anthropic's official marketplace
(`anthropics/claude-plugins-official`), which is the channel the plugin's own
README recommends first for Claude Code. That marketplace entry pins the plugin
to a specific upstream commit rather than tracking a moving branch — v6.3.0 is
commit `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` of `obra/superpowers`.

It adds 14 model-invoked skills (~688 tokens always-on):

| Skill | Purpose |
| --- | --- |
| `using-superpowers` | Entry point — how the rest of the skills fit together |
| `brainstorming` | Turn a vague idea into a concrete spec before coding |
| `writing-plans` | Write an implementation plan a fresh agent can execute |
| `executing-plans` | Work through an existing plan phase by phase |
| `test-driven-development` | Strict RED → GREEN → REFACTOR loop |
| `systematic-debugging` | Root-cause a bug instead of guessing at fixes |
| `verification-before-completion` | Prove the work is done before claiming it |
| `requesting-code-review` | Ask for a review with the right context |
| `receiving-code-review` | Work through review feedback |
| `subagent-driven-development` | Delegate implementation to subagents |
| `dispatching-parallel-agents` | Fan work out across several agents at once |
| `using-git-worktrees` | Isolate work in a git worktree |
| `finishing-a-development-branch` | Land or clean up a branch |
| `writing-skills` | Author new skills |

The plugin also ships a `SessionStart` hook (harness-side, no context cost).

### First run on a new machine or container

Claude Code registers the official marketplace on its own, but a plugin from an
external source is installed on demand. If the skills are missing, run:

```bash
claude plugin install superpowers@claude-plugins-official
```

Then `/reload-plugins` in an open session, or just start a new one.

### Removing it

Delete the `enabledPlugins` entry from `settings.json`, and run
`claude plugin uninstall superpowers@claude-plugins-official`.
