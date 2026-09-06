# Repository Structure Rules

- Understand the existing repository layout before moving or adding files.
- Maintain clear separation between source code, tests, documentation, and generated output.
- Avoid adding arbitrary top-level directories when an existing location already fits.
- Follow established repository conventions unless centrally defined rules intentionally supersede them.
- Do not place test harnesses inside student assignment directories when the repository follows the standardized educational layout.
- Never rename, split, relocate or delete a file whose path or single-file shape is fixed by an assignment, an autograder, a submission process, or code that reads it by path. Report its size or structure instead. The reader that depends on the path is often in another repository, so absence of evidence in this one is not evidence that nothing depends on it.
- A test file placed alongside the assignment it grades is a supported layout, not an inconsistency to tidy up.
