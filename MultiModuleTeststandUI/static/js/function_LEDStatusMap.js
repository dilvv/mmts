const btnStatusAndColor = {
    "idle": "green",
    "run": "rellow",
    "error": "red",
    "busy": "yellow",
    "connectlost": "gray",
    "none": "gray"
};

// Function to set background color based on status
function updateLEDStatus(theID,status) {
    if (btnStatusAndColor.hasOwnProperty(status)) {
        document.getElementById(theID).style.background = btnStatusAndColor[status];
    } else {
        console.error(`button ID "${theID}" got invalid status: "${status}"`);
        document.getElementById(theID).style.background = "transparent";  // Set to default or transparent
    }
}

//// test function
//function _changeLightStatus() {
//    // this is a test function 
//    var theID = 'grayLight';
//
//    document.getElementById(theID).style.background = 'green';
//
//    setTimeout(() => {
//        document.getElementById(theID).style.background = 'blue';
//    }, 3000); // Switch after 3 seconds
//
//    setTimeout(() => {
//        document.getElementById(theID).style.background = 'red';
//    }, 6000); // Switch after another 3 seconds
//
//    setTimeout(() => { changeLightStatus('grayLight', 'busy'); }, 12000);
//
//}


//// test function
//$(document).ready(function() {
//    const socket = io();
//    socket.on('moduleStatusError', (lightID) => {
//        document.getElementById(lightID).style.background = "red";   console.log("light "+lightID+" got error");
//    } );
//    socket.on('moduleStatusRun', (lightID) => {
//        document.getElementById(lightID).style.background = "green"; console.log("light "+lightID+" is running");
//    } );
//    socket.on('moduleStatusIdle', (lightID) => {
//        document.getElementById(lightID).style.background = "gray"; console.log("light "+lightID+" is idle");
//    } );
//    _changeLightStatus();
//});

