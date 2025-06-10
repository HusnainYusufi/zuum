"""
Database Service Module
Handles all database operations for the Voice Freight Broker application
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from loguru import logger
from db_models import Stop, CheckIn, Journey, get_db


class DBService:
    """Database service for handling all database operations"""
    
    @staticmethod
    def get_all_stops() -> List[Dict]:
        """
        Get all stops with basic information
        
        Returns:
            List of dictionaries containing basic stop information
        """
        db = next(get_db())
        try:
            stops = db.query(Stop).all()
            
            return [
                {
                    "id": stop.id,
                    "name": stop.name,
                    "location": stop.location,
                    "eta": stop.eta,
                    "is_delayed": stop.is_delayed,
                    "is_origin": stop.is_origin,
                    "is_destination": stop.is_destination
                }
                for stop in stops
            ]
        except Exception as e:
            logger.error(f"Error fetching stops: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_all_stops_with_details() -> List[Dict]:
        """
        Get all stops with detailed information including cross streets,
        highways, delay reasons, and location details
        
        Returns:
            List of dictionaries containing detailed stop information
        """
        db = next(get_db())
        try:
            stops = db.query(Stop).all()
            
            return [
                {
                    "id": stop.id,
                    "name": stop.name,
                    "location": stop.location,
                    "eta": stop.eta,
                    "cross_street": stop.cross_street,
                    "nearest_highway": stop.nearest_highway,
                    "is_delayed": stop.is_delayed,
                    "delay_reason": stop.delay_reason,
                    "expected_location": stop.expected_location,
                    "reported_location": stop.reported_location,
                    "is_origin": stop.is_origin,
                    "is_destination": stop.is_destination
                }
                for stop in stops
            ]
        except Exception as e:
            logger.error(f"Error fetching stops with details: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_stop_by_id(stop_id: int) -> Optional[Dict]:
        """
        Get a specific stop by ID
        
        Args:
            stop_id: The ID of the stop to retrieve
            
        Returns:
            Dictionary containing stop information or None if not found
        """
        db = next(get_db())
        try:
            stop = db.query(Stop).filter(Stop.id == stop_id).first()
            
            if not stop:
                return None
                
            return {
                "id": stop.id,
                "name": stop.name,
                "location": stop.location,
                "eta": stop.eta,
                "cross_street": stop.cross_street,
                "nearest_highway": stop.nearest_highway,
                "is_delayed": stop.is_delayed,
                "delay_reason": stop.delay_reason,
                "expected_location": stop.expected_location,
                "reported_location": stop.reported_location,
                "is_origin": stop.is_origin,
                "is_destination": stop.is_destination
            }
        except Exception as e:
            logger.error(f"Error fetching stop {stop_id}: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_journey_stops(journey_id: int = 1) -> List[Dict]:
        """
        Get all stops for a specific journey
        
        Args:
            journey_id: The ID of the journey (default: 1)
            
        Returns:
            List of dictionaries containing stop information for the journey
        """
        db = next(get_db())
        try:
            journey = db.query(Journey).filter(Journey.id == journey_id).first()
            
            if not journey:
                logger.warning(f"Journey {journey_id} not found")
                return []
            
            stop_ids = journey.stop_ids
            stops = db.query(Stop).filter(Stop.id.in_(stop_ids)).all()
            
            # Sort stops according to their order in the journey
            stop_dict = {stop.id: stop for stop in stops}
            ordered_stops = [stop_dict[stop_id] for stop_id in stop_ids if stop_id in stop_dict]
            
            return [
                {
                    "id": stop.id,
                    "name": stop.name,
                    "location": stop.location,
                    "eta": stop.eta,
                    "is_delayed": stop.is_delayed,
                    "is_origin": stop.is_origin,
                    "is_destination": stop.is_destination,
                    "order": idx
                }
                for idx, stop in enumerate(ordered_stops)
            ]
        except Exception as e:
            logger.error(f"Error fetching journey stops: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_delayed_stops() -> List[Dict]:
        """
        Get all stops that are currently delayed
        
        Returns:
            List of dictionaries containing delayed stop information
        """
        db = next(get_db())
        try:
            delayed_stops = db.query(Stop).filter(Stop.is_delayed == True).all()
            
            return [
                {
                    "id": stop.id,
                    "name": stop.name,
                    "location": stop.location,
                    "eta": stop.eta,
                    "delay_reason": stop.delay_reason,
                    "expected_location": stop.expected_location,
                    "reported_location": stop.reported_location
                }
                for stop in delayed_stops
            ]
        except Exception as e:
            logger.error(f"Error fetching delayed stops: {str(e)}")
            raise
        finally:
            db.close()


# Create singleton instance for easy import
db_service = DBService()

# Export the functions for backward compatibility
get_all_stops = db_service.get_all_stops
get_all_stops_with_details = db_service.get_all_stops_with_details 