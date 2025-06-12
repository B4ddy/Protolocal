# File: sensor_control/consumer.py
# Main WebSocket consumer for sensor data coordination
import asyncio
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from .sensorcontrol.sensorMonitor import SensorMonitor

logger = logging.getLogger(__name__)

class SensorConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_group_name = 'sensor_control'
        self.stop_event = asyncio.Event()
        
        # Initialize sensor monitor
        self.monitor = None
        self.current_sensor_values = {}
        self.sensor_task = None

    async def connect(self):
        # Add channel to group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name 
        )

        # Initialize sensor monitor
        self.monitor = SensorMonitor(
            self.send_sensor_value, 
            self.send_response,
            self.stop_event
        )
        
        # Start background sensor monitoring task
        self.sensor_task = asyncio.create_task(self.monitor.listen_for_sensor_data())
        
        # Store current sensor values reference
        self.current_sensor_values = self.monitor.sensor_data

        # Accept the websocket connection
        await self.accept()
        
        # Send initial connection confirmation
        await self.send_response({
            "type": "sensor_connection", 
            "status": "connected",
            "message": "Sensor monitoring started"
        })

    async def disconnect(self, close_code):
        logger.info(f"Sensor consumer disconnecting with code: {close_code}")
        
        # Set stop event to halt sensor monitoring
        self.stop_event.set()

        # Properly shutdown sensor monitoring
        if self.sensor_task and not self.sensor_task.done():
            try:
                # Wait for the sensor task to complete gracefully
                await asyncio.wait_for(self.sensor_task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Sensor task didn't complete within timeout, cancelling")
                self.sensor_task.cancel()
                try:
                    await self.sensor_task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logger.error(f"Error during sensor task shutdown: {e}")

        # Final cleanup for monitor
        if self.monitor:
            try:
                # Turn off logging and flush any remaining data
                if self.monitor.logging_bool:
                    await self.monitor.logging_bool_off()
            except Exception as e:
                logger.error(f"Error during monitor cleanup: {e}")
                
        # Remove from channel group
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except Exception as e:
            logger.error(f"Error removing from channel group: {e}")
        
        logger.info(f"Sensor consumer disconnected with code: {close_code}")

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'start_sensor_logging':
                success = await self.monitor.logging_bool_on(text_data_json)
                if success:
                    await self.send_response({
                        "type": "sensor_logging_status", 
                        "status": "started",
                        "sensor_id": self.monitor.current_sensor_id
                    })
                else:
                    await self.send_response({
                        "type": "sensor_logging_status", 
                        "status": "failed", 
                        "reason": "No active sensor session"
                    })
                    
            elif message_type == 'stop_sensor_logging':
                await self.monitor.logging_bool_off()
                await self.send_response({
                    "type": "sensor_logging_status", 
                    "status": "stopped"
                })
                
            elif message_type == 'switch_sensor':
                sensor_id = text_data_json.get('sensor_id', 'sensor_1')
                self.monitor.set_sensor_id(sensor_id)
                await self.send_response({
                    "type": "sensor_switch", 
                    "status": "switched",
                    "current_sensor_id": self.monitor.current_sensor_id
                })
                
            elif message_type == 'get_sensor_status':
                await self.send_response({
                    "type": "sensor_status",
                    "logging_active": self.monitor.logging_bool,
                    "current_sensor_id": self.monitor.current_sensor_id,
                    "available_sensors": self.monitor.sensor_ids,
                    "last_data": self.monitor.get_current_sensor_data()
                })
                
            elif message_type == 'calibrate_sensors':
                # Placeholder for sensor calibration functionality
                await self.send_response({
                    "type": "sensor_calibration", 
                    "status": "calibration_started",
                    "message": "Sensor calibration initiated"
                })
                
            else:
                await self.send_response({
                    "type": "error", 
                    "message": f"Unknown message type: {message_type}"
                })
                
        except json.JSONDecodeError:
            await self.send_response({
                "type": "error", 
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(f"Error processing sensor message: {e}")
            await self.send_response({
                "type": "error", 
                "message": f"Processing error: {str(e)}"
            })

    async def send_sensor_value(self, key, value):
        """Send sensor value to the group"""
        await self.channel_layer.group_send(
            self.room_group_name, 
            {'type': 'sensor_value', 'key': key, 'value': value}
        )

    async def send_response(self, message):
        """Send response directly to this consumer"""
        await self.send(text_data=json.dumps(message))

    async def sensor_value(self, event):
        """Handle sensor value events from the group"""
        key = event['key']
        value = event['value']
        await self.send(text_data=json.dumps({
            'type': key,
            'value': value,
        }))