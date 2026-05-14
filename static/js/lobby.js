console.log("lobby.js loaded");

const socket = io();

socket.on("connect", () => {
    document.getElementById("status").innerText = "Connected";

    // request initial state
    socket.emit("request_lobbies");
});

function createLobby() {
    socket.emit("create_lobby", {
        name: localStorage.getItem("username") || "Player"
    });
}

function joinLobby(id, username) {
    socket.emit("join_lobby", {
        lobby_id: id,
        name: username
    });
}

socket.on("lobby_list", (lobbies) => {
    console.log("🔥 lobby_list received:", lobbies);

    const container = document.getElementById("lobbies");

    if (!container) {
        console.error("❌ Missing #lobbies container");
        return;
    }

    container.innerHTML = "";

    lobbies.forEach(lobby => {
        const div = document.createElement("div");

        const username = localStorage.getItem("username") || "Guest";

        const players = (lobby.player_list || [])
            .map(p => p.name || "Unknown")
            .join(", ");

        div.innerHTML = `
            <p>
                <b>Host:</b> ${lobby.host} |
                <b>Players:</b> ${players}
            </p>
            <button onclick="joinLobby('${lobby.id}', '${username}')">
                Join
            </button>
            <hr>
        `;

        container.appendChild(div);
    });
});