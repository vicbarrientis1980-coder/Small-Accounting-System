from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from models.bir_form_2307 import BIRForm2307
from models.withholding_tax import WithholdingTax
from datetime import datetime
from decimal import Decimal
from utils.error_handler import InputValidator, ErrorHandler, ValidationError

bir_form_2307_bp = Blueprint('bir_form_2307', __name__, url_prefix='/api/bir-form-2307')

def generate_form_number():
    """Generate unique BIR Form 2307 number"""
    last_form = BIRForm2307.query.order_by(BIRForm2307.id.desc()).first()
    if last_form:
        num = int(last_form.form_number.split('-')[1]) + 1
    else:
        num = 1
    return f"F2307-{num:06d}"

@bir_form_2307_bp.route('/', methods=['POST'])
@login_required
def create_bir_form_2307():
    """Create a new BIR Form 2307"""
    try:
        data = request.get_json()
        
        # Validate required fields
        withholding_agent_name = InputValidator.validate_string(data.get('withholding_agent_name'), 'Withholding Agent Name')
        withholding_agent_tin = InputValidator.validate_tin(data.get('withholding_agent_tin'))
        withholding_agent_address = InputValidator.validate_string(data.get('withholding_agent_address'), 'Withholding Agent Address')
        payee_name = InputValidator.validate_string(data.get('payee_name'), 'Payee Name')
        gross_payment = InputValidator.validate_decimal(data.get('gross_payment'), 'Gross Payment', min_value=0)
        tax_withheld = InputValidator.validate_decimal(data.get('tax_withheld'), 'Tax Withheld', min_value=0)
        tax_type = InputValidator.validate_string(data.get('tax_type'), 'Tax Type')
        tax_rate = InputValidator.validate_decimal(data.get('tax_rate'), 'Tax Rate', min_value=0, max_value=1)
        
        # Calculate net payment
        net = gross_payment - tax_withheld
        
        # Create BIR Form 2307
        form = BIRForm2307(
            form_number=generate_form_number(),
            form_date=InputValidator.validate_date(data.get('form_date', datetime.now().date().isoformat()), 'Form Date'),
            withholding_agent_name=withholding_agent_name,
            withholding_agent_tin=withholding_agent_tin,
            withholding_agent_address=withholding_agent_address,
            withholding_agent_contact=InputValidator.validate_phone(data.get('withholding_agent_contact')),
            payee_name=payee_name,
            payee_tin=InputValidator.validate_tin(data.get('payee_tin')),
            payee_address=InputValidator.validate_string(data.get('payee_address'), 'Payee Address', required=False, max_length=500),
            payee_contact=InputValidator.validate_phone(data.get('payee_contact')),
            withholding_month_year=InputValidator.validate_string(data.get('withholding_month_year'), 'Withholding Month/Year', required=False, max_length=7),
            nature_of_payment=InputValidator.validate_string(data.get('nature_of_payment'), 'Nature of Payment', required=False, max_length=255),
            tax_type=tax_type,
            atc_code=InputValidator.validate_string(data.get('atc_code'), 'ATC Code', required=False, max_length=10),
            tax_rate=tax_rate,
            gross_payment=gross_payment,
            tax_withheld=tax_withheld,
            net_payment=net,
            number_of_transactions=data.get('number_of_transactions', 1),
            invoices=InputValidator.validate_string(data.get('invoices'), 'Invoices', required=False, max_length=500),
            withholding_tax_ids=InputValidator.validate_string(data.get('withholding_tax_ids'), 'Withholding Tax IDs', required=False, max_length=500),
            notes=InputValidator.validate_string(data.get('notes'), 'Notes', required=False, max_length=1000),
            prepared_by=current_user.id
        )
        
        db.session.add(form)
        db.session.commit()
        
        return jsonify({
            'message': 'BIR Form 2307 created successfully',
            'form_id': form.id,
            'form_number': form.form_number
        }), 201
    
    except ValidationError as e:
        return ErrorHandler.handle_validation_error(e)
    except Exception as e:
        db.session.rollback()
        return ErrorHandler.handle_generic_error(e)

@bir_form_2307_bp.route('/', methods=['GET'])
@login_required
def get_bir_forms():
    """Get all BIR Form 2307 records"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        filing_status = request.args.get('filing_status')
        tax_type = request.args.get('tax_type')
        payee_tin = request.args.get('payee_tin')
        
        query = BIRForm2307.query
        
        if filing_status:
            filing_status = InputValidator.validate_string(filing_status, 'Filing Status')
            query = query.filter_by(filing_status=filing_status)
        if tax_type:
            tax_type = InputValidator.validate_string(tax_type, 'Tax Type')
            query = query.filter_by(tax_type=tax_type)
        if payee_tin:
            payee_tin = InputValidator.validate_tin(payee_tin)
            query = query.filter_by(payee_tin=payee_tin)
        
        paginated = query.order_by(BIRForm2307.form_date.desc()).paginate(page=page, per_page=per_page)
        
        forms = [{
            'id': form.id,
            'form_number': form.form_number,
            'form_date': form.form_date.isoformat(),
            'payee_name': form.payee_name,
            'payee_tin': form.payee_tin,
            'gross_payment': float(form.gross_payment),
            'tax_withheld': float(form.tax_withheld),
            'net_payment': float(form.net_payment),
            'tax_type': form.tax_type,
            'filing_status': form.filing_status,
            'bir_receipt_number': form.bir_receipt_number
        } for form in paginated.items]
        
        return jsonify({
            'forms': forms,
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page
        }), 200
    
    except ValidationError as e:
        return ErrorHandler.handle_validation_error(e)
    except Exception as e:
        return ErrorHandler.handle_generic_error(e)

@bir_form_2307_bp.route('/<int:form_id>', methods=['GET'])
@login_required
def get_bir_form(form_id):
    """Get specific BIR Form 2307"""
    try:
        form = BIRForm2307.query.get_or_404(form_id)
        
        return jsonify({
            'id': form.id,
            'form_number': form.form_number,
            'form_date': form.form_date.isoformat(),
            'withholding_agent_name': form.withholding_agent_name,
            'withholding_agent_tin': form.withholding_agent_tin,
            'withholding_agent_address': form.withholding_agent_address,
            'payee_name': form.payee_name,
            'payee_tin': form.payee_tin,
            'payee_address': form.payee_address,
            'nature_of_payment': form.nature_of_payment,
            'tax_type': form.tax_type,
            'atc_code': form.atc_code,
            'tax_rate': float(form.tax_rate),
            'gross_payment': float(form.gross_payment),
            'tax_withheld': float(form.tax_withheld),
            'net_payment': float(form.net_payment),
            'number_of_transactions': form.number_of_transactions,
            'invoices': form.invoices,
            'withholding_month_year': form.withholding_month_year,
            'filing_status': form.filing_status,
            'bir_receipt_number': form.bir_receipt_number,
            'filing_date': form.filing_date.isoformat() if form.filing_date else None,
            'notes': form.notes
        }), 200
    
    except Exception as e:
        return ErrorHandler.handle_generic_error(e)

@bir_form_2307_bp.route('/<int:form_id>/file', methods=['PUT'])
@login_required
def file_bir_form(form_id):
    """File BIR Form 2307"""
    try:
        form = BIRForm2307.query.get_or_404(form_id)
        data = request.get_json()
        
        bir_receipt_number = InputValidator.validate_string(data.get('bir_receipt_number'), 'BIR Receipt Number')
        
        form.filing_status = 'filed'
        form.bir_receipt_number = bir_receipt_number
        form.filing_date = datetime.now().date()
        form.approved_by = current_user.id
        form.approval_date = datetime.utcnow()
        form.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'BIR Form 2307 filed successfully',
            'bir_receipt_number': form.bir_receipt_number,
            'filing_date': form.filing_date.isoformat()
        }), 200
    
    except ValidationError as e:
        return ErrorHandler.handle_validation_error(e)
    except Exception as e:
        db.session.rollback()
        return ErrorHandler.handle_generic_error(e)

@bir_form_2307_bp.route('/summary', methods=['GET'])
@login_required
def get_bir_summary():
    """Get summary of all BIR Form 2307 records"""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        tax_type = request.args.get('tax_type')
        
        query = BIRForm2307.query.filter(BIRForm2307.filing_status != 'cancelled')
        
        if year and month:
            query = query.filter(
                db.func.extract('year', BIRForm2307.form_date) == year,
                db.func.extract('month', BIRForm2307.form_date) == month
            )
        
        if tax_type:
            tax_type = InputValidator.validate_string(tax_type, 'Tax Type')
            query = query.filter_by(tax_type=tax_type)
        
        forms = query.all()
        
        total_gross = sum(Decimal(str(f.gross_payment)) for f in forms)
        total_tax = sum(Decimal(str(f.tax_withheld)) for f in forms)
        total_net = sum(Decimal(str(f.net_payment)) for f in forms)
        
        filed_count = len([f for f in forms if f.filing_status == 'filed'])
        draft_count = len([f for f in forms if f.filing_status == 'draft'])
        amended_count = len([f for f in forms if f.filing_status == 'amended'])
        
        return jsonify({
            'period': f"{year}-{month:02d}" if year and month else 'All',
            'total_forms': len(forms),
            'filed_forms': filed_count,
            'draft_forms': draft_count,
            'amended_forms': amended_count,
            'total_gross_payment': float(total_gross),
            'total_tax_withheld': float(total_tax),
            'total_net_payment': float(total_net),
            'payees': len(set(f.payee_tin for f in forms if f.payee_tin))
        }), 200
    
    except Exception as e:
        return ErrorHandler.handle_generic_error(e)
