# wardenIQ roadmap

wardenIQ is beta and moving fast. This is what we're building and, more usefully, **where
you can help**. Everything here is tracked as a GitHub issue — the roadmap is the narrative,
the issues are the work.

> **New here?** The [good first issues](https://github.com/adlerqa/wardeniq/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
> each carry context, acceptance criteria and pointers to the relevant files. Start there.

## How to pick something up

1. **Comment on the issue to claim it** before you start. We've already had two people
   independently solve the same issue — that's our fault for not saying this, and it wastes
   real effort. One comment avoids it.
2. Ask questions in the issue. A clarifying question is always cheaper than a rewrite.
3. Open a draft PR early if it's substantial. Direction feedback beats a surprise at review.
4. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the dev loop. The whole stack runs in Docker
   Compose; you don't need Python, Node or MongoDB installed locally.

---

## Now — [v0.2: First run & trust](https://github.com/adlerqa/wardeniq/milestone/1)

The two things that decide whether wardenIQ gets adopted: **does it work in the first five
minutes**, and **can you trust what it generates**. Everything here beats every feature below.

**Trust.** [#36](https://github.com/adlerqa/wardeniq/issues/36) is the most important open
issue in the project: generation can emit the prompt's own few-shot examples verbatim as real
test cases, attributed to your feature, with a high confidence score. Grounded output is the
entire value proposition — a hallucinated case doesn't fail loudly, it sits in the suite
looking legitimate and inflates your coverage. Fixing this matters more than any integration.

**First run.** [#27](https://github.com/adlerqa/wardeniq/issues/27) — the bundled stack can't
start on Docker Desktop with a kernel ≥ 6.19, and `run.sh` exits 0 while it fails. A new user
gets a success-looking run and a dead `localhost:8001`.

Also in scope: the boot banner covering the header including Sign out
([#34](https://github.com/adlerqa/wardeniq/issues/34)), README screenshots and a demo GIF
([#11](https://github.com/adlerqa/wardeniq/issues/11)) — the README currently has no images at
all — an example PRD so a first run needs no document of your own
([#12](https://github.com/adlerqa/wardeniq/issues/12)), and the first tagged release
([#18](https://github.com/adlerqa/wardeniq/issues/18)).

## Next — Integrations

Two epics. Both need machine authentication first:
**[#37 — service accounts and API tokens](https://github.com/adlerqa/wardeniq/issues/37)**.
A CI job or a Jira app can't hold a session cookie. The extension point for this is already
designed and documented in `app/core/security.py` and currently unused, so it's a
well-scoped, high-leverage piece of backend work that unblocks everything below.

### [Jira app](https://github.com/adlerqa/wardeniq/milestone/2) — [#38](https://github.com/adlerqa/wardeniq/issues/38)

Drive wardenIQ from inside Jira: open a ticket, generate a grounded test suite from what the
ticket already contains, see coverage without leaving the issue view.

We already pull *from* Jira (`app/jira.py`, plus issue/epic/Confluence access and a webhook).
What's missing is a surface *inside* Jira.

The competitor is Atlassian Rovo, and the differentiator is not "AI in Jira" — Rovo has that.
It's that our output is **grounded and traceable**: every case links back to the requirement
text it came from, and the Validator flags anything that doesn't. That transparency is the
feature, and it shouldn't be cut for scope.

### [CI/CD](https://github.com/adlerqa/wardeniq/milestone/3) — [#39](https://github.com/adlerqa/wardeniq/issues/39)

Coverage intelligence in the pipeline, where merge decisions actually get made. A GitHub
Action and a CLI that answer "what did this PR touch, and is it tested?" as a PR comment and
a Check Run.

The analysis engine already exists — Code Analysis maps commits and PRs to impacted test
cases today. What's missing is the pipeline-native surface.

The CLI is the highest-leverage piece: build it once and GitLab CI, Jenkins, CircleCI and
Bitbucket come along for free. Two constraints we're committing to up front — it must work
when wardenIQ is **not** publicly reachable (the CI job calls us, not the reverse), and it
must **never fail your build by default**.

## Later — [Platform](https://github.com/adlerqa/wardeniq/milestone/4)

Cross-cutting work that makes the rest sustainable: structured logging
([#17](https://github.com/adlerqa/wardeniq/issues/17) — there are 24 bare `print()` calls and
no `logging` import anywhere), self-hosted GitLab support
([#14](https://github.com/adlerqa/wardeniq/issues/14) — currently hardcoded to gitlab.com),
cost estimation before a generation run
([#22](https://github.com/adlerqa/wardeniq/issues/22)), and container healthchecks
([#25](https://github.com/adlerqa/wardeniq/issues/25)).

---

## Principles

These are the calls we've already made, so you don't have to re-litigate them in a PR:

- **Grounded beats comprehensive.** A suite of 40 cases that all trace to real requirements is
  worth more than 200 that might not. When in doubt, generate less.
- **Assume our own AI is unreliable.** The Validator exists because the generator will
  confidently invent things. New AI features should ship with the check, not after it.
- **Self-hosted is a first-class deployment**, not a fallback. Plenty of our users can't send
  their requirements to a third party, and features that assume public reachability exclude them.
- **Bring your own model.** No hard dependency on one provider. Ollama has to keep working.
- **Don't break the build.** Anything that plugs into someone's pipeline is advisory by
  default and opt-in to gate.

## Not planned

Saying no is part of a roadmap:

- **Running your tests.** wardenIQ decides *what* should be tested and whether it *is*. It's
  not a test runner and won't compete with Playwright or pytest.
- **Being a test-management SaaS.** Test Cycles exist so you don't have to leave for a release
  regression run — not to replace a dedicated tool.
- **A hosted multi-tenant offering**, for now. The product is self-hosted; that shapes the
  architecture and we'd rather do it well than split focus.

---

Roadmap items change. If something here is wrong, or you need something that isn't here,
open an issue and argue for it — that's a genuinely useful contribution on its own.
