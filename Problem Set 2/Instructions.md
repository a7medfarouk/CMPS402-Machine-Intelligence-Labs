# CMPS402 Assignment 2: Scheduling Advisor

Find a conflict-free timetable, then answer questions about alternatives: *Can I take this tutorial? Can I avoid Tuesday? Is this section unavoidable?*

| Item | Details |
|---|---|
| Work | Individually or in pairs |
| Marks | 8 per student: 4 shared code + 2 individual explanation + 2 individual application |
| Submission | One Python-only ZIP per individual or pair |
| Deadline | **Sunday 22 November 2026 at 11:59 PM** |

## 1. Get started

Extract the ZIP into its own folder. Open a terminal in the folder containing **app.py** and **pyproject.toml**, not inside submission/.

If uv is not installed, use the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/). On Windows with WinGet you can run the following, then reopen your terminal:

```powershell
winget install --id=astral-sh.uv -e
```

Run:

```text
uv --version
uv sync --locked
uv run --locked app.py setup-check
uv run --locked app.py
```

The locked project uses **Python 3.14**. uv may download it and the dependencies on first setup. Do not change the Python version or lockfile. The terminal app uses Rich and Questionary. Your submitted algorithms use Python and the supplied interfaces, not external CSP or optimization solvers.

Use Up/Down and Enter in the menu. Use Back to leave a submenu or Ctrl+C to cancel an action. If arrow input does not work, use **uv run --locked app.py --plain-menu**. The numbered menu also works in restricted terminals.

Start with **Start here > Open the offline walkthrough**, or open [Walkthrough.html](examples/Walkthrough.html) in the examples folder. It runs before you write code. Follow the four steps below:

1. **Understand the choices.** Find CMPS402 T1 in the starting timetable, then open the T4 and Tuesday examples. Inspect the available sections and links in **Try your advisor > View sections, links and blocked times**.
2. **Build the model.** Edit model.py and run **Implement and test > model.py**.
3. **Build the solver.** Edit solver.py and run its checks on small generic CSPs. Use **Implement and test > AC-3 unit checks** to try arc consistency on its own.
4. **Answer advisor questions.** Edit advisor.py and run its checks. They supply a fake solve callback, so you can debug it separately. Then try the whole app. **NOT IMPLEMENTED** is normal for untouched functions; re-run all, failed, or selected checks after editing.

## 2. Timetable rules

A request includes every listed component of each requested course; some courses have no tutorial or lab.

- Select one section per requested component. Each section has **exactly one** weekly slot: one day, one start and one end.
- Two intervals clash if they are on the same declared day and overlap. Endpoints touch without a clash: 09:00-10:00 and 10:00-11:00 can coexist. Meetings are stored in minutes from midnight.
- No two selected slots may clash, even for components of the same course. Identical slots for two selected components clash too. A selected slot may not overlap an unavailable interval.
- The timetable is fixed. Do not optimize gaps, travel, or the number of days. Any valid schedule is accepted.

### Links

**No link means no pairing restriction.** In this catalogue, CMPS and EECS courses have no section links. For example, CMPS402 lecture L1 and tutorial T4 can be taken together. EECS102 has lectures and tutorials only; their section numbers do not have to match. Time clashes and unavailable intervals still apply: CMPS402 L2 and T3 are unlinked but overlap on Tuesday.

**A present link is an allow-list.** For MTHS102 and MTHS104 in this catalogue, L1 must go with T1 and L2 with T2. For MTHS102, the link is written **tutorial first**: (T1, L1) and (T2, L2). Read the endpoint names from the record; do not sort them or match section suffixes in your code. A present link with an empty allow-list forbids all pairings. A missing link permits all pairings as far as linking is concerned. Ignore a link when either endpoint is not requested.

## 3. Implement the model

### From a course request to component variables

The JSON request names courses, not sections. The supplied loader expands the courses into their listed components **before** calling build_problem. For example:

```text
JSON: {"courses": ["CMPS402"], "unavailable": []}
request.components: ("CMPS402.lecture", "CMPS402.tutorial")
request.unavailable: ()
domains: {"CMPS402.lecture": {"L1", "L2"},
          "CMPS402.tutorial": {"T1", "T2", "T3", "T4"}}
```

One variable per component lets you choose a lecture and a tutorial independently, then link only the pairs that need it. Using one variable per whole course would make each value a bundle of several sections. That would hide the individual choices you need for clash checks and what-if queries. You do not write the JSON parser or expand courses yourself.

### The records you receive

| Record | Fields and types |
|---|---|
| Catalogue | `days: tuple[str, ...]`; `sections: Mapping[str, tuple[Section, ...]]`; `links: tuple[Link, ...]`; `course_names: Mapping[str, str]` (display only). |
| Request | `components: tuple[str, ...]` in catalogue order; `unavailable: tuple[Meeting, ...]`. |
| Section | `identifier: str` (for example L1); `meeting: Meeting` (singular). |
| Meeting | `day: str`; `start: int`; `end: int`. For example, 09:00 is 540 minutes. |
| Link | `components: tuple[str, str]` in declared order; `allowed: frozenset[tuple[str, str]]` with one ID per endpoint. |
| Problem | `variables: tuple[str, ...]`; `domains: dict[str, set]`; `constraints: list[UnaryConstraint or BinaryConstraint]`. |

Use `catalogue.sections[component]` to get Section objects. Use **section.identifier**, not the Section object, in a domain or assignment. Use **section.meeting** when looking up its slot. IDs are scoped to a component, so L1 can occur in multiple courses.

### Implement two functions in model.py

| Function | What to return |
|---|---|
| build_domains | A fresh set of all section IDs for each requested component, before unary filtering. |
| add_constraints(problem, catalogue, request) | Append constraint objects to problem.constraints and return None. Decide how to encode the timetable rules from Section 2. Do not assign sections, prune domains, or solve the problem here. |

The starter's **build_problem(catalogue, request)** calls these functions to create a fresh Problem. Leave that wiring in place. The modeling decisions and any helper functions inside **add_constraints** are yours. Do not hard-code the bundled timetable or infer a rule from a course prefix.

Test domains first. The constraint checks supply their own domains so you can test **add_constraints** independently.

### A predicate is a function the solver calls later

This example is about colors, not timetables:

```python
not_red = UnaryConstraint("X", lambda color: color != "red")
different = BinaryConstraint(("Y", "X"), lambda first, second: first != second)
not_red.condition("blue")                  # True
different.is_satisfied({"X": "blue", "Y": "green"})  # True
```

The constraint stores a callable, **not** a True/False result from the builder. The solver later supplies trial values. A binary rule receives values in its own endpoint order, regardless of the order in the assignment dictionary. Do not test a binary rule against a partial assignment unless both of its endpoints are assigned.


## 4. Implement a generic solver

### 4.1: Backtracking with heuristics

Complete **submission/solver.py**. The same implementation must work on timetable and small non-timetable CSPs.

| Function | Required behavior |
|---|---|
| one_consistency(problem) | Filter each unary constraint into its domain, remove unary constraints, keep binary constraints, and return whether every domain is nonempty. |
| minimum_remaining_values(problem, domains) | Select an unassigned variable with the smallest current domain. Break ties by problem.variables order. |
| least_constraining_values(problem, variable, domains) | Return values that eliminate fewer distinct remaining neighbor values first. Use ascending value order for ties. Do not mutate the input domains. |
| forward_checking(problem, variable, value, domains) | Filter each direct unassigned neighbor using all applicable constraints. Complete those updates even after a wipeout, then report whether any domain is empty. Do not propagate between two unassigned variables. |
| solve(problem) | Use the four helpers, check consistency with assigned neighbors, backtrack, and restore branch-local state. Return a complete assignment, or None if no solution exists. |

**MRV picks a variable. LCV (least constraining value) orders that variable's values.** For LCV, count a particular neighbor value once even if multiple constraints reject it. All values are hashable and orderable within their own domain.

The **domains** argument in MRV, LCV, and forward checking contains **only currently unassigned variables**. A missing key means assigned; a present key with an empty set means unassigned with zero choices. For example, with `{"Y": set(), "Z": {1, 2}}`, MRV selects Y when called. In search, that branch cannot succeed.

When trying X = 1, put X in the branch assignment and **drop X from the branch domains before forward checking**. Do not delete a neighbor's key when its domain becomes empty: the empty set shows why the branch failed. Discard or restore both branch changes before trying a sibling.

For **one_consistency**, apply every unary rule and build a separate list of constraints to keep. Replace problem.constraints after the loop. Removing items from the list while iterating can skip the next rule.

Use a copy or an undo mechanism for each branch. Unary preprocessing may mutate the working problem; the runner builds a fresh problem per solve. An empty CSP has solution **{}**. A CSP with a required variable that has no legal value is **None**. Do not treat an empty solution as failure.

The app counts each call to a supplied constraint's yes/no function and each call that asks whether every variable is assigned. The counts help you compare the work each solver does. They do not affect your grade.

### 4.2: Arc consistency (AC-3)

Implement **arc_consistency(problem)** in **solver.py**. The unit tests call it directly with a binary CSP whose unary filtering has already been applied. Update **problem.domains** in place and keep the variable names and constraints. Return **True** once the domains are arc-consistent, or **False** if any domain is empty. An already empty domain also fails, even for a variable with no neighbors. You may stop as soon as a domain is empty.

An arc **X to Y** asks whether every value still in X has a supporting value in Y. A single pair of values must satisfy **all** binary constraints between X and Y together, using each constraint's own endpoint order. For example, with X = Y, Y = Z, and Z restricted to {2}, pruning Y to {2} must also cause X to shrink to {2}.

Start with both directions of every constrained pair. When pruning shrinks a domain, revisit incoming arcs whose supports may have changed. Any queue order is allowed. A nonempty fixed point means local consistency only. For example, a triangle with two colors is arc-consistent, even though it has no full coloring.

Use **Implement and test > AC-3 unit checks** or run `uv run --locked app.py check --case ac3-chain`. This exercise is graded through unit tests on the returned Boolean and the domains. **Leave AC-3 out of solve and the timetable advisor.**

## 5. Implement the advisor

Suppose your first timetable has tutorial T1, but you want T4. That first answer does not tell you whether T4 could work. In **submission/advisor.py**, you ask the existing solver to try the same courses with one extra restriction. The supplied **answer_query** already runs these steps in order:

1. **Check the original request.** The callback runs with no extra restrictions. Implement **base_failure(base)** to decide whether to stop.
2. **Build the what-if restriction.** Implement **make_restrictions(catalogue, request, query)** to return a dictionary of allowed section IDs. It does not call the solver.
3. **Read the second result.** Implement **interpret_trial(kind, trial)** to return the verdict and any witness. The starter calls it only after a feasible base.

Start with **advisor-restrictions** and **advisor-results** in the public checks. They do not need your model, solver, or a working end-to-end query. Then run the individual query checks. The app handles the base-schedule menu action separately.

The supplied Query has `kind: str` and three optional string fields. Here is what each action sends:

| kind | component | section | day |
|---|---|---|---|
| take | Component ID | Section ID | None |
| unavoidable | Component ID | Section ID | None |
| avoid-day | None | None | Day label, e.g. Tue |
| schedule (app only) | None | None | None |

Do not access catalogue.sections[query.component] for avoid-day: there is no single component to look up. A day restriction applies to every requested component.

The runner validates the query and supplies **solve_request(restrictions)**. This function builds and solves a **fresh** CSP on every call. A restriction maps a component ID to the section IDs it is still allowed to use. It intersects those IDs with the domain, without bypassing time, link, or availability rules.

```python
base = solve_request({})
trial = solve_request({"CMPS402.tutorial": {"T4"}})
```

The first call tests the unchanged request. If CMPS402 is requested, the second keeps only T4 for its tutorial; all other components retain their choices. An omitted key leaves a domain alone. A key with an empty set leaves that component with no legal choices. The callback returns **SolveResult(status, schedule)**; only SAT carries a schedule, which can be {}.

| Question | What to ask the solver |
|---|---|
| Take this section? | Keep just that section in its component's domain. |
| Avoid this day? | Keep the sections on other days in each requested component's domain. |
| Is this section unavoidable? | Try to avoid it: keep all other section IDs in its component's domain. |

### Read the status, not the timetable

In **base_failure**, SAT means return None and continue. UNSAT means stop with BASE_INFEASIBLE; LIMIT means stop with INCONCLUSIVE. Check the status directly: an empty SAT schedule is not a failure.

| Trial status | Take or avoid-day | Unavoidable |
|---|---|---|
| SAT | POSSIBLE with the trial schedule | NOT_UNAVOIDABLE with the trial schedule |
| UNSAT | IMPOSSIBLE | UNAVOIDABLE |
| LIMIT | INCONCLUSIVE | INCONCLUSIVE |

Return an **Advice** using the supplied Verdict enum. For example, a successful take trial becomes `Advice(Verdict.POSSIBLE, trial.schedule)`. A limit becomes `Advice(Verdict.INCONCLUSIVE)`, with no schedule. Only a SAT trial supplies a witness; never attach the base schedule in its place. The runner handles process errors and time limits.

### Walk through the unavoidable question

In the **forced** request, Thursday morning is blocked. MTHS102 must use its Monday L1 and linked T1. Monday math clashes with CMPS402 L1, so the base works only with CMPS402 L2. First confirm the base returns SAT. Now **ban L2** by keeping only the other allowed lecture IDs. If this second solve returns UNSAT, there is no timetable without L2, so L2 is unavoidable. If it returns SAT instead, return its timetable as the counterexample. Merely seeing L2 in the first timetable is not proof.

In the **blocked** request, Tuesday morning is also blocked and the base fails. Stop at **BASE INFEASIBLE**, not UNAVOIDABLE. Each question is hypothetical: do not change the saved request or reuse another question's restricted domains. No enumeration of every timetable is required.

## 6. Run, check, and investigate

```text
uv run --locked app.py demo
uv run --locked app.py walkthrough
uv run --locked app.py check
uv run --locked app.py check --case unavoidable
uv run --locked app.py run --case week
uv run --locked app.py run --case alternatives --kind avoid-day --day Tue
uv run --locked app.py run --case forced --kind unavoidable --component CMPS402.lecture --section L2
uv run --locked app.py --help
```

**Try your advisor** starts on **alternatives**, a six-course timetable. Find a schedule, then try taking CMPS402 T4 or keeping Tuesday free. **single-course** is the small CMPS402 debugging example. **forced** demonstrates an unavoidable lecture; **blocked** has no base solution.

A timeout is **inconclusive**, not proof that no schedule exists. Runs and public checks use a 5-second default. For debugging, `run --timeout SECONDS` changes only your local run. Use public checks to compare your implementation with the supplied examples. Staff checks independently verify schedules and cover additional instances using the same rules.

In the walkthrough, **single-course** shows the extra checks spent on ordering and pruning a small request. **Packed** shows how that work pays off on an infeasible six-course request: pruning cuts down the number of search states the solver enters. The app records the counts automatically. Submit your Python code only.

## 7. Assessment and discussion

| Component | Marks | Evidence |
|---|---:|---|
| Shared model | 1.00 | Requested variables, domains, time rules, unary restrictions, links |
| Shared solver | 2.00 | Backtracking solver and helpers (1.50) and standalone AC-3 unit checks (0.50) |
| Shared advisor | 1.00 | Correct restrictions, witnesses, necessity, base/limit handling, query isolation |
| Individual explanation | 2.00 | Explain your actual model, solver, and advisor decisions |
| Individual application | 2.00 | Apply the concepts to an unfamiliar advisor/modeling case and solver case |

Each student is assessed individually in discussion. No written answer file, report, video, or prepared discussion file is submitted.

## 8. Submit

1. Finish the required Python files in **submission/**. Keep Python helpers in that folder and use relative imports for them.
2. Choose **Submit > Enter member details**, then **One member** or **Two members**. Enter the full name and ID of each member. For the command-line workflow, you can enter the same details in the literal MEMBERS list in **submission/student_info.py**.
3. Re-run the public checks.
4. Choose **Submit > Build the Python-only ZIP**, or run **uv run --locked app.py submit**.
5. Open the generated ZIP under **output/submissions/**. Check the name and ID in **Name_ID.zip** for one member, or both names and IDs in **Name1_ID1__Name2_ID2.zip** for two. Confirm that the archive contains only Python files under submission/.
6. Upload one ZIP to the location listed in the course announcement before the deadline. For a pair, only one member uploads it. Check that the submission is confirmed and keep a copy of the uploaded ZIP.

Plagiarism and cheating are prohibited. Do not copy or share solutions across submissions. Each student must understand and be able to explain the submitted work.
