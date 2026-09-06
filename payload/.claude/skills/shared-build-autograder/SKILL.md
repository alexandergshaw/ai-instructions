---
name: shared-build-autograder
description: Build or replace an automated grading harness for a student assignment. Derives tests from the assignment's stated requirements, keeps the harness outside student directories, and reports coverage gaps without revealing solutions. Use when creating or standardizing autograder tests, or deciding which parts of an assignment are objectively testable. Not for writing a student's own solution, not for writing tests against one student's submission, and not for altering an assignment's requirements to make grading easier.
---

# Shared Build Autograder

## Procedure

1. Inspect assignment documentation and any repository README files before writing tests.
2. Identify objectively testable requirements and separate them from unstated expectations.
3. Inspect any existing test harness, fixtures, and grading scripts.
4. Determine the repository's standard test location and keep new tests there.
5. Remove or replace obsolete harness components only when they are clearly superseded.
6. Create tests outside student assignment folders.
7. Cover required behavior and meaningful edge cases without expanding scope arbitrarily.
8. Avoid leaking full assignment solutions in tests, fixtures, or failure messages.
9. Run the relevant test suite after changes.
10. Report remaining coverage gaps, assumptions, and any requirements that were not objectively testable.
