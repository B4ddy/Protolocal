const websocket = new WebSocket('ws://' + window.location.hostname + ':8000/ws/motor_control/'); // Adjust the port if needed

        websocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            console.log(data)
            if (data.type === 'voltage_logic') {
                document.getElementById('voltage_logic').innerText = data.value;
            } else if (data.type === 'voltage_powersupply') {
                document.getElementById('voltage_powersupply').innerText = data.value;
            } else if (data.type === 'phase_current') {
                document.getElementById('phase_current').innerText = data.value;
            } else if (data.type === 'actualvelocity') {
                document.getElementById('actualvelocity').innerText = data.value;
            } else {
                console.log('Received:', data);  // Log other messages
            }
        };

     

        websocket.onopen = function(e) {
            console.log('WebSocket connected');
        };

        websocket.onclose = function(e) {
            console.log('WebSocket disconnected');
        };

        websocket.onerror = function(e) {
            console.error('WebSocket error:', e);
        };

        function sendCommand(command) {
            websocket.send(JSON.stringify({ 'type': 'command', 'command': command }));
        }

       

        function setCurrent() {
            const current = document.getElementById('current').value;
            websocket.send(JSON.stringify({ 'type': 'set_current', 'current': current }));
        }

      
        document.getElementById("power_on").addEventListener("click", function() {
            console.log("power on")
            sendCommand('velocity_mode');
            setVelocity(); // Call setVelocity to send the actual velocity
           });
        document.getElementById('power_off').addEventListener("click", function() {
            console.log("power off")
            sendCommand('x');
            
            
           });
        document.getElementById("quick").addEventListener("click", function() {
            console.log("quick start")
            sendCommand('quick_start');
            
            
           });

function setVelocity() {
  let velocity = document.getElementById('velocity').value;
  if ((typeof(velocity)!="undefined")) {
    websocket.send(JSON.stringify({ 'type': 'set_velocity', 'velocity': velocity }));
    console.log("ist durch")
  } else {
    window.alert("invalid value")
  }
  
}