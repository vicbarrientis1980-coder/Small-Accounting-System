from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from models.subsidiary_ledger import SubsidiaryLedger
from models.account import Account
from datetime import datetime
from decimal import Decimal
from utils.error_handler import InputValidator, ErrorHandler, ValidationError

subsidiary_ledger_bp = Blueprint('subsidiary_ledger', __name__, url_prefix='/api/subsidiary-ledger')

@subsidiary_ledger_bp.route('/', methods=['POST'])
@login_required
def create_subsidiary_entry():
    """Create a new subsidiary ledger entry"""
    try:
        data = request.get_json()
        
        # Validate required fields
        account_id = data.get('account_id')
        entity_name = InputValidator.validate_string(data.get('entity_name'), 'Entity Name', max_length=255)
        entity_code = InputValidator.validate_string(data.get('entity_code'), 'Entity Code', max_length=50)
        subsidiary_type = InputValidator.validate_string(data.get('subsidiary_type'), 'Subsidiary Type', max_length=50)
        transaction_date = InputValidator.validate_date(data.get('transaction_date'), 'Transaction Date')
        debit = InputValidator.validate_decimal(data.get('debit', 0), 'Debit', required=False)
        credit = InputValidator.validate_decimal(data.get('credit', 0), 'Credit', required=False)
        
        if not account_id:
            raise ValidationError('Account ID is required', 'account_id', 'REQUIRED_FIELD')
        
        # Verify account exists
        account = Account.query.get(account_id)
        if not account:
            return ErrorHandler.handle_not_found('Account')
        
        # Create subsidiary ledger entry
        entry = SubsidiaryLedger(
            account_id=account_id,
            subsidiary_type=subsidiary_type,
            entity_name=entity_name,
            entity_code=entity_code,
            transaction_date=transaction_date,
            description=InputValidator.validate_string(data.get('description'), 'Description', required=False, max_length=500),
            reference=InputValidator.validate_string(data.get('reference'), 'Reference', required=False, max_length=100),
            debit=debit,
            credit=credit
        )
        
        # Calculate running balance
        last_entry = SubsidiaryLedger.query.filter_by(
            account_id=account_id,
            entity_code=entity_code
        ).order_by(SubsidiaryLedger.id.desc()).first()
        
        if last_entry:
            previous_balance = Decimal(str(last_entry.running_balance))
        else:
            previous_balance = Decimal('0.00')
        
        entry.running_balance = previous_balance + debit - credit
        
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({
            'message': 'Subsidiary ledger entry created successfully',
            'entry_id': entry.id,
            'entity_name': entry.entity_name,
            'running_balance': float(entry.running_balance)
        }), 201
    
    except ValidationError as e:
        return ErrorHandler.handle_validation_error(e)
    except Exception as e:
        db.session.rollback()
        return ErrorHandler.handle_generic_error(e)

@subsidiary_ledger_bp.route('/account/<int:account_id>', methods=['GET'])
@login_required
def get_subsidiary_ledger_by_account(account_id):
    """Get subsidiary ledger for specific account"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        entity_code = request.args.get('entity_code')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Verify account exists
        account = Account.query.get_or_404(account_id)
        
        query = SubsidiaryLedger.query.filter_by(account_id=account_id)
        
        if entity_code:
            entity_code = InputValidator.validate_string(entity_code, 'Entity Code')
            query = query.filter_by(entity_code=entity_code)
        
        if start_date:
            start_date_obj = InputValidator.validate_date(start_date, 'Start Date')
            query = query.filter(SubsidiaryLedger.transaction_date >= start_date_obj)
        
        if end_date:
            end_date_obj = InputValidator.validate_date(end_date, 'End Date')
            query = query.filter(SubsidiaryLedger.transaction_date <= end_date_obj)
        
        paginated = query.order_by(SubsidiaryLedger.transaction_date.asc()).paginate(page=page, per_page=per_page)
        
        entries = [{
            'id': entry.id,
            'subsidiary_type': entry.subsidiary_type,
            'entity_name': entry.entity_name,
            'entity_code': entry.entity_code,
            'transaction_date': entry.transaction_date.isoformat(),
            'description': entry.description,
            'reference': entry.reference,
            'debit': float(entry.debit),
            'credit': float(entry.credit),
            'running_balance': float(entry.running_balance)
        } for entry in paginated.items]
        
        return jsonify({
            'entries': entries,
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page
        }), 200
    
    except ValidationError as e:
        return ErrorHandler.handle_validation_error(e)
    except Exception as e:
        return ErrorHandler.handle_generic_error(e)

@subsidiary_ledger_bp.route('/summary', methods=['GET'])
@login_required
def get_subsidiary_summary():
    """Get summary of all subsidiary ledgers by entity"""
    try:
        subsidiary_type = request.args.get('subsidiary_type')
        
        query = SubsidiaryLedger.query
        
        if subsidiary_type:
            subsidiary_type = InputValidator.validate_string(subsidiary_type, 'Subsidiary Type')
            query = query.filter_by(subsidiary_type=subsidiary_type)
        
        entries = query.all()
        
        summary = {}
        for entry in entries:
            key = f"{entry.entity_code}_{entry.entity_name}"
            if key not in summary:
                summary[key] = {
                    'entity_code': entry.entity_code,
                    'entity_name': entry.entity_name,
                    'total_debit': Decimal('0.00'),
                    'total_credit': Decimal('0.00'),
                    'balance': Decimal('0.00')
                }
            summary[key]['total_debit'] += entry.debit
            summary[key]['total_credit'] += entry.credit
            summary[key]['balance'] = entry.running_balance
        
        summary_data = [{
            'entity_code': v['entity_code'],
            'entity_name': v['entity_name'],
            'total_debit': float(v['total_debit']),
            'total_credit': float(v['total_credit']),
            'balance': float(v['balance'])
        } for v in summary.values()]
        
        return jsonify({
            'summary': summary_data,
            'total_entries': len(entries)
        }), 200
    
    except ValidationError as e:
        return ErrorHandler.handle_validation_error(e)
    except Exception as e:
        return ErrorHandler.handle_generic_error(e)
