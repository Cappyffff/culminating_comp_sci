console.log("lobby.js loaded");

const socket = io();
let selectedLobbyId     = null;
let currentLobbyId      = null;
let isHost              = false;
let myRoleData          = null;
let availableRoleLists  = {};
let selectedRoleListKey = null;
let currentRoleListConfig = null;

let customList        = { town: [], coven: [], any: [] };
let currentSection    = "town";
let currentPlayerCount = 15;

const ROLE_KEYS = [
    "Sheriff","Tracker","Psychic","Deputy","Vigilante","Mayor","Prosecutor",
    "Cleric","Trapper","Socialite","TavernKeeper",
    "Medusa","Illusionist","Conjurer","Ritualist","Poisoner","Wilding",
    "Witch","HexMaster","Archmage"
];

const CATEGORIES = [
    "Town Investigative","Town Killing","Town Power","Town Protective","Town Support",
    "Coven Deception","Coven Killing","Coven Power","Coven Utility"
];


function createCustomSelect(id, className, options) {
    const wrapper = document.createElement("div");
    wrapper.className = "custom-select " + className;
    wrapper.id = id;
    wrapper.value = options[0];

    wrapper.innerHTML = `
        <div class="custom-select-trigger">${options[0]}</div>
        <ul class="custom-select-dropdown">
            ${options.map((o, i) => `<li data-value="${o}" class="${i===0?'selected':''}">${o}</li>`).join("")}
        </ul>
    `;

    const trigger = wrapper.querySelector(".custom-select-trigger");
    const items   = wrapper.querySelectorAll("li");

    trigger.addEventListener("click", () => wrapper.classList.toggle("open"));
    items.forEach(item => {
        item.addEventListener("click", () => {
            trigger.textContent = item.textContent;
            wrapper.value = item.dataset.value;
            items.forEach(i => i.classList.remove("selected"));
            item.classList.add("selected");
            wrapper.classList.remove("open");
        });
    });

    return wrapper;
}

function setInLobby(lobbyId, host) {
    currentLobbyId = lobbyId;
    isHost = !!host;
    document.getElementById("create-btn").style.display       = "none";
    document.getElementById("leave-btn").style.display        = "";
    document.getElementById("join-btn").style.display         = "none";
    document.getElementById("lock-btn").style.display         = isHost ? "" : "none";
    document.getElementById("host-settings-btn").style.display = isHost ? "" : "none";
    document.getElementById("view-rolelist-btn").style.display = isHost ? "none" : "";
}

function setOutOfLobby() {
    currentLobbyId  = null;
    selectedLobbyId = null;
    isHost          = false;
    document.getElementById("create-btn").style.display       = "";
    document.getElementById("leave-btn").style.display        = "none";
    document.getElementById("lock-btn").style.display         = "none";
    document.getElementById("join-btn").style.display         = "";
    document.getElementById("join-btn").disabled              = true;
    document.getElementById("host-settings-btn").style.display = "none";
    document.getElementById("view-rolelist-btn").style.display = "none";
}

function showPregame() {
    document.querySelector(".lobby-table-container").style.display = "none";
    document.querySelector(".preview-area").style.display          = "none";
    document.querySelector(".browser-footer").style.display        = "none";
    document.getElementById("pregame-panel").style.display         = "flex";
    if (isHost) {
        document.getElementById("pregame-host-controls").style.display = "flex";
    }
}


function renderPregamePlayers(players) {
    currentPlayerCount = players.length;
    updateSlotCounter();

    const container = document.getElementById("pregame-player-list");
    container.innerHTML = "";
    players.forEach(p => {
        const div = document.createElement("div");
        div.className = "pregame-player-entry";

        const kickBtn = isHost
            ? `<button class="btn-kick" onclick="kickPlayer(${p.player_number})" title="Kick player">
                   <i class="fa-solid fa-xmark"></i>
               </button>`
            : "";

        div.innerHTML = `
            <span class="pnum">#${p.player_number}</span>
            <span style="flex:1">${p.name}</span>
            ${kickBtn}
        `;
        container.appendChild(div);
    });
}

function openModal() {
    const modal = document.getElementById("create-modal");
    const input = document.getElementById("lobby-name-input");
    input.value = (localStorage.getItem("username") || "Player") + "'s game";
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
        name:       localStorage.getItem("username") || "Player",
        username:   localStorage.getItem("username") || "Player",
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
        name:     localStorage.getItem("username") || "Guest",
        username: localStorage.getItem("username") || "Player",
    });
}

function refreshLobbies() {
    socket.emit("request_lobbies");
}

function returnHome() {
    window.location.href = "/";
}

function startGame() {
    if (!currentLobbyId || !isHost) return;
    socket.emit("start_game", { lobby_id: currentLobbyId });
    document.getElementById("pregame-host-controls").style.display = "none";
}

function kickPlayer(playerNumber) {
    if (!currentLobbyId || !isHost) return;
    socket.emit("kick_player", { lobby_id: currentLobbyId, player_number: playerNumber });
}


const ANONYMOUS_NAMES = [
    "Cotton Mather","Deodat Lawson","Edward Bishop","Giles Corey",
    "James Bayley","James Russel","John Hathorne","John Proctor",
    "John Willard","Jonathan Corwin","Samuel Parris","Samuel Sewall",
    "Thomas Danforth","William Hobbs","William Phips","Abigail Hobbs",
    "Alice Young","Ann Hibbins","Ann Putnam","Ann Sears",
    "Betty Parris","Dorothy Good","Lydia Dustin","Martha Corey",
    "Mary Eastey","Mary Johnson","Mary Warren","Sarah Bishop",
    "Sarah Good","Sarah Wildes"
];

function anonymousName() {
    const name = ANONYMOUS_NAMES[Math.floor(Math.random() * ANONYMOUS_NAMES.length)];
    document.getElementById("nickname-input").value = name;
    submitNickname();
}

function submitNickname() {
    const input    = document.getElementById("nickname-input");
    const nickname = input.value.trim();
    if (!nickname || !currentLobbyId) return;
    socket.emit("submit_nickname", { lobby_id: currentLobbyId, nickname });
    input.value = "";
}


function renderDebugTerminal(d) {
    const flag = v =>
        v ? '<span style="color:#8ab88a">YES</span>'
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


function openHostSettings() {
    socket.emit("request_rolelists");
    const section = document.getElementById("settings-rolelist-section");
    if (section) section.style.display = currentLobbyId && document.getElementById("pregame-panel").style.display === "flex" ? "none" : "";
    document.getElementById("host-settings-modal").classList.add("open");
}

function closeHostSettings() {
    document.getElementById("host-settings-modal").classList.remove("open");
}

function confirmHostSettings() {
    socket.emit("set_role_list", { lobby_id: currentLobbyId, list_key: selectedRoleListKey });
    closeHostSettings();
}

function renameLobby() {
    if (!currentLobbyId || !isHost) return;
    const name = document.getElementById("settings-lobby-name").value.trim();
    if (!name) return;
    socket.emit("rename_lobby", { lobby_id: currentLobbyId, name });
    document.getElementById("settings-lobby-name").value = "";
}

function renderSettingsRoleList() {
    const container = document.getElementById("settings-rolelist-options");
    container.innerHTML = "";

    const entries = [
        [null, { name: "Random", description: "No guaranteed roles. Fully random within faction caps." }],
        ...Object.entries(availableRoleLists)
    ];

    entries.forEach(([key, list]) => {
        const div = document.createElement("div");
        div.className = "rolelist-option" + (selectedRoleListKey === key ? " selected" : "");
        div.innerHTML = `<span class="rolelist-name">${list.name}</span>
                         <span class="rolelist-desc">${list.description}</span>`;
        div.onclick = () => {
            container.querySelectorAll(".rolelist-option").forEach(el => el.classList.remove("selected"));
            div.classList.add("selected");
            selectedRoleListKey = key;
        };
        container.appendChild(div);
    });
}


function openCustomListModal() {
    closeHostSettings();  
    currentSection = "town";
    updateSectionTabs();
    document.getElementById("new-slot-type").value = "any";
    renderCustomSlotList();
    updateSlotCounter();
    renderSlotDetailInput();
    document.getElementById("custom-list-modal").classList.add("open");
}

function closeCustomListModal() {
    document.getElementById("custom-list-modal").classList.remove("open");
}

function clearCustomList() {
    customList = { town: [], coven: [], any: [] };
    renderCustomSlotList();
    updateSlotCounter();
}

function switchSection(section) {
    currentSection = section;
    updateSectionTabs();
    renderCustomSlotList();
}

function updateSectionTabs() {
    ["town", "coven", "any"].forEach(s => {
        const tab = document.getElementById(`tab-${s}`);
        if (tab) tab.classList.toggle("active", s === currentSection);
    });
}

function slotLabel(slot) {
    switch (slot.type) {
        case "specific":      return `Specific — ${slot.role}`;
        case "pool":          return `Pool — ${(slot.roles || []).join(" / ")}`;
        case "category":      return `Category — ${slot.category}`;
        case "random_town":   return "Random Town";
        case "random_coven":  return "Random Coven";
        case "common_town":   return "Common Town";
        case "common_coven":  return "Common Coven";
        case "any":           return "Any";
        default:              return slot.type;
    }
}

function renderCustomSlotList() {
    const list      = customList[currentSection];
    const container = document.getElementById("custom-slot-list");
    container.innerHTML = "";

    if (list.length === 0) {
        const empty = document.createElement("div");
        empty.className = "slot-list-empty";
        empty.textContent = "No slots — add one on the right";
        container.appendChild(empty);
        return;
    }

    list.forEach((slot, idx) => {
        const row = document.createElement("div");
        row.className = "custom-slot-row";
        row.innerHTML = `
            <span class="custom-slot-label">${slotLabel(slot)}</span>
            <button class="btn-kick" onclick="removeSlot('${currentSection}', ${idx})" title="Remove">
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;
        container.appendChild(row);
    });
}

function removeSlot(section, idx) {
    customList[section].splice(idx, 1);
    renderCustomSlotList();
    updateSlotCounter();
}

function totalSlots() {
    return customList.town.length + customList.coven.length + customList.any.length;
}

function updateSlotCounter() {
    const total   = totalSlots();
    const counter = document.getElementById("custom-slot-counter");
    const warning = document.getElementById("custom-slot-warning");
    if (counter) counter.textContent = `${total} slot${total !== 1 ? "s" : ""}`;
    if (warning) warning.style.display = total > currentPlayerCount ? "" : "none";
}

function onSlotTypeChange() {
    renderSlotDetailInput();
}

function renderSlotDetailInput() {
    const type      = document.getElementById("new-slot-type").value;
    const container = document.getElementById("new-slot-detail");
    container.innerHTML = "";

    if (type === "pool") {
        const label = document.createElement("label");
        label.className = "modal-label";
        label.textContent = "Roles — select multiple for one to be picked at random every game!";
        container.appendChild(label);

        const pool = document.createElement("div");
        pool.id = "slot-pool-roles";
        pool.className = "pool-toggle-list";
        ROLE_KEYS.forEach(key => {
            const item = document.createElement("div");
            item.className = "pool-toggle-item";
            item.textContent = key;
            item.dataset.value = key;
            item.addEventListener("click", () => item.classList.toggle("selected"));
            pool.appendChild(item);
        });
        container.appendChild(pool);

    } else if (type === "category") {
        const label = document.createElement("label");
        label.className = "modal-label";
        label.textContent = "Category";
        container.appendChild(label);

        container.appendChild(createCustomSelect("slot-category", "modal-select", CATEGORIES));

    } else {
        const note = document.createElement("span");
        note.style.cssText = "font-size:11px; color:#5a4a28; letter-spacing:1px; font-style:italic;";
        const descriptions = {
            random_town:  "Draws any Town role.",
            random_coven: "Draws any Coven role (subject to cap).",
            common_town:  "Draws any Town role except Town Power.",
            common_coven: "Draws Coven Utility or Coven Deception only.",
            any:          "Draws any role from either faction (subject to cap).",
        };
        note.textContent = descriptions[type] || "";
        container.appendChild(note);
    }
}

function openRoleListView() {
    if (!currentRoleListConfig) return;
    const container = document.getElementById("rolelist-view-content");
    container.innerHTML = "";

    ["town", "coven", "any"].forEach(section => {
        const slots = currentRoleListConfig[section] || [];
        if (!slots.length) return;

        const header = document.createElement("div");
        header.style.cssText = "font-size:10px; letter-spacing:2px; color:#c4921a; text-transform:uppercase; margin-top:8px;";
        header.textContent = section;
        container.appendChild(header);

        slots.forEach(slot => {
            const row = document.createElement("div");
            row.className = "custom-slot-row";
            row.innerHTML = `<span class="custom-slot-label">${slotLabel(slot)}</span>`;
            container.appendChild(row);
        });
    });

    document.getElementById("rolelist-view-modal").classList.add("open");
}

function addSlot() {
    const type = document.getElementById("new-slot-type").value;
    let slot;

    if (type === "pool") {
        const items = document.querySelectorAll("#slot-pool-roles .pool-toggle-item.selected");
        const roles = Array.from(items).map(i => i.dataset.value);
        if (roles.length < 1) {
            alert("Select at least one role.");
            return;
        }
        slot = roles.length === 1 ? { type: "specific", role: roles[0] } : { type: "pool", roles };

    } else if (type === "category") {
        const category = document.getElementById("slot-category")?.value;
        if (!category) return;
        slot = { type: "category", category };

    } else {
        slot = { type };
    }

    customList[currentSection].push(slot);
    renderCustomSlotList();
    updateSlotCounter();
}

function confirmCustomList() {
    if (totalSlots() === 0) {
        alert("Add at least one slot before applying.");
        return;
    }
    if (totalSlots() > currentPlayerCount) {
        alert("Too many slots for the current player count. Remove some first.");
        return;
    }
    socket.emit("set_custom_role_list", {
        lobby_id: currentLobbyId,
        config:   customList
    });
    closeCustomListModal();
}

function voteRoleList(key) {
    if (!currentLobbyId) return;
    socket.emit("vote_role_list", { lobby_id: currentLobbyId, list_key: key });
}

function renderVoteTally(votes) {
    const container = document.getElementById("pregame-vote-tally");
    if (!container) return;
    container.innerHTML = "";
    if (Object.keys(votes).length === 0) {
        container.innerHTML = "<span>No votes yet</span>";
        return;
    }
    Object.entries(votes).forEach(([key, count]) => {
        const name = availableRoleLists[key]?.name ?? key ?? "Random";
        const div = document.createElement("div");
        div.textContent = `${name}: ${count} vote${count !== 1 ? "s" : ""}`;
        container.appendChild(div);
    });
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
    const gv = document.getElementById("game-view");
    if (gv && gv.style.display === "flex") renderDebugTerminal(data);
});

socket.on("coven_reveal", (data) => {
    sessionStorage.setItem("covenData", JSON.stringify(data));
});

socket.on("game_start", (data) => {
    if (myRoleData) sessionStorage.setItem("roleData", JSON.stringify(myRoleData));
    if (data.lobby_id) sessionStorage.setItem("lobbyId", data.lobby_id);
    window.location.href = "/game";
});

socket.on("lobby_unlocked", () => {
    document.getElementById("pregame-panel").style.display         = "none";
    document.querySelector(".lobby-table-container").style.display = "";
    document.querySelector(".preview-area").style.display          = "";
    document.querySelector(".browser-footer").style.display        = "";
    document.getElementById("lock-btn").style.display              = isHost ? "" : "none";
    document.getElementById("host-settings-btn").style.display     = isHost ? "" : "none";
});

socket.on("lobby_created", (data) => setInLobby(data.lobby_id, true));
socket.on("lobby_joined",  (data) => setInLobby(data.lobby_id, false));
socket.on("lobby_left",    ()     => setOutOfLobby());

socket.on("kicked", (data) => {
    alert(data.message || "You were kicked from the lobby.");
    setOutOfLobby();
    socket.emit("request_lobbies");
});

socket.on("lobby_error", (data) => {
    console.warn("Lobby error:", data.message);
});

socket.on("pregame_start", (data) => {
    showPregame();
    renderPregamePlayers(data.players);
});

socket.on("rolelist_data", (data) => {
    availableRoleLists = data;
    renderSettingsRoleList();
});

socket.on("role_list_updated", (data) => {
    selectedRoleListKey = data.is_custom ? null : data.selected_list;
    currentRoleListConfig = data.config || null;
    const label = document.getElementById("pregame-rolelist-label");
    if (label) {
        label.textContent = data.list_name
            ? `Role List: ${data.list_name}${data.is_custom ? ` (${data.slot_count} slots defined)` : ""}`
            : "";
    }
    socket.emit("request_lobbies");
});

socket.on("lobby_renamed", (data) => {
    console.log("Lobby renamed to:", data.name);
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

        let rolesDisplay;
        if (lobby.has_custom) {
            rolesDisplay = "Custom";
        } else if (lobby.selected_list) {
            rolesDisplay = availableRoleLists[lobby.selected_list]?.name ?? lobby.selected_list;
        } else {
            rolesDisplay = "Random";
        }

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
            <td class="roles-cell">${rolesDisplay}</td>
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

document.addEventListener("click", e => {
    if (!e.target.closest(".custom-select")) {
        document.querySelectorAll(".custom-select.open")
                .forEach(el => el.classList.remove("open"));
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const slotTypeEl = document.getElementById("new-slot-type");
    if (!slotTypeEl) return;
    slotTypeEl.value = "any";

    const trigger = slotTypeEl.querySelector(".custom-select-trigger");
    trigger.addEventListener("click", () => slotTypeEl.classList.toggle("open"));

    slotTypeEl.querySelectorAll("li").forEach(item => {
        item.addEventListener("click", () => {
            slotTypeEl.value = item.dataset.value;
            trigger.textContent = item.textContent;
            slotTypeEl.querySelectorAll("li").forEach(i => i.classList.remove("selected"));
            item.classList.add("selected");
            slotTypeEl.classList.remove("open");
            onSlotTypeChange();
        });
    });
});

socket.on("vote_update", (data) => {
    renderVoteTally(data.votes);
});