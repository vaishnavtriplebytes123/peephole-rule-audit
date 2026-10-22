# Codex planning and milestone workflow

Current authorization (2026-10-22): the user explicitly requested continuation
through all six milestones, periodic pushes, and the new GitHub repository
`vaishnavtriplebytes123/peephole-rule-audit`. This overrides the reusable prompts'
per-milestone approval pauses below for this implementation. Verification,
documentation, intended-diff review and preservation of unrelated files remain
required. Git identity was explicitly provided and configured locally.

The user must approve the plan before application implementation. After each
milestone, report evidence and wait for review. Commit authorization is separate
from approval to implement; do not stage unrelated workspace files.

## Planning prompt

> You are the software engineering agent responsible for this project. Inspect
> repository structure, Git status, PRD.md, AGENTS.md, existing code, dependencies,
> and available validation commands. Treat PRD.md as the product source of truth,
> AGENTS.md as persistent engineering instructions, and existing code/configuration
> as evidence of current implementation. Prepare or update PLAN.md without
> implementing application features. Propose an appropriate architecture and
> ordered milestones with scope, dependencies, deliverables, acceptance criteria,
> and verification commands. Identify real blockers, risks, security concerns,
> assumptions and decisions; distinguish confirmed requirements from proposals.
> Avoid unnecessary dependencies, infrastructure and scope expansion. Preserve
> unrelated work. Do not commit, push, deploy, or modify external services.
> Summarize the plan and wait for review and approval.

## Implementation prompt

> Implement Milestone [NUMBER]: [NAME] from the approved PLAN.md.
> Read PRD.md, AGENTS.md, PLAN.md, current Git status and relevant existing code.
> Implement only this milestone, including connected functionality, configuration,
> tests and documentation. Begin with behavioral tests for its semantic contracts
> and known edge cases. Preserve unrelated behavior and user changes. Validate
> untrusted inputs and handle applicable errors. Avoid unnecessary dependencies
> and unrelated refactoring. Run relevant tests, lint, formatting, type checking,
> builds and CLI smoke checks; fix failures caused by the changes. Review the
> intended diff for regressions, security issues and unrelated modifications.
> Update PLAN.md and documentation. Report functionality, important files, exact
> validation commands and their actual outcomes, known limitations, incomplete
> acceptance criteria and untested behavior. Do not claim unexecuted checks passed.
> Do not commit, push, deploy, purchase services, perform destructive operations,
> or modify external services. Stop for user review after this milestone.

## Review and checkpoint sequence

1. Inspect `git status --short --branch`; identify existing unrelated modifications.
2. Map the milestone to PRD requirement IDs and acceptance criteria.
3. Write tests for behavior, implement, validate, and review the complete intended diff.
4. Report actual evidence, unresolved failures and remaining limitations.
5. Obtain user review and explicit commit authorization.
6. If identity is missing, obtain actual name/email and set repository-local values
   only with authorization; never substitute placeholders or alter global settings.
7. Stage an explicit list of approved files. Inspect `git diff --cached --check`,
   `git diff --cached --stat`, and `git diff --cached` before committing.
8. Use a meaningful message; do not amend/rewrite history or push without authorization.

For the foundation, the intended commit file list consists only of README.md,
PRD.md, AGENTS.md, PLAN.md, .gitignore, .env.example and the new docs/ files.
No commit has been created. Choose branch naming at the authorized checkpoint;
do not initialize a second repository or move existing coursework.

## Required milestone report

- Scope completed and applicable requirement IDs.
- Important files changed and why.
- Exact checks run, actual results, and failures that predate this milestone.
- Verification not performed and the remaining action needed.
- Security/research limitations and any changed assumptions.
- Review request, without implying permission to commit or implement the next milestone.
