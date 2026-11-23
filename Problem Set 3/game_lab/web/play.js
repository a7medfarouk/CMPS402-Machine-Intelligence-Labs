"use strict";

const byId = id => document.getElementById(id);
const field = id => byId(id).value;
const games = {
  "connect-four": {
    name: "Connect Four",
    rules: "Drop a disc into a column. Four in a row, including diagonals, wins.",
    positions: {
      start: ["Empty board", "Start a full game."],
      ordering: ["Compare move ordering", "Load this midgame position for the search comparison."]
    }
  },
  chomp: {
    name: "Chomp",
    rules: "A bite removes the chosen square and the rectangle below and to its right. Leave only poison to win.",
    positions: {
      start: ["Full 3 × 4 bar", "Start with all 12 squares, including the poison."],
      wide: ["Wide bar: 7 columns × 4 rows", "A larger game with 27 safe first moves. Try depth 2 first."],
      row: ["One strip", "Can the player to move leave only the poison this turn?"],
      corner: ["The corner trap", "There are three squares again. What will the opponent be able to do?"]
    }
  }
};
const methods = {minimax: "Minimax", alphabeta: "Alpha-beta", ordered: "Ordered alpha-beta"};
const inputs = ["select-connect-four", "select-chomp", "preset", "agent", "first", "method", "depth",
  "evaluation", "start", "undo", "reset", "go-play", "go-compare", "back-play",
  "compare-depth", "compare-evaluation", "compare", "copy-position", "load-position", "resume"];
let choice = "connect-four", current, state, human, lastStats, busy = false, floor = 0;
let showing = "play";

function selectGame(name) {
  choice = name;
  for (const game of Object.keys(games)) byId("select-" + game).setAttribute("aria-pressed", String(game === name));
  byId("preset").replaceChildren(...Object.entries(games[name].positions)
    .map(([id, [label]]) => new Option(label, id)));
  showPending();
}

function settings() {
  return {game: choice, preset: field("preset"), agent: field("agent"), first: field("first"),
    depth: Number(field("depth")), method: field("method"), evaluation: field("evaluation")};
}

function showPending() {
  byId("preset-hint").textContent = games[choice].positions[field("preset")][1];
  const ownAgent = field("agent") === "student";
  byId("agent-options").hidden = !ownAgent;
  const changed = current && Object.entries(settings()).some(([key, value]) => current[key] !== value);
  byId("setup-note").textContent = changed ? "Choose Start position to apply your settings." :
    ownAgent ? "Use Zero baseline to try your search while your evaluator is unfinished." :
      "You can play the built-in opponent before writing any code.";
}

async function request(action, history, overrides = {}) {
  const response = await fetch("/api/game", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({...current, ...overrides, action, history})
  });
  if (!response.ok) throw new Error("The local app could not complete this request.");
  const result = await response.json();
  if (result.status !== "OK") {
    const detail = result.status === "NOT IMPLEMENTED"
      ? result.detail + " See Run public checks in the terminal." : result.detail;
    throw Object.assign(new Error(detail), {status: result.status});
  }
  return result;
}

function status(message, error = false) {
  byId("status").textContent = message;
  byId("status").classList.toggle("error", error);
}

function playError(error, hint = "") {
  const label = error.status ? error.status + " · " : "";
  status(label + error.message + (hint ? " " + hint : ""), true);
}

function moveText(action) {
  return Array.isArray(action) ? "row " + (action[0] + 1) + ", column " + (action[1] + 1) : "column " + (action + 1);
}

function positionName() {
  return games[current.game].positions[current.preset][0];
}

function playerName(player) {
  return player === 0 ? "X" : "O";
}

function actionButton(label, accessibleName, action, disabled, className) {
  const item = document.createElement("button");
  item.textContent = label;
  item.setAttribute("aria-label", accessibleName);
  item.className = className;
  item.disabled = disabled;
  item.addEventListener("click", () => makeMove(action, accessibleName));
  return item;
}

function renderDiscs(board, allowMove) {
  board.className = "four";
  const latestColumn = state.history.at(-1);
  const latestRow = state.board.findIndex(row => row[latestColumn] != null);
  for (let column = 0; column < 7; column += 1) {
    board.append(actionButton(String(column + 1), "Drop in column " + (column + 1),
      column, !allowMove || !state.legal.includes(column), "drop"));
  }
  state.board.forEach((row, r) => row.forEach((player, col) => {
    const disc = document.createElement("span");
    disc.className = "disc" + (player === null ? "" : " p" + player)
      + (r === latestRow && col === latestColumn ? " last" : "");
    disc.textContent = player === null ? "" : playerName(player);
    board.append(disc);
  }));
}

function renderSquares(board, allowMove) {
  board.className = state.columns === 7 ? "chomp wide-bar" : "chomp";
  const present = [];
  for (let row = 0; row < state.rows; row += 1) {
    for (let col = 0; col < state.columns; col += 1) {
      const gone = col >= state.board[row], poison = row === 0 && col === 0;
      const square = actionButton(poison ? "×" : "•", poison ? "Poison" : "Bite " + moveText([row, col]),
        [row, col], !allowMove || gone || poison, "square" + (gone ? " gone" : poison ? " poison" : ""));
      if (gone) square.setAttribute("aria-hidden", "true");
      else present.push({row, col, square});
      const preview = active => {
        if (!square.disabled) present.forEach(item => {
          item.square.classList.toggle("preview", active && item.row >= row && item.col >= col);
        });
      };
      for (const event of ["pointerenter", "focus"]) square.addEventListener(event, () => preview(true));
      for (const event of ["pointerleave", "blur"]) square.addEventListener(event, () => preview(false));
      board.append(square);
    }
  }
}

function renderLast() {
  const target = byId("last");
  if (!lastStats) {
    target.textContent = "Play a turn to see the reply.";
    return;
  }
  const {move, value, method, max_player, terminal_checks, successors, evaluations, milliseconds} = lastStats;
  target.textContent = "Played " + moveText(move) + ".";
  if (terminal_checks === undefined) return;
  target.append(document.createElement("br"), methods[method] + " scored this position at " + value
    + " for " + playerName(max_player) + ".");
  const metrics = document.createElement("div");
  metrics.className = "move-metrics";
  for (const value of [terminal_checks + " terminal checks", successors + " successors",
                       evaluations + " evaluator calls", milliseconds + " ms"]) {
    const item = document.createElement("span");
    item.textContent = value;
    metrics.append(item);
  }
  target.append(metrics);
}

function render() {
  const board = byId("board");
  board.replaceChildren();
  const game = games[current.game];
  byId("game-title").textContent = game.name;
  byId("position-name").textContent = positionName();
  byId("rules").textContent = game.rules;
  for (const id of inputs) byId(id).disabled = busy;
  byId("undo").disabled = busy || !state || state.history.length <= floor;
  byId("compare").disabled = busy || !state || state.ended;
  byId("copy-position").disabled = busy || !state;
  byId("resume").hidden = !state || state.ended || state.turn === human;
  if (!state) {
    byId("players").textContent = "";
  } else {
    const allowMove = !busy && !state.ended && state.turn === human;
    if (current.game === "chomp") renderSquares(board, allowMove);
    else renderDiscs(board, allowMove);
    byId("players").textContent = "You play " + playerName(human) + " · "
      + (current.agent === "student" ? "My agent" : "Built-in opponent") + " plays " + playerName(1 - human);
  }
  byId("compare-position").textContent = game.name + " · " + positionName() + (state
    ? state.ended ? " · Game finished. Undo or load a playable position." :
      " · " + playerName(state.turn) + " to move · " + state.history.length + " moves from the starting position"
    : " · Load a position in Play first.");
  renderLast();
}

function announce() {
  status(state.ended ? state.winner === "draw" ? "Draw." : state.winner === human ? "You won." : "The agent won."
    : state.turn === human ? "Your turn." : "Agent’s turn.");
}

async function agentReply() {
  status("Agent is moving…");
  state = await request("reply", state.history);
  lastStats = state.stats;
}

async function resume() {
  if (busy || !state || state.ended || state.turn === human) return;
  busy = true;
  render();
  clearComparison();
  try {
    await agentReply();
    if (current.first === "agent" && state.history.length === 1) floor = 1;
    announce();
  } catch (error) {
    playError(error, "Undo or start a new position to retry.");
  } finally {
    busy = false;
    render();
  }
}

function clearComparison() {
  byId("comparison").textContent = "";
}

async function start(applySettings) {
  if (busy) return;
  busy = true;
  if (applySettings) current = settings();
  state = null;
  lastStats = null;
  floor = 0;
  clearComparison();
  showPending();
  status("Loading position…");
  render();
  try {
    state = await request("inspect", []);
    human = current.first === "human" ? state.turn : 1 - state.turn;
    if (human !== state.turn) {
      await agentReply();
      floor = state.history.length;
    }
    announce();
  } catch (error) {
    playError(error, "Change settings and start again to retry.");
  } finally {
    busy = false;
    render();
  }
}

async function makeMove(action, label) {
  if (busy || !state || state.ended || state.turn !== human) return;
  const restoreFocus = document.activeElement?.getAttribute("aria-label") === label;
  busy = true;
  lastStats = null;
  clearComparison();
  status("Playing move…");
  render();
  try {
    state = await request("inspect", [...state.history, action]);
    if (!state.ended) {
      render();
      await agentReply();
    }
    announce();
  } catch (error) {
    playError(error, "Undo or start a new position to retry.");
  } finally {
    busy = false;
    render();
    if (restoreFocus) {
      const legal = [...byId("board").querySelectorAll("button:enabled")];
      (legal.find(move => move.getAttribute("aria-label") === label) || legal[0] || byId("undo")).focus();
    }
  }
}

async function undo() {
  if (busy || !state || state.history.length <= floor) return;
  busy = true;
  clearComparison();
  render();
  try {
    const remove = state.turn === human ? 2 : 1;
    state = await request("inspect", state.history.slice(0, Math.max(floor, state.history.length - remove)));
    lastStats = null;
    announce();
  } catch (error) {
    playError(error);
  } finally {
    busy = false;
    render();
  }
}

function compareRow(values, tag) {
  const row = document.createElement("tr");
  for (const value of values) {
    const cell = document.createElement(tag);
    cell.textContent = value;
    if (tag === "th") cell.scope = "col";
    row.append(cell);
  }
  return row;
}

async function compare() {
  if (busy || !state || state.ended) return;
  busy = true;
  render();
  clearComparison();
  const target = byId("comparison");
  const methodsToCompare = ["minimax", "alphabeta", "ordered"];
  const depth = Number(field("compare-depth")), evaluation = field("compare-evaluation");
  const summary = document.createElement("p");
  summary.setAttribute("role", "status");
  const table = document.createElement("table");
  table.createTHead().append(compareRow(["Search", "Status", "Move", "Value for " + playerName(state.turn), "Terminal checks",
    "Successor calls", "Evaluator calls", "Time (ms)"], "th"));
  const body = table.createTBody();
  const rows = Object.fromEntries(methodsToCompare.map(method => {
    const row = compareRow([methods[method], "Waiting", "—", "—", "—", "—", "—", "—"], "td");
    body.append(row);
    return [method, row];
  }));
  const scroll = document.createElement("div");
  scroll.className = "scroll";
  scroll.tabIndex = 0;
  scroll.setAttribute("role", "region");
  scroll.setAttribute("aria-label", "Comparison results");
  scroll.append(table);
  const errors = document.createElement("ul");
  errors.className = "comparison-errors";
  target.append(summary, scroll, errors);
  const values = [];
  try {
    for (const method of methodsToCompare) {
      const cells = rows[method].cells;
      cells[1].textContent = "Running…";
      summary.textContent = "Running " + methods[method] + " at depth " + depth + "…";
      try {
        const {stats} = await request("compare", state.history, {depth, evaluation, method});
        values.push(stats.value);
        cells[1].textContent = "Completed";
        cells[1].className = "outcome OK";
        [moveText(stats.move), stats.value, stats.terminal_checks, stats.successors, stats.evaluations, stats.milliseconds]
          .forEach((value, index) => { cells[index + 2].textContent = value; });
      } catch (error) {
        cells[1].textContent = error.status || "Connection error";
        cells[1].className = "outcome failed";
        const note = document.createElement("li");
        note.textContent = methods[method] + ": " + error.message;
        errors.append(note);
      }
    }
    const settings = "Depth " + depth + " · " + (evaluation === "zero" ? "Zero baseline." : "My evaluator.");
    const agree = values.every(value => Math.abs(value - values[0]) <= 1e-9);
    if (values.length === methodsToCompare.length && agree) {
      summary.textContent = settings + " All three searches returned the same value.";
    } else if (!agree) {
      summary.textContent = settings + " Completed searches disagree on the position value. Check the cutoff rules and alpha-beta bounds.";
    } else {
      summary.textContent = settings + " " + values.length + " of 3 searches completed. See the rows for details.";
    }
  } finally {
    busy = false;
    render();
  }
}

function show(view) {
  if (busy || view === showing) return;
  showing = view;
  for (const tab of ["play", "compare"]) {
    byId(tab + "-view").hidden = tab !== view;
    byId("go-" + tab).setAttribute("aria-pressed", String(tab === view));
  }
  byId("go-" + view).focus();
}

function replayMessage(message, error = false) {
  const target = byId("replay-status");
  target.textContent = message;
  target.classList.toggle("error", error);
}

async function openReplay(copy) {
  if (busy || (copy && !state)) return;
  const dialog = byId("replay-dialog"), code = byId("replay-code");
  byId("replay-title").textContent = copy ? "Copy position" : "Load position";
  byId("replay-help").textContent = copy
    ? "Keep this code to reopen the same board, moves, and search settings."
    : "Paste a position code. It opens the recorded board without making a move.";
  byId("replay-apply").hidden = copy;
  code.readOnly = copy;
  code.value = copy ? JSON.stringify({
    version: 1, config: current, history: state.history, floor,
    comparison: {depth: Number(field("compare-depth")), evaluation: field("compare-evaluation")}
  }) : "";
  replayMessage("");
  dialog.showModal();
  code.focus();
  if (copy) {
    code.select();
    try {
      await navigator.clipboard.writeText(code.value);
      if (dialog.open && code.readOnly) replayMessage("Copied to clipboard.");
    } catch {
      if (dialog.open && code.readOnly) replayMessage("The code is selected. Use Ctrl+C or your device's Copy command.");
    }
  }
}

function parseReplay(value) {
  if (value.length > 4096) throw new Error("The position code is too long.");
  const decoded = JSON.parse(value);
  if (!decoded || typeof decoded !== "object") throw new Error("Paste a complete position code.");
  const {version, config, history, floor, comparison} = decoded;
  const game = config && Object.hasOwn(games, config.game) ? games[config.game] : null;
  const depth = value => Number.isInteger(value) && value >= 1 && value <= 4;
  const evaluator = value => ["zero", "student"].includes(value);
  if (version !== 1 || !game || !Object.hasOwn(game.positions, config.preset)
      || !["student", "baseline"].includes(config.agent) || !["human", "agent"].includes(config.first)
      || !Object.hasOwn(methods, config.method) || !depth(config.depth) || !evaluator(config.evaluation)
      || !Array.isArray(history) || history.length > 42
      || ![0, 1].includes(floor) || floor > history.length || (floor && config.first !== "agent")
      || !comparison || !depth(comparison.depth) || !evaluator(comparison.evaluation)) {
    throw new Error("This position code has invalid settings.");
  }
  const {game: name, preset, agent, first, method, depth: ply, evaluation} = config;
  return {config: {game: name, preset, agent, first, method, depth: ply, evaluation}, history, floor, comparison};
}

async function loadReplay() {
  if (busy) return;
  const input = byId("replay-code"), dialog = byId("replay-dialog");
  busy = true;
  byId("replay-apply").disabled = byId("replay-close").disabled = input.disabled = true;
  try {
    const replay = parseReplay(input.value.trim());
    const restored = await request("inspect", replay.history, replay.config);
    current = replay.config;
    state = restored;
    floor = replay.floor;
    lastStats = null;
    const openingPlayer = state.history.length % 2 ? 1 - state.turn : state.turn;
    human = current.first === "human" ? openingPlayer : 1 - openingPlayer;
    selectGame(current.game);
    for (const key of ["preset", "agent", "first", "method", "depth", "evaluation"]) byId(key).value = current[key];
    byId("compare-depth").value = replay.comparison.depth;
    byId("compare-evaluation").value = replay.comparison.evaluation;
    showPending();
    clearComparison();
    announce();
    dialog.close();
  } catch (error) {
    replayMessage(error instanceof SyntaxError ? "Paste a complete position code." : error.message, true);
  } finally {
    busy = false;
    byId("replay-apply").disabled = byId("replay-close").disabled = input.disabled = false;
    render();
  }
}

for (const game of Object.keys(games)) byId("select-" + game).addEventListener("click", () => selectGame(game));
for (const id of ["preset", "agent", "first", "method", "depth", "evaluation"]) byId(id).addEventListener("change", showPending);
for (const id of ["compare-depth", "compare-evaluation"]) byId(id).addEventListener("change", clearComparison);
byId("go-play").addEventListener("click", () => show("play"));
byId("go-compare").addEventListener("click", () => show("compare"));
byId("back-play").addEventListener("click", () => show("play"));
byId("start").addEventListener("click", () => start(true));
byId("reset").addEventListener("click", () => start(false));
byId("undo").addEventListener("click", undo);
byId("resume").addEventListener("click", resume);
byId("compare").addEventListener("click", compare);
byId("copy-position").addEventListener("click", () => openReplay(true));
byId("load-position").addEventListener("click", () => openReplay(false));
byId("replay-close").addEventListener("click", () => byId("replay-dialog").close());
byId("replay-apply").addEventListener("click", loadReplay);
byId("replay-dialog").addEventListener("cancel", event => { if (busy) event.preventDefault(); });
selectGame("connect-four");
start(true);
