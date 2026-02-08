from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import secrets

Base = declarative_base()

class Ticket(Base):
    __tablename__ = 'tickets'
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)  # Original text of the report
    category = Column(String(50))  # Category assigned by ML or admin
    priority = Column(String(20), default='medium')  # low, medium, high
    status = Column(String(20), default='new')  # new, in_progress, resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tokens = relationship("Token", back_populates="ticket")
    messages = relationship("Message", back_populates="ticket")
    tags = relationship("Tag", back_populates="ticket")


class Token(Base):
    __tablename__ = 'tokens'
    
    id = Column(Integer, primary_key=True, index=True)
    token_value = Column(String(32), unique=True, index=True)  # Generated token
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_access = Column(DateTime)
    
    # Relationship
    ticket = relationship("Ticket", back_populates="tokens")
    
    @staticmethod
    def generate_token():
        """Generate a random token"""
        return secrets.token_urlsafe(24)[:32]  # Generate a 32-character token


class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    role = Column(String(20), nullable=False)  # 'student' or 'psychologist'
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    ticket = relationship("Ticket", back_populates="messages")


class Tag(Base):
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    tag_name = Column(String(50), nullable=False)  # Name of the tag
    probability = Column(Float)  # Probability score from ML model
    
    # Relationship
    ticket = relationship("Ticket", back_populates="tags")


class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)  # Action performed
    performed_by = Column(String(100))  # Who performed the action
    performed_at = Column(DateTime, default=datetime.utcnow)  # When
    target_entity = Column(String(50))  # What entity was affected (ticket, message, etc.)
    target_id = Column(Integer)  # ID of the affected entity


class UserAdmin(Base):
    __tablename__ = 'users_admin'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    role = Column(String(20), default='psychologist')  # psychologist, admin, supervisor
    permissions = Column(String(200))  # Comma-separated list of permissions
    password_hash = Column(String(255))  # Hashed password
    sso_identifier = Column(String(100), nullable=True)  # For SSO if applied
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)