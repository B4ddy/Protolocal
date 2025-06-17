import asyncio
import logging
import time
import struct
import random
from collections import deque
from django.utils import timezone
from django.db import transaction

from ..models import SensorData, BaseUser, ProtoSession
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
            
        # Sensor addresses from demo script
        self.A2_ADDR = 0x08  # Arduino 2
        self.A3_ADDR = 0x10  # Arduino 3
        
        # Current sensor data storage
        self.sensor_data = {}
        
        # Both sensors are always active
        self.sensor_ids = ['A2', 'A3']
        
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
        if addr == self.A2_ADDR and length == 10:
            # Simulate Arduino A2 sensor data (gewicht, touchstatus, griffhoehe)
            gewicht_A2 = random.uniform(0.0, 150.0)
            touchstatus_A2 = random.randint(0, 4095)  # 12-bit value
            griffhoehe_A2 = random.uniform(5.0, 60.0)
            return struct.pack('<fHf', gewicht_A2, touchstatus_A2, griffhoehe_A2)
        elif addr == self.A3_ADDR and length == 10:
            # Simulate Arduino A3 sensor data (gewicht, touchstatus, griffhoehe)
            gewicht_A3 = random.uniform(0.0, 150.0)
            touchstatus_A3 = random.randint(0, 4095)  # 12-bit value
            griffhoehe_A3 = random.uniform(5.0, 60.0)
            return struct.pack('<fHf', gewicht_A3, touchstatus_A3, griffhoehe_A3)
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
                                self.data_buffer.append({'data': sensor_data_copy})
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
            # Read Arduino A2 sensor data (10 bytes)
            raw_a2 = self.read_floats(self.A2_ADDR, 10)
            if raw_a2 and len(raw_a2) == 10:
                gewicht_A2, touchstatus_A2, griffhoehe_A2 = struct.unpack('<fHf', raw_a2)
                sensor_data.update({
                    'gewicht_A2': round(gewicht_A2, 2),
                    'touchstatus_A2': touchstatus_A2,
                    'griffhoehe_A2': round(griffhoehe_A2, 1)
                })
                logger.debug(f"Arduino A2 → Weight: {gewicht_A2:.2f} N, Touch: {bin(touchstatus_A2)} ({touchstatus_A2}), Grip height: {griffhoehe_A2:.1f} cm")
            else:
                logger.warning("Failed to read Arduino A2 data")
            
            # Read Arduino A3 sensor data (10 bytes)
            raw_a3 = self.read_floats(self.A3_ADDR, 10)
            if raw_a3 and len(raw_a3) == 10:
                gewicht_A3, touchstatus_A3, griffhoehe_A3 = struct.unpack('<fHf', raw_a3)
                sensor_data.update({
                    'gewicht_A3': round(gewicht_A3, 2),
                    'touchstatus_A3': touchstatus_A3,
                    'griffhoehe_A3': round(griffhoehe_A3, 1)
                })
                logger.debug(f"Arduino A3 → Weight: {gewicht_A3:.2f} N, Touch: {bin(touchstatus_A3)} ({touchstatus_A3}), Grip height: {griffhoehe_A3:.1f} cm")
            else:
                logger.warning("Failed to read Arduino A3 data")
                
        except Exception as e:
            logger.error(f"Error reading sensor data: {e}")
        
        return sensor_data

    def format_sensor_data_for_websocket(self, sensor_data, dbw_flag, timestamp):
        """Format sensor data for websocket transmission"""
        data = {
            'timestamp': timestamp
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
                user = BaseUser.objects.get(id=self.user_id)
                session = ProtoSession.objects.filter(user=user, is_active=True).first()
                
                if session:
                    self.user_cache = user
                    self.session_cache = session
                    self.last_cache_update = current_time
                    return user, session
                else:
                    logger.error(f"No active sensor session found for user {self.user_id}")
                    return None, None
            except BaseUser.DoesNotExist:
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
        """Bulk create SensorData objects"""
        # Check if we're in shutdown mode
        if self.stop_event.is_set():
            return 0
            
        try:
            with transaction.atomic():
                sensor_data_objects = [
                    SensorData(
                        # Arduino A2 data
                        gewicht_A2=data['data'].get('gewicht_A2', 0.0),
                        touchstatus_A2=data['data'].get('touchstatus_A2', 0),
                        griffhoehe_A2=data['data'].get('griffhoehe_A2', 0.0),
                        # Arduino A3 data
                        gewicht_A3=data['data'].get('gewicht_A3', 0.0),
                        touchstatus_A3=data['data'].get('touchstatus_A3', 0),
                        griffhoehe_A3=data['data'].get('griffhoehe_A3', 0.0),
                        # Metadata
                        sensor_id='both',  # Both sensors are always recorded
                        session=session,
                        timestamp=timezone.now()
                    ) for data in data_points
                ]
                
                # Use bulk_create for efficiency
                created = SensorData.objects.bulk_create(sensor_data_objects)
                return len(created)
        except Exception as e:
            logger.error(f"Error bulk creating SensorData: {e}")
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


    def get_current_sensor_data(self):
        """Get a copy of current sensor data"""
        return self.sensor_data.copy()