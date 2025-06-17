import React, { useEffect, useState } from 'react';
import useWebSocket, { ReadyState } from "react-use-websocket";

const SensorPanel = ({ currentUserID, currentSession, isLogging }) => {
    // Sensor data states
    const [sensorData, setSensorData] = useState({
        // Arduino A2 sensor data
        gewicht_A2: 0,
        touchstatus_A2: 0,
        griffhoehe_A2: 0,
        // Arduino A3 sensor data
        gewicht_A3: 0,
        touchstatus_A3: 0,
        griffhoehe_A3: 0
    });
    
    const [sensorConnectionStatus, setSensorConnectionStatus] = useState("Disconnected");
    const [sensorLogging, setSensorLogging] = useState(false);

    // Sensor WebSocket connection
    const sensorSocketUrl = 'ws://' + window.location.hostname + ':8000/ws/sensor_control/';
    const { sendMessage: sendSensorMessage, readyState: sensorReadyState } = useWebSocket(sensorSocketUrl, {
        onOpen: () => {
            console.log('Sensor WebSocket opened');
            setSensorConnectionStatus("Connected");
        },
        shouldReconnect: (closeEvent) => true,
        share: true,
        onMessage: (event) => {
            const data = JSON.parse(event.data);
            if (!data) return;
            
            // Update sensor data
            setSensorData(prevData => ({
                ...prevData,
                ...data
            }));
            
            // Handle sensor logging status
            if (data.type === "sensor_logging_status") {
                setSensorLogging(data.status === "started");
            }
        },
        onClose: () => {
            console.log('Sensor WebSocket closed');
            setSensorConnectionStatus("Disconnected");
        },
        onError: (error) => {
            console.error('Sensor WebSocket error:', error);
            setSensorConnectionStatus("Error");
        }
    });

    const sensorConnectionStatusText = {
        [ReadyState.CONNECTING]: 'Connecting',
        [ReadyState.OPEN]: 'Connected',
        [ReadyState.CLOSING]: 'Closing',
        [ReadyState.CLOSED]: 'Disconnected',
        [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
    }[sensorReadyState];

    useEffect(() => {
        setSensorConnectionStatus(sensorConnectionStatusText);
    }, [sensorReadyState]);

    // Auto-start sensor logging only when motor session is active (for database tracking)
    useEffect(() => {
        if (currentSession !== "-" && isLogging && !sensorLogging && sensorConnectionStatus === "Connected") {
            startSensorLogging();
        } else if (currentSession === "-" && sensorLogging) {
            // Stop database logging when session ends, but keep displaying sensor data
            stopSensorLogging();
        }
    }, [currentSession, isLogging, sensorConnectionStatus]);

    const startSensorLogging = () => {
        sendSensorMessage(JSON.stringify({
            type: 'start_sensor_logging',
            message: currentUserID
        }));
        setSensorLogging(true);
    };

    const stopSensorLogging = () => {
        sendSensorMessage(JSON.stringify({
            type: 'stop_sensor_logging'
        }));
        setSensorLogging(false);
    };


    return (
        <div className="sensor-panel">
            <div className="sensor-header">
                <div className="sensor-title">
                    <span>Sensors</span>
                    <div className={`sensor-connection-indicator ${sensorConnectionStatus.toLowerCase()}`}>
                        <span className="sensor-status-dot"></span>
                        <span className="sensor-status-text">{sensorConnectionStatus}</span>
                    </div>
                </div>
            </div>
            
            <div className="sensor-metrics">
                {/* Arduino A2 Sensor Data */}
                <div className="sensor-group">
                    <div className="sensor-group-title">Arduino A2 (0x08)</div>
                    <div className="sensor-values">
                        <div className="sensor-metric">
                            <span className="sensor-label">Weight:</span>
                            <span className="sensor-value">{sensorData.gewicht_A2?.toFixed(2) || "—"} N</span>
                        </div>
                        <div className="sensor-metric">
                            <span className="sensor-label">Touch:</span>
                            <span className="sensor-value">
                                {sensorData.touchstatus_A2 !== undefined ?
                                    `${sensorData.touchstatus_A2} (${sensorData.touchstatus_A2.toString(2).padStart(12, '0')})` :
                                    "—"
                                }
                            </span>
                        </div>
                        <div className="sensor-metric">
                            <span className="sensor-label">Grip Height:</span>
                            <span className="sensor-value">{sensorData.griffhoehe_A2?.toFixed(1) || "—"} cm</span>
                        </div>
                    </div>
                </div>

                {/* Arduino A3 Sensor Data */}
                <div className="sensor-group">
                    <div className="sensor-group-title">Arduino A3 (0x10)</div>
                    <div className="sensor-values">
                        <div className="sensor-metric">
                            <span className="sensor-label">Weight:</span>
                            <span className="sensor-value">{sensorData.gewicht_A3?.toFixed(2) || "—"} N</span>
                        </div>
                        <div className="sensor-metric">
                            <span className="sensor-label">Touch:</span>
                            <span className="sensor-value">
                                {sensorData.touchstatus_A3 !== undefined ?
                                    `${sensorData.touchstatus_A3} (${sensorData.touchstatus_A3.toString(2).padStart(12, '0')})` :
                                    "—"
                                }
                            </span>
                        </div>
                        <div className="sensor-metric">
                            <span className="sensor-label">Grip Height:</span>
                            <span className="sensor-value">{sensorData.griffhoehe_A3?.toFixed(1) || "—"} cm</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SensorPanel;