console.log("lobby.js loaded");

const socket = io();

socket.on("connect", () => {
    document.getElementById("status").innerText = "Connected";
});

function createLobby() {
    socket.emit("create_lobby", {
        name: "Player"
    });
}

socket.on("lobby_list", (lobbies) => {
    const container = document.getElementById("lobbies");
    container.innerHTML = "";

    lobbies.forEach(lobby => {
        const div = document.createElement("div");
        const username = localStorage.getItem("username") || "Guest";

        div.innerHTML = `
            <p>
                <b>Host:</b> ${lobby.host} |
                <b>Players:</b> ${lobby.player_names.join(", ")}
            </p>
            <button onclick="joinLobby('${lobby.id}', '${username}')">Join</button>
            <hr>
        `;

        container.appendChild(div);
    });
});

function joinLobby(id, username) {
    socket.emit("join_lobby", {
        lobby_id: id,
        name: username
    });
}