# app/services/maps_service.py
import googlemaps
from typing import List, Dict, Optional
import os

class GoogleMapsService:
    def __init__(self):
        self.gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))
    
    async def find_nearby_mechanics(self, location: Dict, service_type: str = "car_repair", radius_miles: int = 25) -> List[Dict]:
        """Find nearby mechanics using Google Places API"""
        
        # Convert miles to meters
        radius_meters = radius_miles * 1609.34
        
        # Search for auto repair shops
        places_result = self.gmaps.places_nearby(
            location=(location['latitude'], location['longitude']),
            radius=radius_meters,
            type='car_repair',
            keyword=f'auto repair {service_type}'
        )
        
        mechanics = []
        for place in places_result.get('results', []):
            # Get additional details
            place_details = self.gmaps.place(
                place_id=place['place_id'],
                fields=['name', 'rating', 'formatted_phone_number', 'website', 'opening_hours', 'reviews']
            )
            
            detail = place_details.get('result', {})
            
            mechanic = {
                'place_id': place['place_id'],
                'name': place.get('name'),
                'rating': place.get('rating'),
                'price_level': place.get('price_level'),
                'address': place.get('vicinity'),
                'phone': detail.get('formatted_phone_number'),
                'website': detail.get('website'),
                'is_open': self._is_currently_open(detail.get('opening_hours')),
                'distance': self._calculate_distance(location, place['geometry']['location']),
                'reviews_summary': self._summarize_reviews(detail.get('reviews', []))
            }
            
            mechanics.append(mechanic)
        
        return mechanics
    
    def _is_currently_open(self, opening_hours: Optional[Dict]) -> bool:
        """Check if the business is currently open"""
        if not opening_hours:
            return False
        return opening_hours.get('open_now', False)
    
    def _calculate_distance(self, location1: Dict, location2: Dict) -> float:
        """Calculate distance between two points in miles"""
        import math
        
        lat1, lon1 = location1['latitude'], location1['longitude']
        lat2, lon2 = location2['lat'], location2['lng']
        
        # Haversine formula
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return round(distance, 1)
    
    def _summarize_reviews(self, reviews: List[Dict]) -> Dict:
        """Summarize recent reviews"""
        if not reviews:
            return {"summary": "No reviews available", "recent_rating": None}
        
        recent_reviews = reviews[:3]  # Get 3 most recent
        avg_rating = sum(r.get('rating', 0) for r in recent_reviews) / len(recent_reviews)
        
        return {
            "recent_rating": round(avg_rating, 1),
            "recent_count": len(recent_reviews),
            "summary": f"Recent average: {avg_rating:.1f}/5 from {len(recent_reviews)} reviews"
        }

