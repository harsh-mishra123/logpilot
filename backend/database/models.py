from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, Index
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    team_id = Column(String(36), ForeignKey("teams.id"))
    is_owner = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = relationship("Team", back_populates="members")

class Team(Base):
    __tablename__ = "teams"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    subscription_status = Column(String(50), default="inactive")  # active, trialing, past_due, canceled, inactive
    seats_limit = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("User", back_populates="team")
    api_keys = relationship("APIKey", back_populates="team")
    incidents = relationship("Incident", back_populates="team")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    key = Column(String(255), unique=True, index=True, nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=False)
    name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    
    # Relationships
    team = relationship("Team", back_populates="api_keys")

class LogEntry(Base):
    __tablename__ = "log_entries"
    __table_args__ = (
        Index('idx_log_entries_team_timestamp', 'team_id', 'timestamp'),
        Index('idx_log_entries_severity', 'severity'),
    )
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=False)
    source = Column(String(255))  # e.g., "web-server", "api", "worker"
    timestamp = Column(DateTime, nullable=False)
    severity = Column(String(20))  # INFO, WARNING, ERROR, DEBUG, CRITICAL
    message = Column(Text, nullable=False)
    raw_log = Column(Text)
    parsed_data = Column(JSON)  # Extracted fields like response_time, memory_usage, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    team = relationship("Team")
    anomalies = relationship("Anomaly", back_populates="log_entry")

class Anomaly(Base):
    __tablename__ = "anomalies"
    __table_args__ = (
        Index('idx_anomalies_team_timestamp', 'team_id', 'detected_at'),
    )
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=False)
    log_entry_id = Column(String(36), ForeignKey("log_entries.id"))
    anomaly_type = Column(String(50))  # error_spike, latency_creep, memory_leak, pattern_break
    severity_score = Column(Float)  # 0-100
    description = Column(Text)
    context = Column(JSON)  # Additional data: z_score, trend_slope, etc.
    detected_at = Column(DateTime, default=datetime.utcnow)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    incident_id = Column(String(36), ForeignKey("incidents.id"))
    
    # Relationships
    team = relationship("Team")
    log_entry = relationship("LogEntry", back_populates="anomalies")
    incident = relationship("Incident", back_populates="anomalies")

class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index('idx_incidents_team_timestamp', 'team_id', 'started_at'),
    )
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    severity = Column(String(20))  # critical, high, medium, low
    started_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime)
    status = Column(String(20), default="open")  # open, investigating, resolved, closed
    report = Column(Text)  # Auto-generated incident report
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = relationship("Team", back_populates="incidents")
    anomalies = relationship("Anomaly", back_populates="incident")