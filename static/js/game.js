const socket = io();
let myPlayerNumber = null;
let isCoven = false;
let myRoleInfo = null;
let myLandlubbers = [];
let covenRoles   = {};
let revealedLiving = {};

const stored = sessionStorage.getItem("roleData");
if (stored) {
    const data = JSON.parse(stored);
    applyRoleData(data);
    sessionStorage.removeItem("roleData");
}

const covenStored = sessionStorage.getItem("covenData");
if (covenStored) {
    const data = JSON.parse(covenStored);
    showCovenPanel(data.coven);
    sessionStorage.removeItem("covenData");
}

const revealedRoles = {};

const DAY_ABILITY_ROLES  = ["Mayor", "Prosecutor", "Deputy", "Conjurer"];
const DUAL_TARGET_ROLES  = ["Witch"];
const GUESS_ROLES        = ["Ritualist"];
const MULTI_GUESS_ROLES = ["Doomsayer"];

function buildActionPanel(players) {
    const panel = document.getElementById("action-panel");
    if (!panel || !myRoleInfo) return;

    panel.innerHTML = "";

    const role = myRoleInfo.role;

        if (role === "Doomsayer") {
        panel.innerHTML = `<div class="action-label">Doom 3 players — all must be correct:</div>`;
        for (let i = 1; i <= 3; i++) {
            const row = document.createElement("div");
            row.className = "doom-guess-row";
            row.innerHTML = `
                <select class="doom-target-select" data-idx="${i}">
                    <option value="">Player...</option>
                    ${living.map(p => `<option value="${p.player_number}">#${p.player_number} ${p.nickname}</option>`).join("")}
                </select>
                <input class="doom-role-input" data-idx="${i}" type="text" placeholder="Their role..." />
            `;
            panel.appendChild(row);
        }
        panel.insertAdjacentHTML("beforeend", `
            <div class="action-buttons">
                <button onclick="submitDoomAction()">Cast Doom</button>
                <button onclick="skipAction()">Skip</button>
            </div>
            <div id="action-status"></div>
        `);
        return;
    }

    if (role === "Pirate") {
        panel.innerHTML = `
            <div class="action-label">Choose action:</div>
            <div class="pirate-actions">
                <label><input type="radio" name="pirate-action" value="scour" checked> Scour (is this a landlubber?)</label><br>
                <label><input type="radio" name="pirate-action" value="plunder"> Plunder (basic attack, costs 1 charge)</label>
            </div>
            <div class="action-label">Target:</div>
        `;
        const list = document.createElement("div");
        list.id = "action-target-list";
        living.forEach(p => {
            const btn = document.createElement("button");
            btn.className = "action-target-btn";
            btn.dataset.pnum = p.player_number;
            btn.textContent = `#${p.player_number} ${p.nickname}`;
            btn.onclick = () => selectTarget(p.player_number, "target");
            list.appendChild(btn);
        });
        panel.appendChild(list);
        panel.insertAdjacentHTML("beforeend", `
            <div class="action-buttons">
                <button onclick="submitPirateAction()">Submit</button>
                <button onclick="skipAction()">Skip</button>
            </div>
            <div id="action-status"></div>
        `);
        return;
    }

    if (DAY_ABILITY_ROLES.includes(role)) {
        panel.innerHTML = `<div class="action-note">Your ability is used during the day.</div>`;
        return;
    }

    const living = players.filter(p => p.alive && p.player_number !== myPlayerNumber);

    panel.innerHTML = `<div class="action-label">Choose a target:</div>`;
    const list = document.createElement("div");
    list.id = "action-target-list";
    living.forEach(p => {
        const btn = document.createElement("button");
        btn.className = "action-target-btn";
        btn.dataset.pnum = p.player_number;
        btn.textContent = `#${p.player_number} ${p.nickname}`;
        btn.onclick = () => selectTarget(p.player_number, "target");
        list.appendChild(btn);
    });
    panel.appendChild(list);

    if (DUAL_TARGET_ROLES.includes(role)) {
        const row2 = document.createElement("div");
        row2.id = "action-target2-row";
        row2.innerHTML = `<div class="action-label">Send them to:</div>`;
        const list2 = document.createElement("div");
        list2.id = "action-target2-list";
        living.forEach(p => {
            const btn = document.createElement("button");
            btn.className = "action-target-btn target2";
            btn.dataset.pnum = p.player_number;
            btn.textContent = `#${p.player_number} ${p.nickname}`;
            btn.onclick = () => selectTarget(p.player_number, "target2");
            list2.appendChild(btn);
        });
        row2.appendChild(list2);
        panel.appendChild(row2);
    }

    if (GUESS_ROLES.includes(role)) {
        const guessRow = document.createElement("div");
        guessRow.id = "action-guess-row";
        guessRow.innerHTML = `
            <div class="action-label">Guess their role:</div>
            <input id="action-guess-input" type="text" placeholder="Role name..." />
        `;
        panel.appendChild(guessRow);
    }
    
    if (myRoleInfo.role === "Archmage") {
        const COVEN_ROLES = [
            "Medusa","Illusionist","Conjurer","Ritualist",
            "Poisoner","Wilding","Witch","Hex Master","Archmage"
        ];
        const row = document.createElement("div");
        row.innerHTML = `<div class="action-label">Retrain into:</div>`;
        const select = document.createElement("select");
        select.id = "archmage-role-select";
        COVEN_ROLES.forEach(r => {
            const opt = document.createElement("option");
            opt.value = r;
            opt.textContent = r;
            select.appendChild(opt);
        });
        row.appendChild(select);
        panel.appendChild(row);
    }

    panel.insertAdjacentHTML("beforeend", `
        <div class="action-buttons">
            <button onclick="submitAction()">Submit</button>
            <button onclick="skipAction()">Skip</button>
        </div>
        <div id="action-status"></div>
    `);
}

let selectedTargets = { target: null, target2: null };

function selecTarget(pnum, slot) {
    selectedTargets[slot] = pnum;
    const cls = slot === "target" ? "action-target-btn:not(.target2)" : "action-target-btn.target2";
    document.querySelectorAll(`.action-target-btn${slot === "target2" ? ".target2" : ":not(.target2)"}`)
        .forEach(btn => btn.classList.toggle("selected", parseInt(btn.dataset.pnum) === pnum));
}

function submitAction() {
    const role     = myRoleInfo?.role;
    const guess    = document.getElementById("action-guess-input")?.value.trim() || null;
    const new_role = role === "Archmage"
        ? document.getElementById("archmage-role-select")?.value || null
        : null;
    socket.emit("submit_night_action", {
        target:   selectedTargets.target,
        target2:  DUAL_TARGET_ROLES.includes(role) ? selectedTargets.target2 : null,
        guess:    GUESS_ROLES.includes(role) ? guess : null,
        new_role: new_role,
    });
}

let selectedDayTarget = null;

function buildVotePanel(players) {
    const list = document.getElementById("vote-player-list");
    if (!list) return;
    list.innerHTML = "";
    players.filter(p => p.alive && p.player_number !== myPlayerNumber).forEach(p => {
        const btn = document.createElement("button");
        btn.className = "action-target-btn vote-btn";
        btn.dataset.pnum = p.player_number;
        btn.textContent = `#${p.player_number} ${p.nickname}`;
        btn.onclick = () => {
            list.querySelectorAll(".vote-btn").forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            castVote(p.player_number);
        };
        list.appendChild(btn);
    });
}

function castVote(target) {
    socket.emit("cast_vote", { target });
}

function castVerdict(verdict) {
    socket.emit("cast_verdict", { verdict });
}

function buildDayAbilityPanel(players) {
    const body = document.getElementById("day-ability-body");
    if (!body || !myRoleInfo) return;
    const role   = myRoleInfo.role;
    const living = players.filter(p => p.alive && p.player_number !== myPlayerNumber);
    body.innerHTML = "";

    if (role === "Mayor") {
        body.innerHTML = `
            <div class="action-label">Reveal yourself as Mayor to gain 3 votes.</div>
            <div class="action-buttons">
                <button class="btn-wood" onclick="useDayAbility(null)">Reveal</button>
            </div>
            <div id="day-ability-status"></div>
        `;
        return;
    }

    body.innerHTML = `<div class="action-label">Choose a target:</div>`;
    const list = document.createElement("div");
    list.id = "day-ability-target-list";
    living.forEach(p => {
        const btn = document.createElement("button");
        btn.className = "action-target-btn";
        btn.dataset.pnum = p.player_number;
        btn.textContent = `#${p.player_number} ${p.nickname}`;
        btn.onclick = () => {
            list.querySelectorAll(".action-target-btn").forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            selectedDayTarget = p.player_number;
        };
        list.appendChild(btn);
    });
    body.appendChild(list);

    const label = role === "Deputy" ? "Shoot" : role === "Conjurer" ? "Conjure" : "Prosecute";
    body.insertAdjacentHTML("beforeend", `
        <div class="action-buttons">
            <button class="btn-wood" onclick="useDayAbility(selectedDayTarget)">${label}</button>
        </div>
        <div id="day-ability-status"></div>
    `);
}

function useDayAbility(target) {
    socket.emit("use_day_ability", { target });
}

function submitDoomAction() {
    const guesses = [];
    for (let i = 1; i <= 3; i++) {
        const target = parseInt(document.querySelector(`.doom-target-select[data-idx="${i}"]`)?.value);
        const role   = document.querySelector(`.doom-role-input[data-idx="${i}"]`)?.value.trim();
        if (!target || !role) {
            const s = document.getElementById("action-status");
            if (s) s.textContent = "Fill in all 3 guesses.";
            return;
        }
        guesses.push({ target, role });
    }
    socket.emit("submit_night_action", { guesses });
}

function submitPirateAction() {
    const action_type = document.querySelector('input[name="pirate-action"]:checked')?.value || "scour";
    socket.emit("submit_night_action", {
        action_type,
        target: selectedTargets.target,
    });
}

function skipAction() {
    socket.emit("submit_night_action", { target: null, target2: null, guess: null });
}

function applyRoleData(d) {
    myRoleInfo = d;
    myPlayerNumber = d.player_number;
    sessionStorage.setItem("myPlayerNumber", d.player_number);

    document.getElementById("player-label").innerText = `#${d.player_number} · ${d.nickname}`;
    document.getElementById("rc-name").innerText      = d.role;
    document.getElementById("rc-category").innerText  = d.category;
    document.getElementById("rc-desc").innerText      = d.ability_description;
    document.getElementById("rc-atk").innerText       = d.attack;
    document.getElementById("rc-def").innerText       = d.defense;
    document.getElementById("rc-charges").innerText   = d.charges === -1 ? "∞" : d.charges;

    const factionEl = document.getElementById("rc-faction");
    factionEl.innerText = d.faction;
    factionEl.className = `role-faction ${d.faction}`;

    renderDebugTerminal(d);
}

function renderDebugTerminal(d) {
    const flag = v => v
        ? '<span style="color:#8ab88a">YES</span>'
        : '<span style="color:#a85858">NO</span>';

    document.getElementById("debug-terminal").innerHTML =
`<span style="color:#c4921a">── PLAYER ───────────────────────────</span>
Number   : ${d.player_number}
Nickname : ${d.nickname}

<span style="color:#c4921a">── ROLE ─────────────────────────────</span>
Role      : ${d.role}
Faction   : ${d.faction}
Alignment : ${d.alignment}
Category  : ${d.category}

<span style="color:#c4921a">── STATS ────────────────────────────</span>
Attack    : ${d.attack}
Defense   : ${d.defense}

<span style="color:#c4921a">── ABILITY ──────────────────────────</span>
Type      : ${d.ability_type}
Charges   : ${d.charges === -1 ? "∞" : d.charges}

<span style="color:#c4921a">── FLAGS ────────────────────────────</span>
Unique          : ${flag(d.unique)}
Astral          : ${flag(d.astral)}
Roleblock Immune: ${flag(d.roleblock_immune)}
Control Immune  : ${flag(d.control_immune)}`;
}

function showCovenPanel(covenList) {
    isCoven = true;
    covenList.forEach(p => { covenRoles[p.player_number] = p.role; });
    const names = covenList.map(p => `#${p.player_number} ${p.nickname} (${p.role})`).join(", ");
    const term = document.getElementById("debug-terminal");
    term.innerHTML += `\n\n<span style="color:#c4921a">── COVEN ────────────────────────────</span>\n${names}`;
}

function renderPlayerList(players) {
    const container = document.getElementById("player-list");
    container.innerHTML = "";
    const living = players.filter(p => p.alive).length;
    document.getElementById("living-count").innerText = `${living} alive`;

    players.forEach(p => {
        const div = document.createElement("div");
        div.className = "player-entry" +
            (p.alive ? "" : " dead") +
            (p.player_number === myPlayerNumber ? " me" : "");
        const roleTag = covenRoles[p.player_number]
            ? `<span class="prole coven">${covenRoles[p.player_number]}</span>`
            : revealedLiving[p.player_number]
            ? `<span class="prole revealed">${revealedLiving[p.player_number]}</span>`
            : "";
        div.innerHTML = `<span class="pnum">#${p.player_number}</span><span>${p.nickname}</span>${roleTag}`;
        container.appendChild(div);
    });
}

function sendCovenMessage() {
    const input = document.getElementById("coven-input");
    const msg = input.value.trim();
    if (!msg) return;
    socket.emit("coven_chat", { message: msg });
    input.value = "";
}

function toggleMoreInfo() {
    const body = document.getElementById("more-info-body");
    const btn  = document.getElementById("more-info-btn");
    const open = body.classList.toggle("open");
    btn.classList.toggle("active", open);
}

function renderGraveyard(players) {
    const container = document.getElementById("graveyard-list");
    const dead = players.filter(p => !p.alive);

    document.getElementById("dead-count").innerText =
        dead.length ? `${dead.length} dead` : "—";

    if (!dead.length) {
        container.innerHTML = `<div class="player-placeholder">No deaths yet</div>`;
        return;
    }

    container.innerHTML = "";
    dead.forEach(p => {
        const role = revealedRoles[p.player_number] || null;
        const div = document.createElement("div");
        div.className = "graveyard-entry";
        div.innerHTML = `
            <span class="pnum">#${p.player_number}</span>
            <span class="gname">${p.nickname}</span>
            <span class="grole">${role ? role : "Unknown"}</span>
        `;
        container.appendChild(div);
    });
}

function sendMessage() {
    const input = document.getElementById("chat-input");
    const msg   = input.value.trim();
    if (!msg) return;
    const isNight = document.body.classList.contains("night-phase");
    socket.emit(isNight && isCoven ? "coven_chat" : "send_message", { message: msg });
    input.value = "";
}

socket.on("connect", () => {
    const lobbyId      = sessionStorage.getItem("lobbyId");
    const playerNumber = parseInt(sessionStorage.getItem("myPlayerNumber"));
    if (lobbyId) {
        socket.emit("rejoin_game", { lobby_id: lobbyId, player_number: playerNumber || null });
    }
});

socket.on("role_assigned", (data) => {
    applyRoleData(data);
});

socket.on("coven_reveal", (data) => {
    showCovenPanel(data.coven);
});

socket.on("game_state_update", (data) => {
    if (data.players) {
        renderPlayerList(data.players);
        renderGraveyard(data.players);
    }
    if (data.phase) document.getElementById("phase-label").innerText = data.phase;
});

socket.on("phase_tick", (data) => {
    document.getElementById("phase-timer").innerText = data.seconds;
});

socket.on("coven_message", (data) => {
    const container = document.getElementById("chat-messages");
    if (!container) return;
    const div = document.createElement("div");
    div.className = "chat-msg coven-msg";
    div.innerHTML = `<span class="chat-sender">#${data.player_number}</span>${data.message}`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
});

socket.on("death_announcement", (data) => {
    revealedRoles[data.player_number] = data.role;

    const container = document.getElementById("graveyard-list");
    const entry = container.querySelector(`[data-pnum="${data.player_number}"]`);
    if (entry) {
        entry.querySelector(".grole").innerText = data.role;
    }
});

socket.on("trial_start", (data) => {
    accusedPlayerNumber = data.accused;
    document.getElementById("phase-sub").innerText = `On trial: #${data.accused}`;
});

socket.on("verdict_reveal", (data) => {
    const result = data.guilty ? "GUILTY" : "NOT GUILTY";
    const lines = Object.entries(data.verdicts)
        .map(([pnum, v]) => `#${pnum}: ${v}`)
        .join("\n");
    console.log(`Verdict: ${result}\n${lines}`);
});

socket.on("game_over", (data) => {
    document.getElementById("phase-label").innerText = "Game Over";
    document.getElementById("phase-sub").innerText   = `${data.winner} wins!`;
    document.getElementById("phase-timer").innerText = "";
});

let accusedPlayerNumber = null;

socket.on("phase_change", (data) => {
    const phase   = data.phase     || "";
    const sub     = data.sub_phase || "";
    const isNight = phase.toLowerCase().includes("night");

    document.getElementById("phase-label").innerText = phase || "—";
    document.getElementById("phase-sub").innerText   = sub   || "—";
    document.getElementById("phase-timer").innerText = data.duration || "—";

    document.body.classList.toggle("night-phase", isNight);

    if (sub !== "defense" && sub !== "last_words") {
        accusedPlayerNumber = null;
    }

        const isAccused   = myPlayerNumber === accusedPlayerNumber;
    const blocked     = ["voting", "verdict", "silence"];
    const canTownChat = !isNight
        && !blocked.includes(sub)
        && (sub !== "defense"    || isAccused)
        && (sub !== "last_words" || isAccused);
    const canChat = canTownChat || (isNight && isCoven && sub !== "silence");

    const townInput   = document.getElementById("chat-input");
    const townSendBtn = document.getElementById("chat-send-btn");
    if (townInput)   townInput.disabled   = !canChat;
    if (townSendBtn) townSendBtn.disabled = !canChat;

    const actionPanel = document.getElementById("action-panel");
    if (isNight && sub === "") {
        selectedTargets = { target: null, target2: null };
        if (actionPanel) actionPanel.style.display = "";
        const currentPlayers = Array.from(document.querySelectorAll(".player-entry"))
            .map(el => ({
                player_number: parseInt(el.querySelector(".pnum").textContent.replace("#", "")),
                nickname: el.querySelector("span:last-child").textContent,
                alive: !el.classList.contains("dead"),
            }));
        buildActionPanel(currentPlayers);
    } else {
        if (actionPanel) actionPanel.style.display = "none";
    }

    const votePanel = document.getElementById("vote-panel");
    if (votePanel) {
        votePanel.style.display = sub === "voting" ? "" : "none";
        if (sub === "voting") {
            const currentPlayers = Array.from(document.querySelectorAll(".player-entry"))
                .map(el => ({
                    player_number: parseInt(el.querySelector(".pnum").textContent.replace("#", "")),
                    nickname: el.querySelector("span:last-child").textContent,
                    alive: !el.classList.contains("dead"),
                }));
            buildVotePanel(currentPlayers);
        }
    }

    const verdictPanel = document.getElementById("verdict-panel");
    if (verdictPanel) verdictPanel.style.display = sub === "verdict" ? "" : "none";

    const dayAbilityPanel = document.getElementById("day-ability-panel");
    if (dayAbilityPanel && myRoleInfo && DAY_ABILITY_ROLES.includes(myRoleInfo.role)) {
        const hiddenSubs = ["verdict", "defense", "last_words", "silence"];
        const show = !isNight && !hiddenSubs.includes(sub);
        dayAbilityPanel.style.display = show ? "" : "none";
        if (show) {
            const currentPlayers = Array.from(document.querySelectorAll(".player-entry"))
                .map(el => ({
                    player_number: parseInt(el.querySelector(".pnum").textContent.replace("#", "")),
                    nickname: el.querySelector("span:last-child").textContent,
                    alive: !el.classList.contains("dead"),
                }));
            buildDayAbilityPanel(currentPlayers);
        }
    }
});

socket.on("chat_error", (data) => {
    console.warn("Chat blocked:", data.message);
});

socket.on("votes_updated", (data) => {
    const threshold = document.getElementById("vote-threshold");
    if (threshold) threshold.textContent = `Need ${data.threshold}`;
    const tally = document.getElementById("vote-tally");
    if (!tally) return;
    tally.innerHTML = "";
    Object.entries(data.tally).forEach(([pnum, count]) => {
        const div = document.createElement("div");
        div.className = "vote-tally-row";
        div.textContent = `#${pnum}: ${count} vote${count !== 1 ? "s" : ""}`;
        tally.appendChild(div);
    });
});

socket.on("verdicts_updated", (data) => {
    const tally = document.getElementById("verdict-tally");
    if (!tally) return;
    const counts = { guilty: 0, innocent: 0, abstain: 0 };
    Object.values(data.verdicts).forEach(v => { if (counts[v] !== undefined) counts[v]++; });
    tally.innerHTML = `
        <span class="v-guilty">Guilty: ${counts.guilty}</span>
        <span class="v-innocent">Innocent: ${counts.innocent}</span>
        <span class="v-abstain">Abstain: ${counts.abstain}</span>
    `;
});

socket.on("chat_message", (data) => {
    const container = document.getElementById("chat-messages");
    if (!container) return;
    const div = document.createElement("div");
    div.className = "chat-msg";
    div.innerHTML = `<span class="chat-sender">#${data.player_number} ${data.nickname}</span>${data.message}`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
});

socket.on("action_confirmed", (data) => {
    const status = document.getElementById("action-status");
    if (status) status.textContent = data.target !== null
        ? `Action submitted — targeting #${data.target}`
        : "Action skipped.";
});

socket.on("action_error", (data) => {
    const status = document.getElementById("action-status");
    if (status) status.textContent = `Error: ${data.message}`;
});

socket.on("night_feedback", (data) => {
    const container = document.getElementById("feedback-list");
    if (!container) return;
    container.innerHTML = "";
    data.messages.forEach(msg => {
        const div = document.createElement("div");
        div.className = "feedback-msg";
        div.textContent = msg;
        container.appendChild(div);
    });
    const panel = document.getElementById("feedback-panel");
    if (panel) panel.style.display = "";
});

socket.on("retrain_offer", (data) => {
    const accept = confirm(
        `The Archmage wants to retrain you into ${data.new_role}.\n` +
        `${data.ability_description}\n\nAccept?`
    );
    socket.emit("respond_to_retrain", { accept });
});

socket.on("retrain_declined", (data) => {
    console.log(`Player #${data.target} declined your retrain.`);
});

socket.on("exe_target_info", (data) => {
    const panel = document.getElementById("feedback-panel");
    const list  = document.getElementById("feedback-list");
    if (!list) return;
    const div = document.createElement("div");
    div.className = "feedback-msg ne-info";
    div.textContent = `Your target: #${data.target_number} ${data.target_nickname} (${data.target_role}). Get them lynched to win.`;
    list.appendChild(div);
    if (panel) panel.style.display = "";
});

socket.on("pirate_landlubbers", (data) => {
    myLandlubbers = data.roles;
    const list = document.getElementById("feedback-list");
    if (!list) return;
    const div = document.createElement("div");
    div.className = "feedback-msg ne-info";
    div.textContent = `Your landlubbers are: ${data.roles.join(", ")}. Win by ensuring they all die.`;
    list.appendChild(div);
    const panel = document.getElementById("feedback-panel");
    if (panel) panel.style.display = "";
});

socket.on("ne_departure", (data) => {
    const container = document.getElementById("chat-messages");
    if (!container) return;
    const div = document.createElement("div");
    div.className = "chat-msg ne-departure";
    div.textContent = `✦ ${data.nickname} (${data.role}) has left town.`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
});

socket.on("doom_announcement", (data) => {
    const container = document.getElementById("chat-messages");
    if (!container) return;
    const div = document.createElement("div");
    div.className = "chat-msg doom-msg";
    div.textContent = `☠ ${data.nickname} has been doomed by the Doomsayer!`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
});

socket.on("ne_win_pending", (data) => {
    const list = document.getElementById("feedback-list");
    if (!list) return;
    const div = document.createElement("div");
    div.className = "feedback-msg win-msg";
    div.textContent = data.message || "You have achieved your goal!";
    list.appendChild(div);
    const panel = document.getElementById("feedback-panel");
    if (panel) panel.style.display = "";
});

socket.on("jester_haunt_later", (data) => {
    const list = document.getElementById("feedback-list");
    if (!list) return;
    const div = document.createElement("div");
    div.className = "feedback-msg ne-info";
    div.textContent = data.message;
    list.appendChild(div);
    const panel = document.getElementById("feedback-panel");
    if (panel) panel.style.display = "";
});

socket.on("jester_haunt_prompt", (data) => {
    const panel = document.getElementById("action-panel");
    if (!panel) return;
    panel.innerHTML = `<div class="action-label">You were lynched! Choose who to haunt:</div>`;
    const list = document.createElement("div");
    data.guilty_voters.forEach(pnum => {
        const btn = document.createElement("button");
        btn.className = "action-target-btn haunt-btn";
        btn.textContent = `#${pnum}`;
        btn.onclick = () => {
            document.querySelectorAll(".haunt-btn").forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            socket.emit("submit_haunt", { target: pnum });
        };
        list.appendChild(btn);
    });
    panel.appendChild(list);
    panel.insertAdjacentHTML("beforeend", `<div id="action-status"></div>`);
    panel.style.display = "";
});

socket.on("haunt_confirmed", (data) => {
    const status = document.getElementById("action-status");
    if (status) status.textContent = `Haunt locked in on #${data.target}.`;
});

socket.on("day_ability_used", (data) => {
    if (data.role === "Mayor") {
        revealedLiving[data.player_number] = "Mayor";
        const currentPlayers = Array.from(document.querySelectorAll(".player-entry"))
            .map(el => ({
                player_number: parseInt(el.querySelector(".pnum").textContent.replace("#", "")),
                nickname: el.querySelector("span:not(.pnum):not(.prole)").textContent,
                alive: !el.classList.contains("dead"),
            }));
        renderPlayerList(currentPlayers);
        
};    const status = document.getElementById("day-ability-status");
    if (data.role === "Mayor") {
        const container = document.getElementById("chat-messages");
        if (container) {
            const div = document.createElement("div");
            div.className = "chat-msg system-msg";
            div.textContent = `#${data.player_number} ${data.nickname} has revealed as Mayor!`;
            container.appendChild(div);
        }
    } else {
        if (status) status.textContent = data.killed ? "Target eliminated!" : "Target was too strong.";
    }
});