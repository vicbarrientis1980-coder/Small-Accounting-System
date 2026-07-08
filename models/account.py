from app import db
from datetime import datetime
from decimal import Decimal

class Account(db.Model):
    """Account model - Chart of Accounts"""
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    account_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    account_name = db.Column(db.String(120), nullable=False, index=True)
    account_type = db.Column(db.String(50), nullable=False)  # Asset, Liability, Equity, Revenue, Expense
    account_category = db.Column(db.String(50))  # Current Asset, Fixed Asset, etc.
    description = db.Column(db.Text)
    balance = db.Column(db.Numeric(15, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    journal_entries = db.relationship('JournalEntry', backref='account', lazy=True)
    ledger_entries = db.relationship('Ledger', backref='account', lazy=True)
    
    def __repr__(self):
        return f'<Account {self.account_code} - {self.account_name}>'
    
    def get_balance(self):
        """Get current account balance"""
        return float(self.balance)
