// Function to set background color based on status
function showLog(theID) {
    document.getElementById(theID).addEventListener("click", function() {
        // Redirect to the route that serves the log file content
        window.open(`/showLogpage?btnID=${theID}`, "_blank");
    });
}
function showTestLog(theID) {
    document.getElementById(theID).addEventListener("click", function() {
        // Redirect to the route that serves the log file content
        window.open("/show_logpage?btnID=test", "_blank");
    });
}

showTestLog("LED1L");
showTestLog("LED1C");
showTestLog("grayLight");
