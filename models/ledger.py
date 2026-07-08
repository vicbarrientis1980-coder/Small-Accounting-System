from app import db
from datetime import datetime
from decimal import Decimal

class Ledger(db.Model):
    """General Ledger model"""
    __tablename__ = 'ledger'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False, index=True)
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    entry_date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text)
    debit = db.Column(db.Numeric(15, 2), default=0.00)
    credit = db.Column(db.Numeric(15, 2), default=0.00)
    running_balance = db.Column(db.Numeric(15, 2), default=0.00)
    reference = db.Column(db.String(100))
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Ledger {self.account_id} - {self.entry_date}>'
    
    def get_debit(self):
        """Get debit amount"""
        return float(self.debit)
    
    def get_credit(self):
        """Get credit amount"""
        return float(self.credit)
    
    def get_balance(self):
        """Get running balance"""
        return float(self.running_balance)
