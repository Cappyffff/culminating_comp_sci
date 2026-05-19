const logsEl = document.getElementById("logs");
const lobbiesEl = document.getElementById("lobbies");

load();

async function load() {
    const res = await fetch(`/api/debug?key=${KEY}`);
    const data = await res.json();

    renderLogs(data.logs);
    renderLobbies(data.lobbies);
}

function renderLogs(logs) {
    logsEl.innerHTML = "";

    logs.forEach(l => {
        const div = document.createElement("div");
        div.className = "log";

        div.innerHTML = `
            <b>[${l.time}] ${l.type}</b><br/>
            ${l.message}
        `;

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

            row.innerHTML = `#${p.player_number} <span style="color:#aaa">${p.name}</span> <span style="color:#ffc000; font-size:11px;">(${p.username})</span> <span style="color:#ffc000; font-size:9px; `;
            row.appendChild(button);
            row.appendChild(roleSpan);

            box.appendChild(row);
        });

        lobbiesEl.appendChild(box);
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