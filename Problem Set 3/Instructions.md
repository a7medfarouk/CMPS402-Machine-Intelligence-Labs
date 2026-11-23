# CMPS402 Assignment 3: Adversarial Search

Build one search agent that can play Connect Four and Chomp.

| Item       | Details                                               |
| ---------- | ----------------------------------------------------- |
| Work       | Individually or in pairs                              |
| Marks      | 5 per student, plus an optional bonus of up to 1 mark |
| Submission | One Python-only ZIP per individual or pair            |
| Deadline   | **Saturday 28 November 2026 at 11:59 PM**             |

**Late submissions will be penalized heavily. A submission up to two hours late receives a lower late penalty than a submission more than two hours late.** The lower-penalty window ends on Sunday 29 November 2026 at 1:59 AM. This is not a penalty-free grace period. Start the upload early and check that it finishes successfully.

**Plagiarism and cheating are prohibited.** Work with your registered partner. Do not copy or exchange solutions with other teams, distribute your solution, or submit someone else's work as your own. Each member must understand the submitted implementation and explain its decisions.

## 1. Get started

Extract the student ZIP. Open a terminal in the folder containing **app.py** and **pyproject.toml**.

If you need uv, follow the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/). On Windows with WinGet, you can run `winget install --id=astral-sh.uv -e` and reopen the terminal.

```text
uv sync --locked
uv run --locked app.py
```

The project uses **Python 3.14**. Use Up/Down and Enter in the menu. If arrow keys are unavailable, run `uv run --locked app.py --plain-menu`.

Choose **Play in browser**. If the browser does not open, use the address printed in the terminal. Press Ctrl+C in the terminal to stop the app. The built-in opponent is available as soon as setup is complete.

## 2. Try the games

In **Play**, choose **Built-in opponent** and **Start position** to try either game. In Connect Four, discs fall to the lowest empty cell and four in a line wins. In Chomp, a bite removes the chosen square and the rectangle below and to its right. Leave only the top-left square (poison) to win.

To try your code before writing the evaluators, choose **My agent**, **Minimax**, and **Zero baseline**, then choose **Start position**. The Zero baseline estimates every nonterminal position at 0.

## 3. Implement search

Edit **submission/search.py**. Use the supplied game methods so your code also works on test trees whose states may be strings.

| Method                              | What it returns                                                             |
| ----------------------------------- | --------------------------------------------------------------------------- |
| `game.get_turn(state)`              | Player 0 (X) or player 1 (O).                                               |
| `game.get_actions(state)`           | The legal actions in the engine's order. Call this for a nonterminal state. |
| `game.get_successor(state, action)` | The next immutable state after a legal action.                              |
| `game.is_terminal(state)`           | `(False, None)` during play or `(True, (score_0, score_1))` at the end.     |

### Search functions

`minimax`, `alphabeta`, and `expectimax` return **`(value, action)`**. Keep `max_player` fixed. Each move uses one unit of depth. Check for a terminal state first and return its utility for MAX with action `None`. At depth zero on a nonterminal state, return `evaluate(game, state, max_player)` and `None`. Any genuinely optimal action is accepted on a tie.

- **`minimax`** maximizes on MAX's turn and minimizes on the opponent's turn.
- **`alphabeta`** must match the minimax value and return an optimal legal action. Prune when `alpha >= beta`.
- **`order_moves`** returns all legal actions as a list or tuple sorted by successor score. Use true utility for terminal successors and the evaluator for others. Sort highest first for MAX and lowest first for MIN, with ties in legal action order. Use it at MAX and MIN nodes when `ordered=True` and more than one ply remains. On the final ply, ordering is optional.
- **`expectimax`** maximizes for MAX and takes the uniform mean of all replies at a chance node. At a chance root, return the mean and action `None`. This function is checked on trees.

## 4. Implement both evaluators

Edit **submission/evaluation.py**. Both functions estimate **nonterminal** positions. Think of `max_player` as the player you are scoring for and `game.get_turn(state)` as the player who moves next. If MAX is X, an O threat should lower X's score even on X's turn. Pick your own weights and return a finite score strictly between **-1000 and 1000**. Search scores finished games.

### Connect Four

**Read the board.** On the 6-by-7 board, `state.board[row][column]` is `None` for empty, `0` for X, and `1` for O. Row 0 is the top and row 5 is the bottom. Each entry in `game.lines` gives four `(row, column)` coordinates, including horizontal, vertical, and diagonal lines.

**Score the threats.** In `evaluate_connect_four`, read the four cells in a line. Three discs of one color and an empty fourth cell form a threat. A disc can land in the gap now if it is on row 5 or has a disc directly below it. Give playable threats more weight. You may give unsupported threats zero weight. MAX's weighted threats raise the score and the opponent's lower it.

**Example.** Two X threats, viewed from the bottom of the board. `*` is the gap being scored.

```text
                 Playable        Needs setup
Above bottom     . . . .         X X X *
Bottom row       X X X *         O X O .
```

The left gap fills with one drop. On the right, the disc lands below the gap. The left threat is stronger for X. Browser columns are labeled 1-7 and Python columns are 0-6.

### Chomp

**Read the board.** `state.board` lists row lengths from top to bottom. A horizontal three-square strip is `(3, 0, 0)`. Its vertical counterpart is `(1, 1, 1)`. A bite selects a remaining square by its zero-based `(row, column)` coordinates.

**Score the shapes.** In `evaluate_chomp`, give a strong advantage to the next player if they can win in one bite. Biting `(0, 1)` on the horizontal strip leaves only poison. The same bite on the corner `(2, 1, 0)` leaves `(1, 1, 0)`, so the opponent can win next. Every legal bite on the corner has that drawback. A shape with a bite that avoids immediate loss should score better for the player to move than this corner.

| Next to move, with MAX fixed as player 0 | Which shape should score higher for MAX?      |
| ---------------------------------------- | --------------------------------------------- |
| Player 0 (MAX)                           | Strip. MAX has the winning bite.              |
| Player 1 (MIN)                           | Corner. MIN has to give MAX the winning bite. |

Try **One strip** and **The corner trap** in **Play** to see the difference.

## 5. Run public checks

Choose **Run public checks** for the 13 required checks. From the results you can retry failures or choose one check. **NOT IMPLEMENTED** means a function is still a starter stub.

The alpha-beta check verifies that search skips branches. **Compare** shows work counts and elapsed time. Search values are from the perspective of the player to move.

```text
uv run --locked app.py check
uv run --locked app.py check --case expectimax-average
```

## 6. Assessment and submission

| Task                         |      Marks |
| ---------------------------- | ---------: |
| Shared code                  |       3.00 |
| Individual explanation       |       1.00 |
| Individual application       |       1.00 |
| **Base total**               |   **5.00** |
| Chomp endgame bonus          |       1.00 |

### Optional bonus: exact Chomp endgames

Implement **`solve_chomp_endgame(game, state, max_player=0)`** in **submission/search.py**. Return the exact utility for MAX and an optimal legal bite for the side to move. At a terminal board, return the utility and `None`. Positions have up to 16 squares including poison.

Choose **Chomp bonus** on the main menu or run `uv run --locked app.py check --case chomp-endgame`.

### Submission steps

1. Finish **submission/search.py** and **submission/evaluation.py**. Keep any Python helpers inside **submission/**.
2. Choose **Submit > Enter member details** and select one or two students. For the command-line workflow, you can enter the details in the literal **MEMBERS** list in **submission/student_info.py**.
3. Re-run the public checks. Choose **Submit > Build the Python-only ZIP**, or run `uv run --locked app.py submit`.
4. Open the generated ZIP under **output/submissions/**. Verify **Name_ID.zip** for one member or **Name1_ID1\_\_Name2_ID2.zip** for a pair. It should contain only Python files under **submission/**.
5. Upload one ZIP to Google Classroom before the deadline. For pairs, only one member uploads.
