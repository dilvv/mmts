


function startPeriodicWebStatusUpdate(checkPERIOD) {
    console.log("Periodic web status update activated.");

    // Start periodic update every 2 seconds
    const intervalId = setInterval(() => {
        socket.emit("socket_get_web_status");
    }, checkPERIOD);

    // Listen for the response
    socket.on("socket_get_web_status_response", (data) => {
        console.log(`[Got web status] ${data.status}`);
        updateButtonStates(data.status);
    });

    // Store the interval ID for possible stopping
    return intervalId;
}

// Listen for the start command from the server
// after #btnCONN clicked, activate periodical update service
socket.on("start_periodic_update", () => {
    startPeriodicWebStatusUpdate(2000); // timer in ms.
});
