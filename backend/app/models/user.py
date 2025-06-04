from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)  
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    cars = relationship("Car", back_populates="owner")
    notifications = relationship("Notification", back_populates="user")

class Car(Base):
    __tablename__ = "cars"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    make = Column(String)
    model = Column(String)
    year = Column(Integer)
    vin = Column(String, unique=True)
    current_mileage = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="cars")
    maintenance_records = relationship("MaintenanceRecord", back_populates="car")

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"
    
    id = Column(Integer, primary_key=True, index=True)
    car_id = Column(Integer, ForeignKey("cars.id"))
    service_type = Column(String)  # oil_change, brake_service, etc.
    date_performed = Column(DateTime)
    mileage_at_service = Column(Integer)
    cost = Column(Float)
    shop_name = Column(String)
    notes = Column(String)
    
    # Relationships
    car = relationship("Car", back_populates="maintenance_records")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    notification_type = Column(String)  # maintenance_reminder, diagnostic_alert
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="notifications")