  // Prevent form submission on Enter key press
  document.getElementById('pymodule_configurations').addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
    }
  });
