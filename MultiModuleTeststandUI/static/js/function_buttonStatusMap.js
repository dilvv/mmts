const statusButtonMap = {
    "none": ["#btnCONN", ".jobmode"],
    "job_select": ["#btnINIT", "#btnEXIT", ".jobmode"],
    "startup"  : ["#btnEXIT"],
    'initializing': ["#btnEXIT"],
    "initialized": ["#btnCONF", "#btnEXIT"],
    "configured": ["#btnEXEC", "#btnCONF", "#btnEXIT"],
    "running": ["#btnSTOP", "#btnEXIT"],
    "stopped": ["#btnCONF", "#btnEXIT"], // asdf
    "idle": ["#btnCONF", "#btnEXIT"], // asdf
    "error": ["#btnEXIT"],
    // "destroyed": ["#btnINIT", "#btnEXIT", ".jobmode"],
    "halt": ["#btnINIT", "#btnEXIT", ".jobmode"], // asdf
    "wait": ["#btnEXIT"] // asdf
};
//    "none":
//    "connected":
//    "initialized":
//    "configured":
//    "running": Once all jobs are reported as running.
//    "stopped": Once all jobs are reported as stopped.
//    "idle":
//    "error":
//    "halt": 
//    "wait": used for initialize / run / stop / destroy buttons clicked. waiting for the result.


function updateButtonStates(status) {
    console.log(`[updateButtonStatus] got status ${status}`);
    //document.getElementById('server-status-content').innerHTML = status;
    $('#server-status-content').text(status);

    // Disable all buttons initially
    $(".ctrlbtn").prop("disabled", true);
    document.querySelectorAll(".jobmode").forEach( opt => opt.disabled = true );


    // Get the buttons to enable for the current status
    const buttonsToEnable = statusButtonMap[status] || [];
    buttonsToEnable.forEach(btnIdentifier => {
        //console.log(`set button ${btnIdentifier} !`);
        //#("#" + btnIdentifier).prop("disabled", false);
        if ('#' === btnIdentifier[0]) // search ID
        { document.getElementById(btnIdentifier.slice(1)).disabled = false; }
        if ('.' === btnIdentifier[0]) // search class
        {
          const buttons = document.querySelectorAll(btnIdentifier);
          if (buttons.length > 0) { buttons.forEach(btn => btn.disabled = false); }
        }
    });
}

