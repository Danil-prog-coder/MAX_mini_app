# Claude Code configuration

## superpowers plugin

`settings.json` registers the [superpowers](https://github.com/obra/superpowers)
marketplace (`obra/superpowers`) and enables the `superpowers` plugin for anyone
working in this repository.

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

Claude Code adds the marketplace automatically once the repository folder is
trusted, but a plugin from an external source is installed on demand. If the
skills are missing, run:

```bash
claude plugin install superpowers@superpowers-dev
```

Then `/reload-plugins` in an open session, or just start a new one.

### Removing it

Delete the `extraKnownMarketplaces` and `enabledPlugins` entries from
`settings.json`, and run `claude plugin uninstall superpowers@superpowers-dev`.
