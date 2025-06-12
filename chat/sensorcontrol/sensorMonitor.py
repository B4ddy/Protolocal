import asyncio
import logging
import time
import struct
import random
from collections import deque
from django.utils import timezone
from django.db import transaction

from ..models import sensordata, baseuser, protosession
from asgiref.sync import sync_to_async

# Try to import smbus2, fall back to simulation if not available
try:
    import smbus2
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    logging.warning("smbus2 not available, using simulated sensor data")

logger = logging.getLogger(__name__)

class SensorMonitor:
    def __init__(self, send_sensor_value_callback, send_response_callback, stop_event):
        self.send_sensor_value = send_sensor_value_callback
        self.send_response = send_response_callback
        self.stop_event = stop_event
        self.logging_bool = False
        self.user_id = 0
        self.previous_sensor_data = {}
        
        # I2C configuration
        if HARDWARE_AVAILABLE:
            try:
                self.bus = smbus2.SMBus(2)  # I2C-Bus 2 for Orange Pi 5 Plus
                self.hardware_mode = True
            except Exception as e:
                logger.warning(f"Failed to initialize I2C bus: {e}. Using simulation mode.")
                self.hardware_mode = False
        else:
            self.hardware_mode = False
            
        self.MPU_ADDR = 0x09
        self.HX711_ADDR = 0x08
        
        # Current sensor data storage
        self.sensor_data = {}
        
        # Sensor identifiers for dual sensor support
        self.sensor_ids = ['sensor_1', 'sensor_2']
        self.current_sensor_id = 'sensor_1'
        
        # Database write configuration
        self.db_write_interval = 20 
        self.data_buffer = deque(maxlen=500) 
        
        # Cache for user and session objects
        self.user_cache = None
        self.session_cache = None
        self.last_cache_update = 0
        self.cache_ttl = 60  # Cache TTL in seconds
        
        # Websocket send configuration
        self.last_websocket_send_time = time.time()
        self.websocket_send_interval = 0.1  # Send every 100ms (sensors are slower than motor)
        
        # Database write frequency control
        self.db_write_frequency = 5  # Write every 5th websocket send
        self.websocket_send_counter = 0 
        self.db_write_flag = False 

    def read_floats(self, addr, length):
        """Read float data from I2C sensor or simulate data"""
        if self.hardware_mode:
            try:
                data = self.bus.read_i2c_block_data(addr, 0, length)
                return bytes(data)
            except Exception as e:
                logger.error(f"I2C read error at address {hex(addr)}: {e}")
                return None
        else:
            # Simulate sensor data for testing
            return self.simulate_sensor_data(addr, length)
    
    def simulate_sensor_data(self, addr, length):
        """Simulate sensor data for testing purposes"""
        if addr == self.MPU_ADDR and length == 20:
            # Simulate MPU6050 data (5 floats)
            acc_x = random.uniform(-2.0, 2.0)
            acc_y = random.uniform(-2.0, 2.0)
            acc_z = random.uniform(8.0, 12.0)  # Gravity component
            pitch = random.uniform(-45.0, 45.0)
            roll = random.uniform(-45.0, 45.0)
            return struct.pack('<fffff', acc_x, acc_y, acc_z, pitch, roll)
        elif addr == self.HX711_ADDR and length == 10:
            # Simulate HX711 + MPR121 data
            gewicht_N = random.uniform(0.0, 100.0)
            touchStatus = random.randint(0, 255)
            griffhoehe = random.uniform(10.0, 50.0)
            return struct.pack('<fHf', gewicht_N, touchStatus, griffhoehe)
        else:
            # Return zeros for unknown addresses
            return bytes(length)

    async def listen_for_sensor_data(self):
        """Main sensor data reading loop"""
        try:
            loop = asyncio.get_event_loop()
            
            while not self.stop_event.is_set():
                try:
                    # Check if loop is still running before scheduling executor tasks
                    if loop.is_closed():
                        logger.info("Event loop is closed, stopping sensor monitoring")
                        break
                        
                    # Read sensor data in executor to avoid blocking
                    sensor_data = await loop.run_in_executor(None, self.read_all_sensors)
                    
                    if sensor_data and not self.stop_event.is_set():
                        # Update internal sensor data storage
                        self.sensor_data.update(sensor_data)
                        
                        # Check if it's time to send data to websocket
                        current_time = time.time()
                        if current_time - self.last_websocket_send_time >= self.websocket_send_interval:
                            
                            # Create a copy of the sensor data for this websocket send
                            sensor_data_copy = self.sensor_data.copy()
                            
                            # Determine if this message should be tagged for DB writing
                            dbw_flag = False
                            if self.logging_bool and self.websocket_send_counter % self.db_write_frequency == 0:
                                dbw_flag = True
                            
                            # Format data and send (only if not stopping)
                            if not self.stop_event.is_set():
                                formatted_data = self.format_sensor_data_for_websocket(sensor_data_copy, dbw_flag, current_time)
                                await self.send_response(formatted_data)
                            
                            # Increment counter
                            self.websocket_send_counter += 1
                            
                            # Write to DB if needed
                            if self.logging_bool and self.websocket_send_counter % self.db_write_frequency == 0:
                                self.data_buffer.append({'data': sensor_data_copy, 'sensor_id': self.current_sensor_id})
                                self.db_write_flag = True
                            
                            self.last_websocket_send_time = current_time
                    
                    # Write to database if flagged (only if not stopping)
                    if self.db_write_flag and not self.stop_event.is_set():
                        await self.write_buffered_data_to_db()
                        self.db_write_flag = False
                    
                    # Small delay to prevent overwhelming the I2C bus
                    await asyncio.sleep(0.05)  # 50ms delay
                    
                except RuntimeError as e:
                    if "cannot schedule new futures after interpreter shutdown" in str(e):
                        logger.info("Interpreter shutting down, stopping sensor monitoring")
                        break
                    else:
                        logger.error(f"Runtime error in sensor monitoring: {e}")
                        break
                except asyncio.CancelledError:
                    logger.info("Sensor monitoring task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error in sensor monitoring: {e}")
                    # Continue the loop for other exceptions
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            logger.info("Sensor monitoring task cancelled during initialization")
        except Exception as e:
            logger.error(f"Error in listen_for_sensor_data: {e}")
        finally:
            # Final cleanup - write any remaining buffered data
            if self.data_buffer and self.logging_bool:
                try:
                    await self.write_buffered_data_to_db()
                except Exception as e:
                    logger.error(f"Error writing final buffered data: {e}")
            logger.info("Sensor monitoring stopped")

    def read_all_sensors(self):
        """Read data from all sensors"""
        sensor_data = {}
        
        try:
            # Read MPU6050 data (5 floats = 20 bytes)
            raw_mpu = self.read_floats(self.MPU_ADDR, 20)
            if raw_mpu and len(raw_mpu) == 20:
                acc_x, acc_y, acc_z, pitch, roll = struct.unpack('<fffff', raw_mpu)
                sensor_data.update({
                    'acc_x': round(acc_x, 2),
                    'acc_y': round(acc_y, 2),
                    'acc_z': round(acc_z, 2),
                    'pitch': round(pitch, 2),
                    'roll': round(roll, 2)
                })
                logger.debug(f"MPU6050: aX={acc_x:.2f} m/s², aY={acc_y:.2f} m/s², aZ={acc_z:.2f} m/s² | Pitch={pitch:.2f}°, Roll={roll:.2f}°")
            else:
                logger.warning("Failed to read MPU6050 data")
            
            # Read HX711 + MPR121 data (10 bytes)
            raw_hx = self.read_floats(self.HX711_ADDR, 10)
            if raw_hx and len(raw_hx) == 10:
                gewicht_N, touchStatus, griffhoehe = struct.unpack('<fHf', raw_hx)
                sensor_data.update({
                    'gewicht_N': round(gewicht_N, 2),
                    'touch_status': touchStatus,
                    'griffhoehe': round(griffhoehe, 1)
                })
                logger.debug(f"HX711 → Weight: {gewicht_N:.2f} N, MPR121 → Grip height: {griffhoehe:.1f} cm")
            else:
                logger.warning("Failed to read HX711/MPR121 data")
                
        except Exception as e:
            logger.error(f"Error reading sensor data: {e}")
        
        return sensor_data

    def format_sensor_data_for_websocket(self, sensor_data, dbw_flag, timestamp):
        """Format sensor data for websocket transmission"""
        data = {
            'timestamp': timestamp,
            'sensor_id': self.current_sensor_id
        }
        
        if dbw_flag:
            data['dbw'] = True
        
        # Include all sensor data
        data.update(sensor_data)
        
        # Update previous values
        self.previous_sensor_data.update(sensor_data)
        
        return data

    @sync_to_async
    def _get_user_and_session(self):
        """Get and cache user and session objects"""
        # Check if we're in shutdown mode
        if self.stop_event.is_set():
            return None, None
            
        current_time = time.time()
        
        # Check if cache needs refresh
        if (self.user_cache is None or self.session_cache is None or
                current_time - self.last_cache_update > self.cache_ttl):
            try:
                user = baseuser.objects.get(id=self.user_id)
                session = protosession.objects.filter(user=user, is_active=True).first()
                
                if session:
                    self.user_cache = user
                    self.session_cache = session
                    self.last_cache_update = current_time
                    return user, session
                else:
                    logger.error(f"No active sensor session found for user {self.user_id}")
                    return None, None
            except baseuser.DoesNotExist:
                logger.error(f"User with ID {self.user_id} does not exist")
                return None, None
            except Exception as e:
                logger.error(f"Error getting user and session: {e}")
                return None, None
        else:
            # Return cached values
            return self.user_cache, self.session_cache

    @sync_to_async
    def _bulk_create_sensor_data(self, data_points, session):
        """Bulk create sensordata objects"""
        # Check if we're in shutdown mode
        if self.stop_event.is_set():
            return 0
            
        try:
            with transaction.atomic():
                sensor_data_objects = [
                    sensordata(
                        acc_x=data['data'].get('acc_x', 0.0),
                        acc_y=data['data'].get('acc_y', 0.0),
                        acc_z=data['data'].get('acc_z', 0.0),
                        pitch=data['data'].get('pitch', 0.0),
                        roll=data['data'].get('roll', 0.0),
                        gewicht_N=data['data'].get('gewicht_N', 0.0),
                        touch_status=data['data'].get('touch_status', 0),
                        griffhoehe=data['data'].get('griffhoehe', 0.0),
                        sensor_id=data.get('sensor_id', 'sensor_1'),
                        session=session,
                        timestamp=timezone.now()
                    ) for data in data_points
                ]
                
                # Use bulk_create for efficiency
                created = sensordata.objects.bulk_create(sensor_data_objects)
                return len(created)
        except Exception as e:
            logger.error(f"Error bulk creating sensordata: {e}")
            return 0

    async def write_buffered_data_to_db(self):
        """Write buffered sensor data to database in bulk"""
        if not self.data_buffer or not self.logging_bool:
            return  # Nothing to write
        
        try:
            # Check if we're in shutdown mode
            if self.stop_event.is_set():
                logger.info("[SENSOR-DBW] Stop event set, skipping database write")
                return
                
            # Get user and session (using cached values if available)
            _, session = await self._get_user_and_session()
            
            if not session:
                logger.error("Cannot write to database: No active sensor session")
                return
            
            # Extract data points from buffer
            data_points = list(self.data_buffer)
            
            # Bulk create in database
            num_created = await self._bulk_create_sensor_data(data_points, session)
            
            if num_created > 0:
                # Clear buffer after successful write
                self.data_buffer.clear()
                logger.info(f"[SENSOR-DBW] Successfully wrote {num_created} sensor data points to database")
            else:
                logger.warning("[SENSOR-DBW] No sensor data points written to database.")
                
        except RuntimeError as e:
            if "cannot schedule new futures after interpreter shutdown" in str(e):
                logger.info("[SENSOR-DBW] Interpreter shutting down, skipping database write")
            else:
                logger.error(f"[SENSOR-DBW] Runtime error writing to database: {e}")
        except Exception as db_error:
            logger.error(f"[SENSOR-DBW] Error writing sensor data to database: {db_error}")

    async def logging_bool_on(self, textdata):
        """Enable sensor data logging"""
        self.user_id = textdata["message"]
        
        # First check if there's an active session before enabling logging
        user, session = await self._get_user_and_session()
        
        if not session:
            logger.warning(f"Cannot enable sensor logging: No active session for user {self.user_id}")
            return False  # Return False to indicate logging wasn't enabled
        
        self.logging_bool = True
        self.websocket_send_counter = 0
        logger.info(f"Sensor logging enabled for user {self.user_id}")
        return True  # Return True to indicate logging was enabled

    async def logging_bool_off(self):
        """Disable sensor data logging"""
        # Write any remaining data before turning off logging
        if self.data_buffer:
            await self.write_buffered_data_to_db()
        
        self.logging_bool = False
        logger.info("Sensor logging disabled")

    def set_sensor_id(self, sensor_id):
        """Set the current sensor ID for dual sensor support"""
        if sensor_id in self.sensor_ids:
            self.current_sensor_id = sensor_id
            logger.info(f"Switched to sensor ID: {sensor_id}")
        else:
            logger.warning(f"Invalid sensor ID: {sensor_id}. Valid IDs: {self.sensor_ids}")

    def get_current_sensor_data(self):
        """Get a copy of current sensor data"""
        return self.sensor_data.copy()