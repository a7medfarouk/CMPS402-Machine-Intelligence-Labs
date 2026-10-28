"use strict";

const records = JSON.parse(document.getElementById("records").textContent);
const byId = identifier => document.getElementById(identifier);
const algorithmNames = {bfs: "BFS", dfs: "DFS", ucs: "UCS", greedy: "Greedy", astar: "A*"};
const heuristicNames = {baseline: "Manhattan baseline", student: "My heuristic"};
const verdicts = {ok: "Passed local checks", no_solution: "No solution", local_only: "Local only", wrong_answer: "Wrong answer", time_limit: "Time limit", resource_limit: "Expansion limit", not_implemented: "Not implemented", runtime_error: "Runtime error"};
const goodStatuses = new Set(["ok", "no_solution"]);
const neutralStatuses = new Set(["ok", "no_solution", "local_only"]);
let active = 0;
let mode = "path";
let step = 0;
let timer = null;

function mapTitle(record, index) {
    const name = record.case || "";
    const known = {demo: "Campus demo", weighted_detour: "Weighted detour", key_revisit: "Collect, then revisit", goal_before_key: "Destination before pickup", locked_key: "Locked pickup", unreachable: "Unreachable destination", ties: "Equal-priority paths"};
    if (known[name]) return known[name];
    const match = name.match(/^(unit_cost|weighted|key_door)_(\d+)$/);
    if (match) return ({unit_cost: "Unit-cost", weighted: "Weighted", key_door: "Pickup & doors"})[match[1]] + " map " + Number(match[2]);
    return name ? name.replace(/_/g, " ") : "Custom map " + (index + 1);
}

const maps = [];
const mapForRecord = records.map((record, index) => {
    const key = JSON.stringify([record.case || "", record.map]);
    let group = maps.findIndex(item => item.key === key);
    if (group < 0) {
        group = maps.length;
        maps.push({key, title: mapTitle(record, group), indices: []});
    }
    maps[group].indices.push(index);
    return group;
});

function current() { return records[active]; }
function frames() { return current()?.[mode] || []; }
function needsAttention(record) { return !neutralStatuses.has(record.status); }
function tone(record) { return goodStatuses.has(record.status) ? "good" : record.status === "local_only" ? "warn" : "bad"; }
function display(value) { return value === null || value === undefined ? "—" : String(value); }
function algorithmLabel(record) { return algorithmNames[record.algorithm] || record.algorithm || "Agent"; }
function informed(record) { return ["astar", "greedy"].includes(record.algorithm); }

function setOptions(element, choices, selected) {
    element.replaceChildren();
    for (const [value, label] of choices) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        element.append(option);
    }
    element.value = String(selected);
}

function stop() {
    clearInterval(timer);
    timer = null;
    byId("play").textContent = "Play";
}

function activate(index) {
    stop();
    active = index;
    step = 0;
    mode = current().path?.length ? "path" : "expanded";
    renderSelection();
    renderSummary();
    renderComparison();
    renderPlayback();
}

function renderSelection() {
    const record = current();
    const group = maps[mapForRecord[active]];
    byId("map").value = String(mapForRecord[active]);
    byId("mapInfo").textContent = record.map[0].length + " columns × " + record.map.length + " rows · " + group.indices.length + " recorded runs";
    byId("algorithms").replaceChildren();
    for (const algorithm of [...new Set(group.indices.map(index => records[index].algorithm))]) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = algorithmNames[algorithm] || algorithm;
        button.setAttribute("aria-pressed", String(record.algorithm === algorithm));
        button.addEventListener("click", () => {
            const choices = group.indices.filter(index => records[index].algorithm === algorithm);
            activate(choices.find(index => records[index].heuristic === record.heuristic) ?? choices[0]);
        });
        byId("algorithms").append(button);
    }
    const heuristics = [...new Set(group.indices.filter(index => records[index].algorithm === record.algorithm).map(index => records[index].heuristic))];
    byId("heuristicGroup").hidden = !informed(record);
    setOptions(byId("heuristic"), heuristics.map(name => [name, heuristicNames[name] || name || "None"]), record.heuristic);
    byId("heuristic").disabled = heuristics.length < 2;
    byId("heuristicNote").textContent = heuristics.length < 2 ? "Only this heuristic was recorded." : "Compare the baseline with your design.";
}

function renderSummary() {
    const record = current();
    const messages = {
        ok: "This recorded run passed the available local checks.",
        no_solution: "The supplied reference facts say this map is unreachable. No solution is a valid result here.",
        local_only: "Custom map: replay uses your own model, not an independent world validator.",
        wrong_answer: "The result disagreed with a stated expectation. Review the diagnostic beside the map.",
        time_limit: "The run exceeded its wall-clock limit. Check loops, imports, and duplicate handling.",
        resource_limit: "The run exceeded its expansion budget. Check repeated states and stale entries.",
        not_implemented: "A required function is still unfinished. Complete it, then run this case again.",
        runtime_error: "The code raised an exception. Review the diagnostic and reported file/line."
    };
    byId("runTitle").textContent = algorithmLabel(record) + (informed(record) ? " · " + (heuristicNames[record.heuristic] || record.heuristic) : "");
    byId("status").textContent = verdicts[record.status] || "Unknown result";
    byId("status").dataset.tone = tone(record);
    byId("statusMessage").textContent = messages[record.status] || "Review the saved diagnostic.";
    byId("cost").textContent = display(record.cost);
    byId("moves").textContent = display(record.length);
    byId("expanded").textContent = display(record.expansions);
    byId("runtime").textContent = Number(record.seconds || 0).toFixed(4) + " seconds on the recording machine";
    byId("validation").textContent = record.validation_scope || "Local replay and public diagnostics; staff grading is separate.";
    byId("diagnostic").hidden = !needsAttention(record);
    byId("errorSummary").textContent = String(record.error || messages[record.status] || "No diagnostic was saved.").slice(0, 240);
    byId("nextStep").textContent = "Next: " + (record.hint || "Rerun the smallest failing public case before generating all experiments.");
    byId("errorDetails").textContent = [record.error, record.location, record.hint].filter(Boolean).join("\n\n") || "No additional diagnostic was recorded.";
    byId("routeView").disabled = !record.path?.length;
    byId("searchView").disabled = !record.expanded?.length;
    byId("routeView").title = record.path?.length ? "Replay the courier's returned route" : "No successful route was recorded";
    byId("searchView").title = record.expanded?.length ? "Inspect states actually expanded by this algorithm" : "No expansions were recorded";
    const issues = records.filter(needsAttention).length;
    byId("nextIssue").disabled = !issues;
    byId("nextIssue").textContent = issues ? "Next issue · " + issues + " runs" : "No issues recorded";
}

function renderComparison() {
    const group = maps[mapForRecord[active]];
    const indices = group.indices.filter(index => byId("resultFilter").value !== "failed" || needsAttention(records[index]));
    byId("results").replaceChildren();
    for (const index of indices) {
        const record = records[index];
        const row = document.createElement("tr");
        if (index === active) row.classList.add("selected");
        const name = document.createElement("td");
        name.textContent = algorithmLabel(record);
        if (informed(record)) {
            const subtitle = document.createElement("small");
            subtitle.textContent = heuristicNames[record.heuristic] || record.heuristic;
            name.append(subtitle);
        }
        row.append(name);
        const result = document.createElement("td");
        const label = document.createElement("span");
        label.className = "result";
        label.dataset.tone = tone(record);
        label.textContent = record.status === "ok" ? "Passed" : verdicts[record.status] || record.status;
        result.append(label);
        row.append(result);
        for (const value of [record.cost, record.expansions]) {
            const cell = document.createElement("td");
            cell.textContent = display(value);
            row.append(cell);
        }
        const action = document.createElement("td");
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "View";
        button.setAttribute("aria-label", "View " + algorithmLabel(record) + (informed(record) ? " with " + (heuristicNames[record.heuristic] || record.heuristic) : ""));
        button.addEventListener("click", () => activate(index));
        action.append(button);
        row.append(action);
        byId("results").append(row);
    }
    byId("noComparison").hidden = indices.length > 0;
    byId("recordingCount").textContent = group.indices.length === 1 ? "Only one run is in this file. Use Compare all algorithms in the terminal app to produce comparisons." : "Costs, expansions, and runtime describe this run, not a universal algorithm ranking.";
}

function renderPlayback() {
    const record = current();
    const sequence = frames();
    step = Math.max(0, Math.min(step, sequence.length - 1));
    byId("frame").max = Math.max(0, sequence.length - 1);
    byId("frame").value = step;
    for (const name of ["play", "restart", "frame"]) byId(name).disabled = sequence.length < 2;
    byId("previous").disabled = !sequence.length || step === 0;
    byId("next").disabled = !sequence.length || step >= sequence.length - 1;
    byId("routeView").setAttribute("aria-pressed", String(mode === "path"));
    byId("searchView").setAttribute("aria-pressed", String(mode === "expanded"));
    byId("viewHelp").textContent = mode === "path" ? "The faint line previews the returned route; the solid line shows movement so far." : "Each step inspects a hypothetical state. These jumps are not the courier moving.";
    const state = sequence[step];
    byId("stepLabel").textContent = !state ? "No animation recorded" : mode === "path" ? (step ? "Move " + step + " of " + (sequence.length - 1) : "Start · " + (sequence.length - 1) + " moves") : "Expansion " + (step + 1) + " of " + sequence.length;
    byId("position").textContent = state ? "Position: row " + state.row + ", column " + state.column : "";
    byId("pickup").textContent = state ? "Pickup held: " + (state.has_key ? "yes" : "no") : "";
    byId("currentCost").textContent = state && mode === "path" && state.cost_so_far !== undefined ? "Cost so far: " + state.cost_so_far : "";
    if (!state) {
        byId("stepTitle").textContent = "Nothing to animate yet";
        byId("stepExplanation").textContent = record.status === "no_solution" ? "The search returned no route. Inspect recorded exploration if available." : "The run did not record this sequence. Read the diagnostic or rerun the case from the terminal app.";
    } else if (mode === "expanded") {
        byId("stepTitle").textContent = "Inspecting state " + (step + 1);
        byId("stepExplanation").textContent = "The algorithm requested legal actions at this position with this pickup state. Repeated coordinates can represent different inventory states.";
    } else if (step === 0) {
        byId("stepTitle").textContent = "Courier at the start";
        byId("stepExplanation").textContent = "Press Play to follow the returned actions, or use Step to inspect one move at a time.";
    } else {
        const action = (record.actions || [])[step - 1] || "Move";
        const collected = state.has_key && !sequence[step - 1].has_key;
        const surcharge = record.map[state.row]?.[state.column] === "w";
        byId("stepTitle").textContent = "Move " + step + ": " + action.toLowerCase();
        byId("stepExplanation").textContent = collected ? "Pickup collected. Doors can now be used." : step === sequence.length - 1 ? "The returned route is complete. Check its total cost and compare another algorithm." : surcharge ? "Entered expensive terrain: this tile costs 5 to enter." : "Follow the solid trail; the remaining planned route is faint.";
    }
    drawBoard(record, sequence, state);
}

function drawBoard(record, sequence, state) {
    const height = record.map.length;
    const width = record.map[0].length;
    const tile = Math.min(66, 760 / width, 310 / height);
    const canvas = byId("grid");
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.ceil(width * tile * ratio);
    canvas.height = Math.ceil(height * tile * ratio);
    canvas.style.width = width * tile + "px";
    canvas.style.aspectRatio = width + " / " + height;
    const context = canvas.getContext("2d");
    context.scale(ratio, ratio);
    const colours = {"#": "#304957", w: "#b9dbe8", D: "#ecc99b", K: "#dfcfea", G: "#bde0cb", S: "#d4e7e3"};
    record.map.forEach((row, rowIndex) => [...row].forEach((symbol, column) => {
        context.fillStyle = colours[symbol] || "#fbfcfa";
        context.fillRect(column * tile, rowIndex * tile, tile - 1, tile - 1);
    }));
    if (mode === "path" && sequence.length) {
        drawLine(context, sequence, tile, "#c8d7d8", 3);
        drawLine(context, sequence.slice(0, step + 1), tile, "#286f73", 5);
    } else if (mode === "expanded") {
        for (const inspected of sequence.slice(0, step + 1)) {
            context.fillStyle = "rgba(228,177,54,.35)";
            context.fillRect(inspected.column * tile + 3, inspected.row * tile + 3, tile - 7, tile - 7);
        }
    }
    record.map.forEach((row, rowIndex) => [...row].forEach((symbol, column) => {
        if (symbol === ".") return;
        context.fillStyle = symbol === "#" ? "#e4eff0" : "#284653";
        context.font = "bold " + Math.max(10, tile * .23) + "px system-ui";
        context.fillText(symbol, column * tile + tile * .12, rowIndex * tile + tile * .29);
        if (symbol === "w") context.fillText("5", column * tile + tile * .69, rowIndex * tile + tile * .84);
    }));
    if (state) {
        context.fillStyle = state.has_key ? "#82559d" : "#226c74";
        context.strokeStyle = "#fff";
        context.lineWidth = 2;
        context.beginPath();
        context.arc((state.column + .5) * tile, (state.row + .56) * tile, tile * .19, 0, Math.PI * 2);
        context.fill();
        context.stroke();
    }
    canvas.setAttribute("aria-label", maps[mapForRecord[active]].title + ", " + width + " columns by " + height + " rows. " + byId("stepTitle").textContent + ". " + byId("position").textContent);
}

function drawLine(context, sequence, tile, colour, thickness) {
    if (sequence.length < 2) return;
    context.beginPath();
    context.strokeStyle = colour;
    context.lineWidth = thickness;
    context.lineJoin = "round";
    context.lineCap = "round";
    sequence.forEach((state, index) => {
        const screenX = (state.column + .5) * tile;
        const screenY = (state.row + .56) * tile;
        if (!index) context.moveTo(screenX, screenY);
        else context.lineTo(screenX, screenY);
    });
    context.stroke();
}

function move(delta) {
    stop();
    step += delta;
    renderPlayback();
}

function togglePlay() {
    if (timer) { stop(); return; }
    if (frames().length < 2) return;
    if (step >= frames().length - 1) step = 0;
    renderPlayback();
    byId("play").textContent = "Pause";
    timer = setInterval(() => {
        step += 1;
        renderPlayback();
        if (step >= frames().length - 1) stop();
    }, Number(byId("speed").value));
}

byId("map").addEventListener("change", () => {
    const choices = maps[Number(byId("map").value)].indices;
    const previous = current();
    activate(choices.find(index => records[index].algorithm === previous.algorithm && records[index].heuristic === previous.heuristic) ?? choices.find(index => records[index].algorithm === previous.algorithm) ?? choices[0]);
});
byId("heuristic").addEventListener("change", () => activate(maps[mapForRecord[active]].indices.find(index => records[index].algorithm === current().algorithm && records[index].heuristic === byId("heuristic").value)));
byId("resultFilter").addEventListener("change", renderComparison);
byId("nextIssue").addEventListener("click", () => {
    const issues = records.map((record, index) => needsAttention(record) ? index : -1).filter(index => index >= 0);
    if (issues.length) activate(issues[(issues.indexOf(active) + 1) % issues.length]);
});
for (const [identifier, view] of [["routeView", "path"], ["searchView", "expanded"]]) {
    byId(identifier).addEventListener("click", () => { stop(); mode = view; step = 0; renderPlayback(); });
}
byId("previous").addEventListener("click", () => move(-1));
byId("next").addEventListener("click", () => move(1));
byId("restart").addEventListener("click", () => { stop(); step = 0; renderPlayback(); });
byId("frame").addEventListener("input", () => { stop(); step = Number(byId("frame").value); renderPlayback(); });
byId("play").addEventListener("click", togglePlay);
byId("speed").addEventListener("change", () => { if (timer) { stop(); togglePlay(); } });
document.addEventListener("keydown", event => {
    if (!records.length || ["INPUT", "SELECT", "TEXTAREA", "BUTTON", "SUMMARY"].includes(event.target.tagName) || event.target.isContentEditable) return;
    if (event.key === " ") { event.preventDefault(); togglePlay(); }
    else if (event.key === "ArrowLeft") { event.preventDefault(); move(-1); }
    else if (event.key === "ArrowRight") { event.preventDefault(); move(1); }
    else if (["Home", "End"].includes(event.key)) { event.preventDefault(); stop(); step = event.key === "Home" ? 0 : frames().length - 1; renderPlayback(); }
});

if (records.length) {
    setOptions(byId("map"), maps.map((group, index) => [index, group.title]), 0);
    activate(0);
} else {
    byId("workspace").hidden = true;
    byId("empty").hidden = false;
    byId("nextIssue").disabled = true;
    byId("nextIssue").textContent = "No recorded runs";
}
