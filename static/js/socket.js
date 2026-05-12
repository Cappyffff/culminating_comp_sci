const socket = io();

socket.on("connect", () => {
    console.log("Connected:", socket.id);

    socket.emit("ping_test", {
        msg: "hello server"
    });
});

socket.on("connection_ack", (data) => {
    console.log("ACK:", data);
});

socket.on("pong_test", (data) => {
    console.log("PONG:", data);
});