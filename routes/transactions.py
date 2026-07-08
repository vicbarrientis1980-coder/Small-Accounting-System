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

class DoubleEntryValidator:
    """Validates double-entry bookkeeping principles"""
    
    @staticmethod
    def validate_entry_lines(entry_lines):
        """
        Validate that all entry lines follow double-entry bookkeeping:
        - Total debits must equal total credits
        - Each line must have either debit OR credit, not both
        - No negative amounts
        
        Args:
            entry_lines: List of dicts with 'account_id', 'debit', 'credit'
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not entry_lines or len(entry_lines) < 2:
            return False, "At least 2 lines are required for a journal entry"
        
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        
        for i, line in enumerate(entry_lines):
            debit = Decimal(str(line.get('debit', 0)))
            credit = Decimal(str(line.get('credit', 0)))
            
            # Validate amounts are non-negative
            if debit < 0:
                return False, f"Line {i+1}: Debit amount cannot be negative"
            if credit < 0:
                return False, f"Line {i+1}: Credit amount cannot be negative"
            
            # Validate that each line has either debit or credit, not both
            if debit > 0 and credit > 0:
                return False, f"Line {i+1}: A line cannot have both debit and credit amounts"
            
            # Validate that each line has at least one amount
            if debit == 0 and credit == 0:
                return False, f"Line {i+1}: Each line must have either a debit or credit amount"
            
            # Validate account exists
            account = Account.query.get(line.get('account_id'))
            if not account:
                return False, f"Line {i+1}: Account ID {line.get('account_id')} does not exist"
            
            if not account.is_active:
                return False, f"Line {i+1}: Account {account.account_code} is not active"
            
            total_debit += debit
            total_credit += credit
        
        # Core rule: Total debits must equal total credits
        if total_debit != total_credit:
            difference = abs(total_debit - total_credit)
            return False, f"Double-entry bookkeeping violation: Total debits ({float(total_debit)}) do not equal total credits ({float(total_credit)}). Difference: {float(difference)}"
        
        return True, None

@transactions_bp.route('/', methods=['POST'])
@login_required
def create_journal_entry():
    """
    Create a new journal entry with multiple lines following double-entry bookkeeping
    
    Request body:
    {
        "entry_date": "2024-01-15",
        "description": "Payment for office supplies",
        "reference": "CHK-001",
        "lines": [
            {"account_id": 1, "debit": 500.00, "credit": 0},
            {"account_id": 2, "debit": 0, "credit": 500.00}
        ]
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['entry_date', 'description', 'lines']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields: entry_date, description, lines'}), 400
        
        # Validate entry lines follow double-entry bookkeeping
        is_valid, error_msg = DoubleEntryValidator.validate_entry_lines(data['lines'])
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # Parse entry date
        try:
            entry_date = datetime.strptime(data['entry_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Create main journal entry record
        je_number = generate_entry_number()
        journal_entry = JournalEntry(
            entry_number=je_number,
            entry_date=entry_date,
            description=data['description'],
            account_id=data['lines'][0]['account_id'],  # First account for reference
            debit=Decimal(str(data['lines'][0].get('debit', 0))),
            credit=Decimal(str(data['lines'][0].get('credit', 0))),
            reference=data.get('reference'),
            status='posted',
            created_by=current_user.id
        )
        
        db.session.add(journal_entry)
        db.session.flush()  # Flush to get the ID without committing
        
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        entry_lines_data = []
        
        # Process each line in the entry
        for line in data['lines']:
            account_id = line['account_id']
            debit = Decimal(str(line.get('debit', 0)))
            credit = Decimal(str(line.get('credit', 0)))
            
            account = Account.query.get(account_id)
            
            # Update account balance
            if debit > 0:
                account.balance += debit
            if credit > 0:
                account.balance -= credit
            
            # Create ledger entry
            ledger_entry = Ledger(
                account_id=account_id,
                journal_entry_id=journal_entry.id,
                entry_date=entry_date,
                description=data['description'],
                debit=debit,
                credit=credit,
                running_balance=account.balance,
                reference=data.get('reference')
            )
            
            db.session.add(ledger_entry)
            
            total_debit += debit
            total_credit += credit
            
            entry_lines_data.append({
                'account_id': account_id,
                'account_code': account.account_code,
                'account_name': account.account_name,
                'debit': float(debit),
                'credit': float(credit)
            })
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'message': 'Journal entry created successfully',
            'entry_id': journal_entry.id,
            'entry_number': journal_entry.entry_number,
            'entry_date': entry_date.isoformat(),
            'description': data['description'],
            'lines': entry_lines_data,
            'total_debit': float(total_debit),
            'total_credit': float(total_credit),
            'is_balanced': total_debit == total_credit
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error creating journal entry: {str(e)}'}), 500

@transactions_bp.route('/', methods=['GET'])
@login_required
def get_journal_entries():
    """Get all journal entries with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        account_id = request.args.get('account_id', type=int)
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = JournalEntry.query
        
        if account_id:
            query = query.filter_by(account_id=account_id)
        if status:
            query = query.filter_by(status=status)
        
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(JournalEntry.entry_date >= start_date_obj)
        
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(JournalEntry.entry_date <= end_date_obj)
        
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
            'status': entry.status,
            'created_by': entry.created_by
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
    """Get specific journal entry with all its lines"""
    try:
        entry = JournalEntry.query.get_or_404(entry_id)
        
        # Get all ledger entries for this journal entry
        ledger_entries = Ledger.query.filter_by(journal_entry_id=entry_id).all()
        
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        lines = []
        
        for ledger in ledger_entries:
            total_debit += ledger.debit
            total_credit += ledger.credit
            
            lines.append({
                'ledger_id': ledger.id,
                'account_id': ledger.account_id,
                'account_code': ledger.account.account_code,
                'account_name': ledger.account.account_name,
                'account_type': ledger.account.account_type,
                'debit': float(ledger.debit),
                'credit': float(ledger.credit),
                'running_balance': float(ledger.running_balance)
            })
        
        return jsonify({
            'id': entry.id,
            'entry_number': entry.entry_number,
            'entry_date': entry.entry_date.isoformat(),
            'description': entry.description,
            'reference': entry.reference,
            'status': entry.status,
            'lines': lines,
            'total_debit': float(total_debit),
            'total_credit': float(total_credit),
            'is_balanced': total_debit == total_credit,
            'created_at': entry.created_at.isoformat(),
            'created_by': entry.created_by
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@transactions_bp.route('/<int:entry_id>', methods=['PUT'])
@login_required
def update_journal_entry(entry_id):
    """Update journal entry (only if status is draft)"""
    try:
        entry = JournalEntry.query.get_or_404(entry_id)
        data = request.get_json()
        
        if entry.status == 'posted':
            return jsonify({'error': 'Cannot modify posted entries. Audit trail requires original entries to remain unchanged.'}), 403
        
        if entry.status == 'reversed':
            return jsonify({'error': 'Cannot modify reversed entries.'}), 403
        
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

@transactions_bp.route('/<int:entry_id>/reverse', methods=['POST'])
@login_required
def reverse_journal_entry(entry_id):
    """Reverse a journal entry by creating an opposite entry"""
    try:
        original_entry = JournalEntry.query.get_or_404(entry_id)
        data = request.get_json()
        
        if original_entry.status == 'reversed':
            return jsonify({'error': 'This entry has already been reversed'}), 400
        
        reversal_reason = data.get('reason', 'Reversal of entry ' + original_entry.entry_number)
        
        # Get all lines from the original entry
        original_lines = Ledger.query.filter_by(journal_entry_id=entry_id).all()
        
        if not original_lines:
            return jsonify({'error': 'Original entry has no lines to reverse'}), 400
        
        # Create reversed entry lines (swap debits and credits)
        reversed_lines = []
        for line in original_lines:
            reversed_lines.append({
                'account_id': line.account_id,
                'debit': float(line.credit),
                'credit': float(line.debit)
            })
        
        # Create the reversal entry
        reversal_entry_data = {
            'entry_date': datetime.now().date().isoformat(),
            'description': reversal_reason,
            'reference': f'REV-{original_entry.entry_number}',
            'lines': reversed_lines
        }
        
        # Create the reversal entry using the main creation logic
        je_number = generate_entry_number()
        reversal_entry = JournalEntry(
            entry_number=je_number,
            entry_date=datetime.now().date(),
            description=reversal_reason,
            account_id=reversed_lines[0]['account_id'],
            debit=Decimal(str(reversed_lines[0].get('debit', 0))),
            credit=Decimal(str(reversed_lines[0].get('credit', 0))),
            reference=f'REV-{original_entry.entry_number}',
            status='posted',
            created_by=current_user.id
        )
        
        db.session.add(reversal_entry)
        db.session.flush()
        
        # Process reversal lines
        for line in reversed_lines:
            account_id = line['account_id']
            debit = Decimal(str(line.get('debit', 0)))
            credit = Decimal(str(line.get('credit', 0)))
            
            account = Account.query.get(account_id)
            
            # Update account balance (reverse the original)
            if debit > 0:
                account.balance += debit
            if credit > 0:
                account.balance -= credit
            
            # Create ledger entry for reversal
            ledger_entry = Ledger(
                account_id=account_id,
                journal_entry_id=reversal_entry.id,
                entry_date=datetime.now().date(),
                description=reversal_reason,
                debit=debit,
                credit=credit,
                running_balance=account.balance,
                reference=f'REV-{original_entry.entry_number}'
            )
            
            db.session.add(ledger_entry)
        
        # Mark original as reversed
        original_entry.status = 'reversed'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Journal entry reversed successfully',
            'original_entry_id': original_entry.id,
            'original_entry_number': original_entry.entry_number,
            'reversal_entry_id': reversal_entry.id,
            'reversal_entry_number': reversal_entry.entry_number,
            'reversal_date': datetime.now().date().isoformat()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/validate', methods=['POST'])
@login_required
def validate_entry():
    """Validate a journal entry before posting (without creating it)"""
    try:
        data = request.get_json()
        
        if 'lines' not in data:
            return jsonify({'error': 'Missing lines field'}), 400
        
        is_valid, error_msg = DoubleEntryValidator.validate_entry_lines(data['lines'])
        
        if not is_valid:
            return jsonify({
                'is_valid': False,
                'error': error_msg
            }), 400
        
        # Calculate totals
        total_debit = sum(Decimal(str(line.get('debit', 0))) for line in data['lines'])
        total_credit = sum(Decimal(str(line.get('credit', 0))) for line in data['lines'])
        
        return jsonify({
            'is_valid': True,
            'total_debit': float(total_debit),
            'total_credit': float(total_credit),
            'number_of_lines': len(data['lines']),
            'message': 'Entry is valid and follows double-entry bookkeeping principles'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@transactions_bp.route('/balance-check', methods=['GET'])
@login_required
def check_balance():
    """Verify that all debits equal all credits across all entries"""
    try:
        all_debits = db.session.query(db.func.sum(Ledger.debit)).scalar() or Decimal('0.00')
        all_credits = db.session.query(db.func.sum(Ledger.credit)).scalar() or Decimal('0.00')
        
        is_balanced = all_debits == all_credits
        
        return jsonify({
            'total_debits': float(all_debits),
            'total_credits': float(all_credits),
            'is_balanced': is_balanced,
            'difference': float(abs(all_debits - all_credits)) if not is_balanced else 0.00,
            'status': 'Books are balanced' if is_balanced else 'Books are NOT balanced - audit required'
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
