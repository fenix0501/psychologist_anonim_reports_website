from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import secrets

Base = declarative_base()

class Ticket(Base):
    __tablename__ = 'tickets'
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    category = Column(String(50))
    priority = Column(String(20), default='medium')
    status = Column(String(20), default='new')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tokens = relationship("Token", back_populates="ticket")
    messages = relationship("Message", back_populates="ticket")
    tags = relationship("Tag", back_populates="ticket")


class Token(Base):
    __tablename__ = 'tokens'
    
    id = Column(Integer, primary_key=True, index=True)
    token_value = Column(String(32), unique=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_access = Column(DateTime)
    
    ticket = relationship("Ticket", back_populates="tokens")
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(24)[:32]


class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    role = Column(String(20), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    ticket = relationship("Ticket", back_populates="messages")


class Tag(Base):
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    tag_name = Column(String(50), nullable=False)
    probability = Column(Float)
    
    ticket = relationship("Ticket", back_populates="tags")


class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    performed_by = Column(String(100))
    performed_at = Column(DateTime, default=datetime.utcnow)
    target_entity = Column(String(50))
    target_id = Column(Integer)


class UserAdmin(Base):
    __tablename__ = 'users_admin'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    role = Column(String(20), default='psychologist')
    permissions = Column(String(200))
    password_hash = Column(String(255))
    sso_identifier = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
