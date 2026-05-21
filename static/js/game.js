const socket = io();
let myPlayerNumber = null;
let isCoven = false;

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

function applyRoleData(d) {
    myPlayerNumber = d.player_number;

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
    document.getElementById("coven-chat-panel").style.display = "flex";

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
        div.innerHTML = `<span class="pnum">#${p.player_number}</span><span>${p.nickname}</span>`;
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

socket.on("phase_change", (data) => {
    document.getElementById("phase-label").innerText = data.phase    || "—";
    document.getElementById("phase-sub").innerText   = data.sub_phase || "—";
    document.getElementById("phase-timer").innerText = data.duration  || "—";

    const isNight = (data.phase || "").toLowerCase().includes("night");
    document.body.classList.toggle("night-phase", isNight);

    if (isCoven) {
        document.getElementById("coven-input").disabled    = !isNight;
        document.getElementById("coven-send-btn").disabled = !isNight;
    }
});

socket.on("phase_tick", (data) => {
    document.getElementById("phase-timer").innerText = data.seconds;
});

socket.on("coven_message", (data) => {
    const container = document.getElementById("coven-messages");
    const placeholder = container.querySelector(".coven-msg-placeholder");
    if (placeholder) placeholder.remove();

    const div = document.createElement("div");
    div.className = "coven-msg";
    div.innerHTML = `<span class="coven-sender">#${data.player_number}</span>${data.message}`;
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