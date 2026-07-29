function send_cmd(btnID) {
    fetch('/buttonClick_hub', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            'button_id': btnID,
        }),
    })
        .then(response => response.json())
        .then(data => {
            // Handle the response if needed
            console.log(data);
            //alert(data.status);
            //showMessage(data.status);
            showMessage2(data.indicator,data.message);
        })
        .catch(error => {
            console.error('Error:', error);
        });
}
function DisableMe(clickedBUTTONid, connectedBUTTONs) {
    // Disable the clicked button
    document.getElementById(clickedBUTTONid).disabled = true;

    // Enable all other buttons
    connectedBUTTONs.forEach(function(buttonId) {
        if (buttonId !== clickedBUTTONid) {
            document.getElementById(buttonId).disabled = false;
        }
    });
    send_cmd(clickedBUTTONid);

    // Add your additional logic here based on the clicked button
    console.log(clickedBUTTONid + " was clicked!");
}

function DisableMyGroup(clickedBUTTONid, correlatedGROUPs) { //asdf
    var classes = document.getElementById(clickedBUTTONid).classList;

    classes.forEach(function(my_group) {
        correlatedGROUPs.forEach(function(corr_group) {
            // Enable all buttons in group2
            var group2Buttons = document.getElementsByClassName(corr_group);
            if (corr_group !== my_group) {
                for (var i = 0; i < group2Buttons.length; i++) {
                    group2Buttons[i].disabled = false;
                }
            } else {
                for (var i = 0; i < group2Buttons.length; i++) {
                    group2Buttons[i].disabled = true;
                }
            }
        });
    });
    send_cmd(clickedBUTTONid);
}
// function showMessage(mesg) {
// 	  document.getElementById('messageBox').innerText = mesg;
// }
// function showMessage2(theID,mesg) {
// 	  document.getElementById('mesg'+theID).innerText = mesg;
// }


function showMessage(htmlCode) {
    // Get the reference to the message box
    var statusbox = document.getElementById('statusbox');

    // Display the message in the message box
    statusbox.innerHTML = htmlCode;
}

function toggleLock() {
    var button = document.getElementById('lockallbtn');
    var iconElement = document.getElementById('icon');
    var textElement = document.getElementById('text');

    // Toggle between different Font Awesome icons
    if (iconElement.classList.contains('fa-lock')) {
        iconElement.classList.remove('fa-lock');
        iconElement.classList.add('fa-lock-open');
        textElement.textContent = 'Unlock Sc';
    } else {
        iconElement.classList.remove('fa-lock-open');
        iconElement.classList.add('fa-lock');
        textElement.textContent = 'Lock Sc';
    }
}

function disableOtherButtons(clickedButton) {
    // Get all buttons on the page
    var buttons = document.getElementsByTagName('button');

    // // Loop through each button and disable it if it's not the clicked button
    // for (var i = 0; i < buttons.length; i++) {
    //     if (buttons[i] !== clickedButton) {
    //         buttons[i].disabled = true;
    //     }
    // }

    // Toggle the disabled state of all buttons except the clicked one
    for (var i = 0; i < buttons.length; i++) {
        if (buttons[i] !== clickedButton) {
            buttons[i].disabled = !buttons[i].disabled;
        }
    }
}

function enableButtons(clickedButton) {
    // Get all buttons on the page
    var buttons = document.getElementsByTagName('button');

    // Check if buttons are currently disabled
    var areButtonsDisabled = buttons[0].disabled;

    // Enable or disable buttons based on their current state
    for (var i = 0; i < buttons.length; i++) {
        buttons[i].disabled = !areButtonsDisabled;
    }
}

function fetchLog() {
    fetch('/fetch_logs')
        .then(response => response.text())
        .then(logs => {
            // Get the current timestamp
            var timestamp = new Date().toLocaleString();
            // Get the textarea element
            var logTextArea = document.getElementById('logbox');

            // Set fetched logs to the textarea
            logTextArea.value += timestamp + " | " + logs + '\n';

            // Scroll textarea to the bottom
            logTextArea.scrollTop = logTextArea.scrollHeight;
        })
        .catch(error => console.error('Error fetching logs:', error));
}

function inputWindow() {
    // Open a new window with a prompt for user input
    var userInput = prompt("Please enter the new board ID:");

    // If the user input is not null (i.e., they clicked 'OK'), display a greeting
    if (userInput !== null) {
        // Get the reference to the message box
        var statusbox = document.getElementById('statusbox');

        // Display the message in the message box
        statusbox.innerHTML = "Board " + userInput + " ready for test!";
        // alert("Hello, " + userInput + "! You entered: " + userInput);
    }

}
