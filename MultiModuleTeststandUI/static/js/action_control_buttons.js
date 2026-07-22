function button_clicking_fetch(btnID) {
  document.getElementById(btnID).addEventListener("click", function() {
    fetch(`/${btnID}`) // fetch uses /btnID
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        console.log(`[${btnID}] Connect to server for fetching current web status ${JSON.stringify(data)}`);
        // function from static/js/function_buttonStatusMap.js
        updateButtonStates(data.btnSTATUS);
        Object.keys(data.LEDs).forEach(function(ledID) {
          var LEDstatus = data.LEDs[ledID];
          // function from static/js/function_LEDStatusMap.js
          updateLEDStatus(ledID,LEDstatus);
        });

        // update filled module ID
        Object.keys(data.moduleIDs).forEach(function(inputBOXid) {
          var moduleID = data.moduleIDs[inputBOXid];
          if ( moduleID )
            document.getElementById(inputBOXid).value = moduleID;
        });

        // to do: add other configurations
      })
      .catch(error => console.error('Error:', error));
  });
}

function button_clicking_configure(btnID) {
  // only used for 'btnCONF'
  $(document).ready(function() {
    const storedMessage = sessionStorage.getItem('message');
    if (storedMessage) { 
      $('#messageInput').val(storedMessage); 
    }

    $('form').off('submit').on('submit', function(event) {
      event.preventDefault();  // Prevent default form submission
      var formData = $(this).serialize();
      console.log('Module IDs configured');

      $.ajax({
        type: 'POST',
        url: '/task2/submit',
        data: formData,
        success: function(response) {
          if (response.status === 'success') {
            //console.log("[Configurations]" + response.message);
            console.log(`[Configurations] ${response.message}`);
            alert(response.message); // show additional textbox informing user.
            updateButtonStates("configured");
          } else {
            alert(`[UnableToConfigure] ${response.errors} \n\n ${response.message}`);
            console.error("Configuration failed: " + response.errors);
            updateButtonStates("error");
          }
        },
        error: function() {
          alert('An error occurred. Please try again.');
          console.error("Configuration failed: " + response.errors);
          updateButtonStates("error");
        }
      });
    }); // end of submit handler
  }); // end of document ready
}



function button_clicking_socketIO(btnID) {
  document.getElementById(btnID).addEventListener("click", function() {
    if ( btnID == "btnINIT" ) {
      // Get the selected radio button value
      // for button INITIALIZE : Collect radio field "jobmodule" selecting the job mode.
      const selectedOption = document.querySelector('input[name="jobmode"]:checked').value;

      socket.emit(btnID, {jobmode: selectedOption}); // socketio uses the same name as button ID
        
    } else { socket.emit(btnID); }

    // read feedback after request sent
    socket.on('btnSTATUS', (data) => {
      console.log(data.log);
      updateButtonStates(data.btnSTATUS);
    });
  });
}

//button_clicking_fetch    ('btnCONN');
//button_clicking_socketIO ('btnINIT');
//button_clicking_configure('btnCONF');
//button_clicking_socketIO ('btnEXEC');
//button_clicking_socketIO ('btnSTOP');
//button_clicking_socketIO ('btnEXIT');
