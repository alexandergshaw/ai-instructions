# General Testing Rules

- Derive tests from requirements and observable behavior.
- Favor deterministic tests over timing-sensitive or environment-sensitive checks.
- Preserve test isolation and avoid hidden ordering dependencies.
- Do not change implementation solely to game a test.
- Distinguish unit, integration, and system testing responsibilities.
- Validate both happy paths and meaningful edge cases.

## A test must be able to fail

A test that cannot fail is an assumption wearing a test's clothes, and the suite
being green is what makes it dangerous.

Prove a test can fail before trusting it: break the behavior it names, confirm
the test goes red, then delete the sabotaged copy and confirm the suite is green
in the original.

**Say which tests you proved this way.** A proof nobody has to name is a proof
nobody has to perform.

**Break a scratch copy, never the working tree.** Copy the whole project — or
the smallest self-contained unit that builds and runs on its own, such as a
single assignment folder — to a temporary location outside the repository.
Sabotage it there, and run the suite **from inside the copy**, so imports,
build paths and test discovery resolve to the copy rather than back to the
original.

Copying only the one file under test does not work: a test that locates its
subject relative to its own path, or through the project's import path, will
run against the untouched original and report green. That is the failure this
section exists to prevent, produced by the method meant to avoid it.

A break applied in place instead survives an interruption, a crash, or a
forgotten restore — and if anything commits in between, the sabotage ships.

**Never modify a file that holds submitted or assessed work in order to prove a
test.** In a repository holding assessed work the assignment's own test file is
an artifact too: do not add, delete or alter its cases to make a proof easier.
Where the code under test and the graded artifact are the same file, there is no
safe in-place sabotage. Use a copy, or say the test is unproven and why.

**Confirm the sabotage actually reached the code the test ran against.** A break
that never applied — a replacement string that did not match, a path that did
not exist, an edit to a file the suite does not import — reports green and looks
identical to a test that cannot fail.

## The catalogue

Every shape below is a real way a suite reports success over code it never
exercised.

**The tested twin nobody calls.** Two implementations of one rule exist; the
code that actually runs wires up one and the tests import the other. Invert the live one and
the suite stays green. When consolidating, delete the loser rather than leaving
it exported, and check which one the running code actually imports.

**The assertion of absence.** Asserting that a value is missing passes when the
field was renamed, when the object is empty, and when the function returned
early without doing anything. Assert what *is* there — unless absence is itself
the requirement, in which case assert the absence **and** the positive behavior
that must remain.

**The fixture the code never emits.** A green suite proves nothing if every
fixture uses a shape the real code cannot produce. Where the code under test
already exists, build fixtures from its observed output rather than from what
the test author expects. Where the test predates the code — an autograder
written from an assignment specification — build them from the specification,
and add one for every output shape the specification permits, so a valid
alternative solution is not failed for being shaped differently.

**The injected fake that cannot see the bug.** A stub whose signature ignores
the argument under test passes whether or not the caller passes it. If the
defect is "a field was dropped", the fake must be able to observe the field.

**Fakes that outlive their reset.** A framework's blanket reset usually restores
stubs it installed, and usually does *not* clear one installed by replacing a
module or a factory before import. Check which of the two each fake is, and
assert in a later test that the fake is gone — a stale fake from a previous test
makes the next one pass for the wrong reason.

**The round-trip that hides the regression.** Testing a writer by reading its
own output back passes when both sides share a defect, and when the reader
independently re-establishes the invariant the writer just broke. Assert against
the serialized form directly.

**The test that pins the spelling.** Asserting exact wording forces contorted
implementations and goes red on every harmless edit. Pin the fact and the
ordering, not the phrasing — **unless the wording is itself the requirement**,
which is common and legitimate: an assignment that specifies exact output, a
protocol with a fixed message, a user-facing string under review. Where the
wording is the requirement, assert it exactly and say why.

**The count canary nobody bumped.** When a total and a sub-count both move by
one, that agreement is the proof the new member landed in the right bucket,
which is why the bump belongs in the same commit. "Fixing" a red canary by
deleting an entry destroys the only thing it was measuring.

**The scanner that matched nothing.** A source-text scan reports clean because
its pattern never matched anything at all, including the thing it was looking
for. Every scanner needs a canary case proving it fires on known-bad input.

**The skipped test read as a passing one.** A test skipped for a missing
platform capability, an absent credential, or an unavailable service is not
evidence of anything. State which tests skipped and why, rather than reporting
the summary line as green.
