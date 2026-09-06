---
name: shared-standardize-repository
description: Reconcile a repository's layout against shared structure conventions, making the minimum change needed. Use when files are demonstrably in the wrong place - source mixed into tests, generated output committed beside handwritten code, two directories serving one purpose. Not for a layout that merely differs from another project's. Never moves, renames or splits a file whose path is fixed by an assignment, an autograder, a submission process, or code that reads it by path, and treats a test file colocated with the assignment it grades as a supported layout rather than an inconsistency.
---

# Shared Standardize Repository

## Procedure

1. Inspect the full repository layout before proposing structural changes.
2. Identify inconsistencies in source, tests, documentation, and generated output placement.
3. Compare the current layout against shared repository standards.
4. Preserve meaningful project-specific structures that serve a real purpose.
5. Make only the minimum structural changes needed to improve consistency.
6. Avoid deleting unrelated content.
7. Update imports, paths, and configuration when structural changes require it.
8. Run the relevant validation or test commands after changes.
9. Summarize the structural changes, preserved exceptions, and remaining assumptions.
