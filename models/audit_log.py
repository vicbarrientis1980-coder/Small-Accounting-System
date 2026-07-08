from app import db
from datetime import datetime
import json

class AuditLog(db.Model):
    """Audit Log model for tracking all user actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Action Information
    action_type = db.Column(db.String(50), nullable=False, index=True)  # CREATE, READ, UPDATE, DELETE, VIEW, etc.
    resource_type = db.Column(db.String(50), nullable=False, index=True)  # Account, Transaction, User, etc.
    resource_id = db.Column(db.Integer, index=True)  # ID of the affected resource
    
    # User Information
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.String(255))  # Browser/client information
    
    # Details
    details = db.Column(db.Text)  # Additional details in JSON format
    old_values = db.Column(db.Text)  # Previous values before update
    new_values = db.Column(db.Text)  # New values after update
    
    # Status
    status = db.Column(db.String(20), default='SUCCESS')  # SUCCESS, FAILED, PENDING
    error_message = db.Column(db.Text)  # Error details if action failed
    
    # Timestamp
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action_type} on {self.resource_type} at {self.timestamp}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'action_type': self.action_type,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
            'details': json.loads(self.details) if self.details else None
        }
