from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from models.account import Account
from models.ledger import Ledger
from datetime import datetime
from sqlalchemy import func

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('/trial-balance', methods=['GET'])
@login_required
def trial_balance():
    """Generate Trial Balance Report"""
    try:
        date = request.args.get('date')
        if date:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            date = datetime.today().date()
        
        accounts = Account.query.filter_by(is_active=True).all()
        
        trial_balance_data = []
        total_debits = 0
        total_credits = 0
        
        for account in accounts:
            # Calculate balance based on account type
            balance = account.get_balance()
            
            # Debits and credits depend on account type
            if account.account_type in ['Asset', 'Expense']:
                if balance > 0:
                    total_debits += balance
                else:
                    total_credits += abs(balance)
            else:  # Liability, Equity, Revenue
                if balance > 0:
                    total_credits += balance
                else:
                    total_debits += abs(balance)
            
            trial_balance_data.append({
                'account_code': account.account_code,
                'account_name': account.account_name,
                'account_type': account.account_type,
                'balance': balance
            })
        
        return jsonify({
            'date': date.isoformat(),
            'accounts': trial_balance_data,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'is_balanced': total_debits == total_credits
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/balance-sheet', methods=['GET'])
@login_required
def balance_sheet():
    """Generate Balance Sheet Report"""
    try:
        date = request.args.get('date')
        if date:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            date = datetime.today().date()
        
        # Get accounts by type
        assets = Account.query.filter_by(account_type='Asset', is_active=True).all()
        liabilities = Account.query.filter_by(account_type='Liability', is_active=True).all()
        equity = Account.query.filter_by(account_type='Equity', is_active=True).all()
        
        def calculate_section_total(accounts):
            return sum(acc.get_balance() for acc in accounts)
        
        assets_total = calculate_section_total(assets)
        liabilities_total = calculate_section_total(liabilities)
        equity_total = calculate_section_total(equity)
        
        return jsonify({
            'date': date.isoformat(),
            'assets': [{
                'account_code': acc.account_code,
                'account_name': acc.account_name,
                'balance': acc.get_balance()
            } for acc in assets],
            'assets_total': assets_total,
            'liabilities': [{
                'account_code': acc.account_code,
                'account_name': acc.account_name,
                'balance': acc.get_balance()
            } for acc in liabilities],
            'liabilities_total': liabilities_total,
            'equity': [{
                'account_code': acc.account_code,
                'account_name': acc.account_name,
                'balance': acc.get_balance()
            } for acc in equity],
            'equity_total': equity_total,
            'total_liabilities_equity': liabilities_total + equity_total
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/income-statement', methods=['GET'])
@login_required
def income_statement():
    """Generate Income Statement Report"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date parameters required'}), 400
        
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get revenue and expense accounts
        revenues = Account.query.filter_by(account_type='Revenue', is_active=True).all()
        expenses = Account.query.filter_by(account_type='Expense', is_active=True).all()
        
        revenue_total = sum(acc.get_balance() for acc in revenues)
        expense_total = sum(acc.get_balance() for acc in expenses)
        net_income = revenue_total - expense_total
        
        return jsonify({
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'revenues': [{
                'account_code': acc.account_code,
                'account_name': acc.account_name,
                'amount': acc.get_balance()
            } for acc in revenues],
            'revenue_total': revenue_total,
            'expenses': [{
                'account_code': acc.account_code,
                'account_name': acc.account_name,
                'amount': acc.get_balance()
            } for acc in expenses],
            'expense_total': expense_total,
            'net_income': net_income
        }), 200
    
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/general-ledger/<int:account_id>', methods=['GET'])
@login_required
def general_ledger(account_id):
    """Generate General Ledger Report for specific account"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        account = Account.query.get_or_404(account_id)
        
        query = Ledger.query.filter_by(account_id=account_id)
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Ledger.entry_date >= start_date)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Ledger.entry_date <= end_date)
        
        paginated = query.order_by(Ledger.entry_date.asc()).paginate(page=page, per_page=per_page)
        
        ledger_entries = [{
            'id': entry.id,
            'entry_date': entry.entry_date.isoformat(),
            'description': entry.description,
            'debit': float(entry.debit),
            'credit': float(entry.credit),
            'running_balance': float(entry.running_balance),
            'reference': entry.reference
        } for entry in paginated.items]
        
        return jsonify({
            'account_code': account.account_code,
            'account_name': account.account_name,
            'account_type': account.account_type,
            'entries': ledger_entries,
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
