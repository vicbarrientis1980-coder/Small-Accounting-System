from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from models.journal_entry import JournalEntry
from models.account import Account
from models.ledger import Ledger
from datetime import datetime
from decimal import Decimal

transactions_bp = Blueprint('transactions', __name__, url_prefix='/api/transactions')

def generate_entry_number():
    """Generate unique entry number"""
    last_entry = JournalEntry.query.order_by(JournalEntry.id.desc()).first()
    if last_entry:
        entry_num = int(last_entry.entry_number.split('-')[1]) + 1
    else:
        entry_num = 1
    return f"JE-{entry_num:06d}"

@transactions_bp.route('/', methods=['POST'])
@login_required
def create_journal_entry():
    """Create a new journal entry"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['entry_date', 'description', 'account_id', 'debit', 'credit']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate that at least debit or credit is provided
        debit = Decimal(str(data['debit']))
        credit = Decimal(str(data['credit']))
        
        if debit == 0 and credit == 0:
            return jsonify({'error': 'Either debit or credit must be greater than 0'}), 400
        
        # Check if account exists
        account = Account.query.get_or_404(data['account_id'])
        
        # Create journal entry
        entry = JournalEntry(
            entry_number=generate_entry_number(),
            entry_date=datetime.strptime(data['entry_date'], '%Y-%m-%d').date(),
            description=data['description'],
            account_id=data['account_id'],
            debit=debit,
            credit=credit,
            reference=data.get('reference'),
            created_by=current_user.id
        )
        
        db.session.add(entry)
        db.session.flush()
        
        # Update account balance
        if debit > 0:
            account.balance += debit
        if credit > 0:
            account.balance -= credit
        
        # Create ledger entry
        ledger_entry = Ledger(
            account_id=data['account_id'],
            journal_entry_id=entry.id,
            entry_date=entry.entry_date,
            description=data['description'],
            debit=debit,
            credit=credit,
            running_balance=account.balance,
            reference=data.get('reference')
        )
        
        db.session.add(ledger_entry)
        db.session.commit()
        
        return jsonify({
            'message': 'Journal entry created successfully',
            'entry_id': entry.id,
            'entry_number': entry.entry_number,
            'account_id': account.id,
            'account_name': account.account_name
        }), 201
    
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/', methods=['GET'])
@login_required
def get_journal_entries():
    """Get all journal entries"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        account_id = request.args.get('account_id', type=int)
        status = request.args.get('status')
        
        query = JournalEntry.query
        
        if account_id:
            query = query.filter_by(account_id=account_id)
        if status:
            query = query.filter_by(status=status)
        
        paginated = query.order_by(JournalEntry.entry_date.desc()).paginate(page=page, per_page=per_page)
        
        entries_data = [{
            'id': entry.id,
            'entry_number': entry.entry_number,
            'entry_date': entry.entry_date.isoformat(),
            'description': entry.description,
            'account_id': entry.account_id,
            'debit': float(entry.debit),
            'credit': float(entry.credit),
            'reference': entry.reference,
            'status': entry.status
        } for entry in paginated.items]
        
        return jsonify({
            'entries': entries_data,
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/<int:entry_id>', methods=['GET'])
@login_required
def get_journal_entry(entry_id):
    """Get specific journal entry"""
    try:
        entry = JournalEntry.query.get_or_404(entry_id)
        
        return jsonify({
            'id': entry.id,
            'entry_number': entry.entry_number,
            'entry_date': entry.entry_date.isoformat(),
            'description': entry.description,
            'account_id': entry.account_id,
            'account_name': entry.account.account_name,
            'debit': float(entry.debit),
            'credit': float(entry.credit),
            'reference': entry.reference,
            'status': entry.status,
            'created_at': entry.created_at.isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@transactions_bp.route('/<int:entry_id>', methods=['PUT'])
@login_required
def update_journal_entry(entry_id):
    """Update journal entry (only if not posted)"""
    try:
        entry = JournalEntry.query.get_or_404(entry_id)
        data = request.get_json()
        
        if entry.status == 'posted':
            return jsonify({'error': 'Cannot modify posted entries'}), 403
        
        # Update allowed fields for draft entries
        if 'description' in data:
            entry.description = data['description']
        if 'reference' in data:
            entry.reference = data['reference']
        
        entry.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Journal entry updated successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
