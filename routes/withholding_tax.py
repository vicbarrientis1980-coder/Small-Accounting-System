from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from models.withholding_tax import WithholdingTax
from models.account import Account
from datetime import datetime
from decimal import Decimal
from utils.error_handler import InputValidator, ErrorHandler, ValidationError

withholding_tax_bp = Blueprint('withholding_tax', __name__, url_prefix='/api/withholding-tax')

def generate_withholding_tax_number():
    """Generate unique withholding tax number"""
    last_record = WithholdingTax.query.order_by(WithholdingTax.id.desc()).first()
    if last_record:
        num = int(last_record.withholding_tax_number.split('-')[1]) + 1
    else:
        num = 1
    return f"WT-{num:06d}"

@withholding_tax_bp.route('/', methods=['POST'])
@login_required
def create_withholding_tax():
    """Create a new withholding tax record"""
    try:
        data = request.get_json()
        
        # Validate required fields
        tax_type = InputValidator.validate_string(data.get('tax_type'), 'Tax Type')
        tax_rate = InputValidator.validate_decimal(data.get('tax_rate'), 'Tax Rate', min_value=0, max_value=1)
        payee_name = InputValidator.validate_string(data.get('payee_name'), 'Payee Name')
        payee_tin = InputValidator.validate_tin(data.get('payee_tin'))
        transaction_date = InputValidator.validate_date(data.get('transaction_date'), 'Transaction Date')
        gross_amount = InputValidator.validate_decimal(data.get('gross_amount'), 'Gross Amount', min_value=0)
        withholding_tax_amount = InputValidator.validate_decimal(data.get('withholding_tax_amount'), 'Withholding Tax Amount', min_value=0)
        
        # Calculate net amount
        net = gross_amount - withholding_tax_amount
        
        # Create withholding tax record
        wht = WithholdingTax(
            withholding_tax_number=generate_withholding_tax_number(),
            withholding_date=datetime.now().date(),
            tax_type=tax_type,
            tax_rate=tax_rate,
            payee_name=payee_name,
            payee_tin=payee_tin,
            payee_address=InputValidator.validate_string(data.get('payee_address'), 'Payee Address', required=False, max_length=500),
            payee_type=InputValidator.validate_string(data.get('payee_type', 'Individual'), 'Payee Type'),
            payor_name=InputValidator.validate_string(data.get('payor_name'), 'Payor Name', required=False),
            payor_tin=InputValidator.validate_tin(data.get('payor_tin')),
            transaction_description=InputValidator.validate_string(data.get('transaction_description'), 'Transaction Description', required=False, max_length=500),
            invoice_number=InputValidator.validate_string(data.get('invoice_number'), 'Invoice Number', required=False, max_length=100),
            transaction_date=transaction_date,
            gross_amount=gross_amount,
            withholding_tax_amount=withholding_tax_amount,
            net_amount=net,
            notes=InputValidator.validate_string(data.get('notes'), 'Notes', required=False, max_length=1000),
            created_by=current_user.id
        )
        
        db.session.add(wht)
        db.session.commit()
        
        return jsonify({
            'message': 'Withholding tax record created successfully',
            'withholding_tax_id': wht.id,
            'withholding_tax_number': wht.withholding_tax_number,
            'net_amount': float(net)
        }), 201
    
    except ValidationError as e:
        return ErrorHandler.handle_validation_error(e)
    except Exception as e:
        db.session.rollback()
        return ErrorHandler.handle_generic_error(e)

@withholding_tax_bp.route('/', methods=['GET'])
@login_required
def get_withholding_taxes():
    """Get all withholding tax records"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        tax_type = request.args.get('tax_type')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        payee_tin = request.args.get('payee_tin')
        
        query = WithholdingTax.query
        
        if tax_type:
            tax_type = InputValidator.validate_string(tax_type, 'Tax Type')
            query = query.filter_by(tax_type=tax_type)
        if status:
            status = InputValidator.validate_string(status, 'Status')
            query = query.filter_by(status=status)
        if payee_tin:
            payee_tin = InputValidator.validate_tin(payee_tin)
            query = query.filter_by(payee_tin=payee_tin)
        
        if start_date:
            start_date_obj = InputValidator.validate_date(start_date, 'Start Date')
            query = query.filter(WithholdingTax.transaction_date >= start_date_obj)
        
        if end_date:
            end_date_obj = InputValidator.validate_date(end_date, 'End Date')
            query = query.filter(WithholdingTax.transaction_date <= end_date_obj)
        
        paginated = query.order_by(WithholdingTax.transaction_date.desc()).paginate(page=page, per_page=per_page)
        
        records = [{
            'id': wht.id,
            'withholding_tax_number': wht.withholding_tax_number,
            'tax_type': wht.tax_type,
            'payee_name': wht.payee_name,
            'payee_tin': wht.payee_tin,
            'gross_amount': float(wht.gross_amount),
            'withholding_tax_amount': float(wht.withholding_tax_amount),
            'net_amount': float(wht.net_amount),
            'status': wht.status,
            'transaction_date': wht.transaction_date.isoformat()
        } for wht in paginated.items]
        
        return jsonify({
            'records': records,
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page
        }), 200
    
    except ValidationError as e:
        return ErrorHandler.handle_validation_error(e)
    except Exception as e:
        return ErrorHandler.handle_generic_error(e)

@withholding_tax_bp.route('/<int:wht_id>', methods=['GET'])
@login_required
def get_withholding_tax(wht_id):
    """Get specific withholding tax record"""
    try:
        wht = WithholdingTax.query.get_or_404(wht_id)
        
        return jsonify({
            'id': wht.id,
            'withholding_tax_number': wht.withholding_tax_number,
            'withholding_date': wht.withholding_date.isoformat(),
            'tax_type': wht.tax_type,
            'tax_rate': float(wht.tax_rate),
            'payee_name': wht.payee_name,
            'payee_tin': wht.payee_tin,
            'payee_address': wht.payee_address,
            'payee_type': wht.payee_type,
            'payor_name': wht.payor_name,
            'payor_tin': wht.payor_tin,
            'transaction_description': wht.transaction_description,
            'invoice_number': wht.invoice_number,
            'transaction_date': wht.transaction_date.isoformat(),
            'gross_amount': float(wht.gross_amount),
            'withholding_tax_amount': float(wht.withholding_tax_amount),
            'net_amount': float(wht.net_amount),
            'status': wht.status,
            'form_2307_number': wht.form_2307_number,
            'filing_date': wht.filing_date.isoformat() if wht.filing_date else None,
            'payment_date': wht.payment_date.isoformat() if wht.payment_date else None,
            'notes': wht.notes
        }), 200
    
    except Exception as e:
        return ErrorHandler.handle_generic_error(e)

@withholding_tax_bp.route('/<int:wht_id>/file-form-2307', methods=['PUT'])
@login_required
def file_form_2307(wht_id):
    """Update withholding tax status to filed and assign Form 2307"""
    try:
        wht = WithholdingTax.query.get_or_404(wht_id)
        data = request.get_json()
        
        form_2307_number = InputValidator.validate_string(data.get('form_2307_number'), 'Form 2307 Number')
        
        wht.form_2307_number = form_2307_number
        wht.filing_date = datetime.now().date()
        wht.status = 'filed'
        wht.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Withholding tax filed successfully',
            'form_2307_number': wht.form_2307_number,
            'filing_date': wht.filing_date.isoformat()
        }), 200
    
    except ValidationError as e:
        return ErrorHandler.handle_validation_error(e)
    except Exception as e:
        db.session.rollback()
        return ErrorHandler.handle_generic_error(e)

@withholding_tax_bp.route('/summary/monthly', methods=['GET'])
@login_required
def get_monthly_summary():
    """Get monthly withholding tax summary"""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        tax_type = request.args.get('tax_type')
        
        query = WithholdingTax.query
        
        if year and month:
            query = query.filter(
                db.func.extract('year', WithholdingTax.transaction_date) == year,
                db.func.extract('month', WithholdingTax.transaction_date) == month
            )
        
        if tax_type:
            tax_type = InputValidator.validate_string(tax_type, 'Tax Type')
            query = query.filter_by(tax_type=tax_type)
        
        records = query.all()
        
        total_gross = sum(Decimal(str(r.gross_amount)) for r in records)
        total_tax = sum(Decimal(str(r.withholding_tax_amount)) for r in records)
        total_net = sum(Decimal(str(r.net_amount)) for r in records)
        
        return jsonify({
            'period': f"{year}-{month:02d}" if year and month else 'All',
            'total_records': len(records),
            'total_gross_amount': float(total_gross),
            'total_withholding_tax': float(total_tax),
            'total_net_amount': float(total_net),
            'records_by_type': dict([
                (tax_type, len([r for r in records if r.tax_type == tax_type]))
                for tax_type in set(r.tax_type for r in records)
            ])
        }), 200
    
    except Exception as e:
        return ErrorHandler.handle_generic_error(e)
