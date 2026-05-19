console.log("lobby.js loaded");

const socket = io();
let selectedLobbyId = null;
let currentLobbyId  = null;
let isHost          = false;
let myRoleData = null;


function setInLobby(lobbyId, host) {
    currentLobbyId = lobbyId;
    isHost = !!host;
    document.getElementById("create-btn").style.display = "none";
    document.getElementById("leave-btn").style.display  = "";
    document.getElementById("join-btn").style.display   = "none";
    document.getElementById("lock-btn").style.display   = isHost ? "" : "none";
}

function setOutOfLobby() {
    currentLobbyId  = null;
    selectedLobbyId = null;
    isHost          = false;
    document.getElementById("create-btn").style.display = "";
    document.getElementById("leave-btn").style.display  = "none";
    document.getElementById("lock-btn").style.display   = "none";
    document.getElementById("join-btn").style.display   = "";
    document.getElementById("join-btn").disabled        = true;
}

function showPregame() {
    document.querySelector(".lobby-table-container").style.display = "none";
    document.querySelector(".preview-area").style.display          = "none";
    document.querySelector(".browser-footer").style.display        = "none";
    document.getElementById("pregame-panel").style.display         = "flex";
}


function renderPregamePlayers(players) {
    const container = document.getElementById("pregame-player-list");
    container.innerHTML = "";
    players.forEach(p => {
        const div = document.createElement("div");
        div.className = "pregame-player-entry";
        div.innerHTML = `<span class="pnum">#${p.player_number}</span><span>${p.name}</span>`;
        container.appendChild(div);
    });
}


function openModal() {
    const modal = document.getElementById("create-modal");
    const input = document.getElementById("lobby-name-input");
    const username = localStorage.getItem("username") || "Player";
    input.value = username + "'s game";
    modal.classList.add("open");
    input.focus();
    input.select();
}

function closeModal() {
    document.getElementById("create-modal").classList.remove("open");
}

function confirmCreate() {
    const name = document.getElementById("lobby-name-input").value.trim();
    if (!name) return;
    socket.emit("create_lobby", {
        name: localStorage.getItem("username") || "Player",
        username: localStorage.getItem("username") || "Player",
        lobby_name: name
    });
    closeModal();
}

function leaveLobby() {
    if (!currentLobbyId) return;
    socket.emit("leave_lobby", {});
}

function lockLobby() {
    if (!currentLobbyId || !isHost) return;
    socket.emit("lock_lobby", { lobby_id: currentLobbyId });
}

function unlockLobby() {
    if (!currentLobbyId || !isHost) return;
    socket.emit("unlock_lobby", { lobby_id: currentLobbyId });
}

function joinSelected() {
    if (!selectedLobbyId) return;
    socket.emit("join_lobby", {
        lobby_id: selectedLobbyId,
        name: localStorage.getItem("username") || "Guest",
        username: localStorage.getItem("username") || "Player",

    });
}

function joinRandom() {
    socket.emit("join_random", {
        name: localStorage.getItem("username") || "Guest",
        username: localStorage.getItem("username") || "Player",
    });
}

function refreshLobbies() {
    socket.emit("request_lobbies");
}

function returnHome() {
    window.location.href = "/";
}

const ANONYMOUS_NAMES = [
    "Cotton Mather", "Deodat Lawson", "Edward Bishop", "Giles Corey",
    "James Bayley", "James Russel", "John Hathorne", "John Proctor",
    "John Willard", "Jonathan Corwin", "Samuel Parris", "Samuel Sewall",
    "Thomas Danforth", "William Hobbs", "William Phips", "Abigail Hobbs",
    "Alice Young", "Ann Hibbins", "Ann Putnam", "Ann Sears",
    "Betty Parris", "Dorothy Good", "Lydia Dustin", "Martha Corey",
    "Mary Eastey", "Mary Johnson", "Mary Warren", "Sarah Bishop",
    "Sarah Good", "Sarah Wildes"
];

function anonymousName() {
    const name = ANONYMOUS_NAMES[Math.floor(Math.random() * ANONYMOUS_NAMES.length)];
    document.getElementById("nickname-input").value = name;
    submitNickname();
}

function startGame() {
    if (!currentLobbyId || !isHost) return;
    socket.emit("start_game", { lobby_id: currentLobbyId });
    document.getElementById("pregame-host-controls").style.display = "none";
}

function submitNickname() {
    const input = document.getElementById("nickname-input");
    const nickname = input.value.trim();
    if (!nickname || !currentLobbyId) return;
    socket.emit("submit_nickname", { lobby_id: currentLobbyId, nickname });
    input.value = "";
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
Desc      : ${d.ability_description}

<span style="color:#c4921a">── FLAGS ────────────────────────────</span>
Unique          : ${flag(d.unique)}
Astral          : ${flag(d.astral)}
Roleblock Immune: ${flag(d.roleblock_immune)}
Control Immune  : ${flag(d.control_immune)}`;
}

socket.on("connect", () => {
    const el = document.getElementById("status");
    el.innerText = "Connected";
    el.classList.add("connected");
    socket.emit("request_lobbies");
});

socket.on("disconnect", () => {
    const el = document.getElementById("status");
    el.innerText = "Disconnected";
    el.classList.remove("connected");
});

socket.on("role_assigned", (data) => {
    myRoleData = data;
});

socket.on("game_start", () => {
    document.getElementById("pregame-panel").style.display = "none";
    const gv = document.getElementById("game-view");
    gv.style.display = "flex";
    if (myRoleData) renderDebugTerminal(myRoleData);
});

socket.on("lobby_unlocked", () => {
    document.getElementById("pregame-panel").style.display          = "none";
    document.querySelector(".lobby-table-container").style.display  = "";
    document.querySelector(".preview-area").style.display           = "";
    document.querySelector(".browser-footer").style.display         = "";
    document.getElementById("lock-btn").style.display               = "";
});

socket.on("lobby_created", (data) => setInLobby(data.lobby_id, true));
socket.on("lobby_joined",  (data) => setInLobby(data.lobby_id, false));
socket.on("lobby_left",    ()     => setOutOfLobby());

socket.on("lobby_error", (data) => {
    console.warn("Lobby error:", data.message);
});

function showPregame() {
    document.querySelector(".lobby-table-container").style.display = "none";
    document.querySelector(".preview-area").style.display          = "none";
    document.querySelector(".browser-footer").style.display        = "none";
    document.getElementById("pregame-panel").style.display         = "flex";
    if (isHost) {
    document.getElementById("pregame-host-controls").style.display = "flex";
}
}

socket.on("pregame_start", (data) => {
    showPregame();
    renderPregamePlayers(data.players);
});

socket.on("pregame_tick", (data) => {
    const el = document.getElementById("countdown-display");
    if (el) el.innerText = data.seconds;
});

socket.on("pregame_end", () => {
    const el = document.getElementById("countdown-display");
    if (el) el.innerText = "0";
});

socket.on("player_list_update", (data) => {
    renderPregamePlayers(data.players);
});

socket.on("lobby_list", (lobbies) => {
    const container = document.getElementById("lobbies");
    if (!container) return;

    if (!lobbies || lobbies.length === 0) {
        container.innerHTML = `
            <tr class="empty-row">
                <td colspan="4">No lobbies found — create one or refresh</td>
            </tr>`;
        return;
    }

    container.innerHTML = "";

    lobbies.forEach(lobby => {
        const playerCount = (lobby.player_list || []).length;
        const maxPlayers  = lobby.max_players || 15;
        const displayName = lobby.lobby_name || lobby.host || lobby.id;

        const tr = document.createElement("tr");
        tr.dataset.lobbyId = lobby.id;
        if (lobby.id === selectedLobbyId) tr.classList.add("selected");

        tr.innerHTML = `
            <td>
                <div class="lobby-name-cell">
                    <i class="fa-solid fa-heart lobby-icon" aria-hidden="true"></i>
                    ${displayName}
                </div>
            </td>
            <td class="host-cell">${lobby.host || "—"}</td>
            <td class="roles-cell">${lobby.role_list || "—"}</td>
            <td class="players-cell">${playerCount} / ${maxPlayers}</td>
        `;

        tr.addEventListener("click", () => {
            if (currentLobbyId) return;
            document.querySelectorAll("#lobbies tr").forEach(r => r.classList.remove("selected"));
            tr.classList.add("selected");
            selectedLobbyId = lobby.id;
            document.getElementById("join-btn").disabled = false;
        });

        container.appendChild(tr);
    });
});