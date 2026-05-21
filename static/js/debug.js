const logsEl = document.getElementById("logs");
const lobbiesEl = document.getElementById("lobbies");
const gameEl = document.getElementById("game");

// Tab switching
document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.add("hidden"));
        btn.classList.add("active");
        document.getElementById(btn.dataset.tab).classList.remove("hidden");
    });
});

load();

async function load() {
    const res = await fetch(`/api/debug?key=${KEY}`);
    const data = await res.json();

    renderLogs(data.logs);
    renderLobbies(data.lobbies);
    renderGame(data.game);
}

function renderLogs(logs) {
    logsEl.innerHTML = "";

    logs.forEach(l => {
        const div = document.createElement("div");
        div.className = "log";
        div.innerHTML = `<b>[${l.time}] ${l.type}</b><br/>${l.message}`;
        logsEl.appendChild(div);
    });
}

function renderLobbies(lobbies) {
    lobbiesEl.innerHTML = "";

    lobbies.forEach(l => {
        const box = document.createElement("div");
        box.className = "lobby";

        box.innerHTML = `
            <b>Lobby ${l.id}</b><br/>
            Locked: ${l.locked}<br/>
            Roles: ${l.role_list.join(", ")}
        `;

        l.players.forEach(p => {
            const row = document.createElement("div");
            row.className = "player";

            const button = document.createElement("button");
            button.textContent = "Reveal";

            const roleSpan = document.createElement("span");
            roleSpan.className = "role hidden";
            roleSpan.textContent = "hidden";

            button.addEventListener("click", () => {
                reveal(p.sid, roleSpan);
            });

            row.innerHTML = `#${p.player_number} <span style="color:#aaa">${p.name}</span> <span style="color:#ffc000; font-size:11px;">(${p.username})</span> `;
            row.appendChild(button);
            row.appendChild(roleSpan);
            box.appendChild(row);
        });

        lobbiesEl.appendChild(box);
    });
}

function renderGame(game) {
    gameEl.innerHTML = "";

    if (!game) {
        gameEl.innerHTML = `<div class="log" style="color:#888">No active game.</div>`;
        return;
    }

    const header = document.createElement("div");
    header.className = "lobby";
    header.innerHTML = `<b>Phase:</b> ${game.phase} &nbsp; <b>Phase #:</b> ${game.phase_number}`;
    gameEl.appendChild(header);

    game.players.forEach(p => {
        const row = document.createElement("div");
        row.className = "player";

        const aliveColor = p.alive ? "#b3e6b3" : "#e66";
        const statusText = p.status_effects.length ? p.status_effects.join(", ") : "none";

        const button = document.createElement("button");
        button.textContent = "Reveal";

        const roleSpan = document.createElement("span");
        roleSpan.className = "role hidden";
        roleSpan.textContent = p.role || "No role";

        button.addEventListener("click", () => {
        reveal(p.sid, roleSpan);
        }); 

        row.innerHTML = `
            <span style="color:${aliveColor}">#${p.player_number} ${p.nickname}</span>
            <span style="color:#888; font-size:11px;"> ATK:${p.current_attack} DEF:${p.current_defense} | ${p.alignment || "?"} | fx: ${statusText}</span>
            &nbsp;
        `;
        row.appendChild(button);
        row.appendChild(roleSpan);

        gameEl.appendChild(row);
    });
}

async function reveal(sid, roleSpan) {
    const res = await fetch(`/api/debug/reveal-role?key=${KEY}&sid=${sid}`);
    const data = await res.json();

    if (!data.role) {
        roleSpan.textContent = "ERROR";
        return;
    }

    roleSpan.textContent = data.role;
    roleSpan.classList.remove("hidden");
}

document.getElementById("refresh").addEventListener("click", load);