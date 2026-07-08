from app import db
from datetime import datetime
from decimal import Decimal

class JournalEntry(db.Model):
    """Journal Entry model"""
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, nullable=False, index=True)
    entry_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    debit = db.Column(db.Numeric(15, 2), default=0.00)
    credit = db.Column(db.Numeric(15, 2), default=0.00)
    reference = db.Column(db.String(100))  # Invoice number, check number, etc.
    status = db.Column(db.String(20), default='posted')  # posted, draft, reversed
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<JournalEntry {self.entry_number}>'
    
    def get_debit(self):
        """Get debit amount"""
        return float(self.debit)
    
    def get_credit(self):
        """Get credit amount"""
        return float(self.credit)
