import React, { useEffect, useState } from 'react';
import useWebSocket, { ReadyState } from "react-use-websocket";

const SensorPanel = ({ currentUserID, currentSession, isLogging }) => {
    // Sensor data states
    const [sensorData, setSensorData] = useState({
        acc_x: 0,
        acc_y: 0,
        acc_z: 0,
        pitch: 0,
        roll: 0,
        gewicht_N: 0,
        touch_status: 0,
        griffhoehe: 0,
        sensor_id: 'sensor_1'
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

    // Auto-start sensor logging when motor session is active
    useEffect(() => {
        if (currentSession !== "-" && isLogging && !sensorLogging && sensorConnectionStatus === "Connected") {
            startSensorLogging();
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

    const switchSensor = () => {
        const newSensorId = sensorData.sensor_id === 'sensor_1' ? 'sensor_2' : 'sensor_1';
        sendSensorMessage(JSON.stringify({
            type: 'switch_sensor',
            sensor_id: newSensorId
        }));
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
                <div className="sensor-controls">
                    <button 
                        className="sensor-switch-btn"
                        onClick={switchSensor}
                        disabled={sensorConnectionStatus !== "Connected"}
                    >
                        {sensorData.sensor_id}
                    </button>
                </div>
            </div>
            
            <div className="sensor-metrics">
                {/* Accelerometer Data */}
                <div className="sensor-group">
                    <div className="sensor-group-title">Accelerometer (m/s²)</div>
                    <div className="sensor-values">
                        <div className="sensor-metric">
                            <span className="sensor-label">X:</span>
                            <span className="sensor-value">{sensorData.acc_x?.toFixed(2) || "—"}</span>
                        </div>
                        <div className="sensor-metric">
                            <span className="sensor-label">Y:</span>
                            <span className="sensor-value">{sensorData.acc_y?.toFixed(2) || "—"}</span>
                        </div>
                        <div className="sensor-metric">
                            <span className="sensor-label">Z:</span>
                            <span className="sensor-value">{sensorData.acc_z?.toFixed(2) || "—"}</span>
                        </div>
                    </div>
                </div>

                {/* Orientation Data */}
                <div className="sensor-group">
                    <div className="sensor-group-title">Orientation (°)</div>
                    <div className="sensor-values">
                        <div className="sensor-metric">
                            <span className="sensor-label">Pitch:</span>
                            <span className="sensor-value">{sensorData.pitch?.toFixed(1) || "—"}</span>
                        </div>
                        <div className="sensor-metric">
                            <span className="sensor-label">Roll:</span>
                            <span className="sensor-value">{sensorData.roll?.toFixed(1) || "—"}</span>
                        </div>
                    </div>
                </div>

                {/* Force & Touch Data */}
                <div className="sensor-group">
                    <div className="sensor-group-title">Force & Touch</div>
                    <div className="sensor-values">
                        <div className="sensor-metric">
                            <span className="sensor-label">Force:</span>
                            <span className="sensor-value">{sensorData.gewicht_N?.toFixed(1) || "—"} N</span>
                        </div>
                        <div className="sensor-metric">
                            <span className="sensor-label">Height:</span>
                            <span className="sensor-value">{sensorData.griffhoehe?.toFixed(1) || "—"} cm</span>
                        </div>
                        <div className="sensor-metric">
                            <span className="sensor-label">Touch:</span>
                            <span className="sensor-value">{sensorData.touch_status || "—"}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SensorPanel;