from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from models.account import Account
from models.journal_entry import JournalEntry
from models.ledger import Ledger
from models.withholding_tax import WithholdingTax
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

# ======================= TRIAL BALANCE =======================
@reports_bp.route('/trial-balance', methods=['GET'])
@login_required
def trial_balance():
    """Generate Trial Balance Report - shows all accounts with their debit/credit balances"""
    try:
        as_of_date = request.args.get('as_of_date')
        if as_of_date:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        else:
            as_of_date = datetime.today().date()
        
        accounts = Account.query.filter_by(is_active=True).all()
        
        trial_balance_data = []
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')
        
        for account in accounts:
            balance = Decimal(str(account.balance))
            
            # Determine if balance is debit or credit based on account type
            if account.account_type in ['Asset', 'Expense']:
                if balance >= 0:
                    debit = balance
                    credit = Decimal('0.00')
                    total_debits += balance
                else:
                    debit = Decimal('0.00')
                    credit = abs(balance)
                    total_credits += abs(balance)
            else:  # Liability, Equity, Revenue
                if balance >= 0:
                    credit = balance
                    debit = Decimal('0.00')
                    total_credits += balance
                else:
                    debit = abs(balance)
                    credit = Decimal('0.00')
                    total_debits += abs(balance)
            
            trial_balance_data.append({
                'account_code': account.account_code,
                'account_name': account.account_name,
                'account_type': account.account_type,
                'debit': float(debit),
                'credit': float(credit),
                'balance': float(balance)
            })
        
        return jsonify({
            'report_type': 'Trial Balance',
            'as_of_date': as_of_date.isoformat(),
            'accounts': trial_balance_data,
            'total_debits': float(total_debits),
            'total_credits': float(total_credits),
            'is_balanced': total_debits == total_credits,
            'difference': float(abs(total_debits - total_credits)) if total_debits != total_credits else 0.00
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= BALANCE SHEET =======================
@reports_bp.route('/balance-sheet', methods=['GET'])
@login_required
def balance_sheet():
    """Generate Balance Sheet Report - shows Assets, Liabilities, and Equity as of a specific date"""
    try:
        as_of_date = request.args.get('as_of_date')
        if as_of_date:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        else:
            as_of_date = datetime.today().date()
        
        # Get accounts by type
        assets = Account.query.filter_by(account_type='Asset', is_active=True).all()
        liabilities = Account.query.filter_by(account_type='Liability', is_active=True).all()
        equity = Account.query.filter_by(account_type='Equity', is_active=True).all()
        
        def calculate_section_total(accounts):
            return sum(Decimal(str(acc.balance)) for acc in accounts)
        
        # Calculate totals
        assets_total = calculate_section_total(assets)
        liabilities_total = calculate_section_total(liabilities)
        equity_total = calculate_section_total(equity)
        total_liabilities_equity = liabilities_total + equity_total
        
        # Verify balance sheet equation
        is_balanced = assets_total == total_liabilities_equity
        
        return jsonify({
            'report_type': 'Balance Sheet',
            'as_of_date': as_of_date.isoformat(),
            'company_name': 'Your Company Name',
            
            # ASSETS
            'assets': [{
                'account_code': acc.account_code,
                'account_name': acc.account_name,
                'account_category': acc.account_category,
                'balance': float(acc.balance)
            } for acc in assets if acc.balance > 0],
            'total_assets': float(assets_total),
            
            # LIABILITIES
            'liabilities': [{
                'account_code': acc.account_code,
                'account_name': acc.account_name,
                'account_category': acc.account_category,
                'balance': float(acc.balance)
            } for acc in liabilities if acc.balance > 0],
            'total_liabilities': float(liabilities_total),
            
            # EQUITY
            'equity': [{
                'account_code': acc.account_code,
                'account_name': acc.account_name,
                'account_category': acc.account_category,
                'balance': float(acc.balance)
            } for acc in equity if acc.balance > 0],
            'total_equity': float(equity_total),
            
            # TOTALS
            'total_liabilities_and_equity': float(total_liabilities_equity),
            'is_balanced': is_balanced,
            'difference': float(abs(assets_total - total_liabilities_equity)) if not is_balanced else 0.00
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= INCOME STATEMENT =======================
@reports_bp.route('/income-statement', methods=['GET'])
@login_required
def income_statement():
    """Generate Income Statement Report - shows Revenue, Expenses, and Net Income for a period"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date parameters required (YYYY-MM-DD)'}), 400
        
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get revenue and expense accounts
        revenues = Account.query.filter_by(account_type='Revenue', is_active=True).all()
        expenses = Account.query.filter_by(account_type='Expense', is_active=True).all()
        
        # Calculate totals
        revenue_total = sum(Decimal(str(acc.balance)) for acc in revenues)
        expense_total = sum(Decimal(str(acc.balance)) for acc in expenses)
        gross_profit = revenue_total - expense_total  # Simplified - actual would deduct COGS
        net_income = revenue_total - expense_total
        
        # Group expenses by category
        expense_categories = {}
        for expense in expenses:
            category = expense.account_category or 'Other Expenses'
            if category not in expense_categories:
                expense_categories[category] = {
                    'accounts': [],
                    'subtotal': Decimal('0.00')
                }
            expense_categories[category]['accounts'].append({
                'account_code': expense.account_code,
                'account_name': expense.account_name,
                'amount': float(expense.balance)
            })
            expense_categories[category]['subtotal'] += Decimal(str(expense.balance))
        
        # Group revenues by category
        revenue_categories = {}
        for revenue in revenues:
            category = revenue.account_category or 'Other Revenue'
            if category not in revenue_categories:
                revenue_categories[category] = {
                    'accounts': [],
                    'subtotal': Decimal('0.00')
                }
            revenue_categories[category]['accounts'].append({
                'account_code': revenue.account_code,
                'account_name': revenue.account_name,
                'amount': float(revenue.balance)
            })
            revenue_categories[category]['subtotal'] += Decimal(str(revenue.balance))
        
        return jsonify({
            'report_type': 'Income Statement',
            'period_from': start_date.isoformat(),
            'period_to': end_date.isoformat(),
            'company_name': 'Your Company Name',
            
            # REVENUE
            'revenue_sections': [{
                'category': category,
                'accounts': data['accounts'],
                'subtotal': float(data['subtotal'])
            } for category, data in revenue_categories.items()],
            'total_revenue': float(revenue_total),
            
            # EXPENSES
            'expense_sections': [{
                'category': category,
                'accounts': data['accounts'],
                'subtotal': float(data['subtotal'])
            } for category, data in expense_categories.items()],
            'total_expenses': float(expense_total),
            
            # NET INCOME
            'gross_profit': float(gross_profit),
            'net_income': float(net_income),
            'net_income_percentage': float((net_income / revenue_total * 100) if revenue_total > 0 else 0)
        }), 200
    
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= GENERAL LEDGER =======================
@reports_bp.route('/general-ledger/<int:account_id>', methods=['GET'])
@login_required
def general_ledger(account_id):
    """Generate General Ledger Report for a specific account"""
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
        
        paginated = query.order_by(Ledger.entry_date.asc(), Ledger.id.asc()).paginate(page=page, per_page=per_page)
        
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
            'report_type': 'General Ledger',
            'account_code': account.account_code,
            'account_name': account.account_name,
            'account_type': account.account_type,
            'opening_balance': 0.00,  # Calculate from first entry
            'entries': ledger_entries,
            'closing_balance': float(account.balance),
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= CASH FLOW STATEMENT =======================
@reports_bp.route('/cash-flow-statement', methods=['GET'])
@login_required
def cash_flow_statement():
    """Generate Cash Flow Statement Report"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date parameters required (YYYY-MM-DD)'}), 400
        
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Operating Activities - from revenues and operating expenses
        revenues = Account.query.filter_by(account_type='Revenue', is_active=True).all()
        expenses = Account.query.filter_by(account_type='Expense', is_active=True).all()
        
        operating_cash = sum(Decimal(str(r.balance)) for r in revenues) - sum(Decimal(str(e.balance)) for e in expenses)
        
        # Investing Activities - changes in fixed assets
        fixed_assets = Account.query.filter(
            Account.account_type == 'Asset',
            Account.account_category == 'Fixed Asset',
            Account.is_active == True
        ).all()
        investing_cash = -sum(Decimal(str(a.balance)) for a in fixed_assets)
        
        # Financing Activities - equity and liability changes
        liabilities = Account.query.filter_by(account_type='Liability', is_active=True).all()
        equity = Account.query.filter_by(account_type='Equity', is_active=True).all()
        
        financing_cash = sum(Decimal(str(l.balance)) for l in liabilities) + sum(Decimal(str(e.balance)) for e in equity)
        
        # Net change in cash
        net_change = operating_cash + investing_cash + financing_cash
        
        return jsonify({
            'report_type': 'Cash Flow Statement',
            'period_from': start_date.isoformat(),
            'period_to': end_date.isoformat(),
            'company_name': 'Your Company Name',
            
            'operating_activities': {
                'revenues': float(sum(Decimal(str(r.balance)) for r in revenues)),
                'expenses': float(sum(Decimal(str(e.balance)) for e in expenses)),
                'net_operating_cash_flow': float(operating_cash)
            },
            
            'investing_activities': {
                'fixed_assets': float(investing_cash),
                'net_investing_cash_flow': float(investing_cash)
            },
            
            'financing_activities': {
                'liabilities': float(sum(Decimal(str(l.balance)) for l in liabilities)),
                'equity': float(sum(Decimal(str(e.balance)) for e in equity)),
                'net_financing_cash_flow': float(financing_cash)
            },
            
            'net_change_in_cash': float(net_change)
        }), 200
    
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= ACCOUNT RECONCILIATION =======================
@reports_bp.route('/account-reconciliation/<int:account_id>', methods=['GET'])
@login_required
def account_reconciliation(account_id):
    """Generate Account Reconciliation Report"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        account = Account.query.get_or_404(account_id)
        
        query = JournalEntry.query.filter_by(account_id=account_id)
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(JournalEntry.entry_date >= start_date)
        
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(JournalEntry.entry_date <= end_date)
        
        entries = query.order_by(JournalEntry.entry_date.asc()).all()
        
        reconciliation = []
        running_balance = Decimal('0.00')
        
        for entry in entries:
            debit = Decimal(str(entry.debit))
            credit = Decimal(str(entry.credit))
            running_balance = running_balance + debit - credit
            
            reconciliation.append({
                'entry_number': entry.entry_number,
                'entry_date': entry.entry_date.isoformat(),
                'description': entry.description,
                'debit': float(debit),
                'credit': float(credit),
                'running_balance': float(running_balance),
                'reference': entry.reference
            })
        
        return jsonify({
            'report_type': 'Account Reconciliation',
            'account_code': account.account_code,
            'account_name': account.account_name,
            'account_type': account.account_type,
            'entries': reconciliation,
            'final_balance': float(running_balance),
            'system_balance': float(account.balance),
            'variance': float(abs(running_balance - Decimal(str(account.balance))))
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= TAX SUMMARY REPORT =======================
@reports_bp.route('/tax-summary', methods=['GET'])
@login_required
def tax_summary():
    """Generate Tax Summary Report including Withholding Taxes"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        tax_type = request.args.get('tax_type')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date parameters required (YYYY-MM-DD)'}), 400
        
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        query = WithholdingTax.query.filter(
            WithholdingTax.transaction_date >= start_date,
            WithholdingTax.transaction_date <= end_date
        )
        
        if tax_type:
            query = query.filter_by(tax_type=tax_type)
        
        records = query.all()
        
        # Group by tax type
        tax_breakdown = {}
        for record in records:
            if record.tax_type not in tax_breakdown:
                tax_breakdown[record.tax_type] = {
                    'count': 0,
                    'total_gross': Decimal('0.00'),
                    'total_tax': Decimal('0.00'),
                    'total_net': Decimal('0.00'),
                    'payees': set()
                }
            
            tax_breakdown[record.tax_type]['count'] += 1
            tax_breakdown[record.tax_type]['total_gross'] += Decimal(str(record.gross_amount))
            tax_breakdown[record.tax_type]['total_tax'] += Decimal(str(record.withholding_tax_amount))
            tax_breakdown[record.tax_type]['total_net'] += Decimal(str(record.net_amount))
            tax_breakdown[record.tax_type]['payees'].add(record.payee_tin)
        
        return jsonify({
            'report_type': 'Tax Summary Report',
            'period_from': start_date.isoformat(),
            'period_to': end_date.isoformat(),
            'tax_breakdown': [{
                'tax_type': tax_type,
                'count': data['count'],
                'total_gross_amount': float(data['total_gross']),
                'total_tax_withheld': float(data['total_tax']),
                'total_net_amount': float(data['total_net']),
                'number_of_payees': len(data['payees'])
            } for tax_type, data in tax_breakdown.items()],
            'total_records': len(records),
            'total_gross': float(sum(r.gross_amount for r in records)),
            'total_tax_withheld': float(sum(r.withholding_tax_amount for r in records)),
            'total_net': float(sum(r.net_amount for r in records))
        }), 200
    
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ======================= FINANCIAL RATIOS =======================
@reports_bp.route('/financial-ratios', methods=['GET'])
@login_required
def financial_ratios():
    """Generate Financial Ratios Report"""
    try:
        as_of_date = request.args.get('as_of_date')
        if as_of_date:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        else:
            as_of_date = datetime.today().date()
        
        # Get all accounts
        current_assets = Account.query.filter(
            Account.account_type == 'Asset',
            Account.account_category == 'Current Asset',
            Account.is_active == True
        ).all()
        
        current_liabilities = Account.query.filter(
            Account.account_type == 'Liability',
            Account.account_category == 'Current Liability',
            Account.is_active == True
        ).all()
        
        assets = Account.query.filter_by(account_type='Asset', is_active=True).all()
        liabilities = Account.query.filter_by(account_type='Liability', is_active=True).all()
        equity = Account.query.filter_by(account_type='Equity', is_active=True).all()
        revenues = Account.query.filter_by(account_type='Revenue', is_active=True).all()
        expenses = Account.query.filter_by(account_type='Expense', is_active=True).all()
        
        # Calculate totals
        total_current_assets = sum(Decimal(str(a.balance)) for a in current_assets)
        total_current_liabilities = sum(Decimal(str(l.balance)) for l in current_liabilities)
        total_assets = sum(Decimal(str(a.balance)) for a in assets)
        total_liabilities = sum(Decimal(str(l.balance)) for l in liabilities)
        total_equity = sum(Decimal(str(e.balance)) for e in equity)
        total_revenue = sum(Decimal(str(r.balance)) for r in revenues)
        total_expenses = sum(Decimal(str(e.balance)) for e in expenses)
        net_income = total_revenue - total_expenses
        
        # Calculate ratios
        current_ratio = float(total_current_assets / total_current_liabilities) if total_current_liabilities > 0 else 0
        debt_to_equity = float(total_liabilities / total_equity) if total_equity > 0 else 0
        roa = float((net_income / total_assets) * 100) if total_assets > 0 else 0
        roe = float((net_income / total_equity) * 100) if total_equity > 0 else 0
        profit_margin = float((net_income / total_revenue) * 100) if total_revenue > 0 else 0
        
        return jsonify({
            'report_type': 'Financial Ratios',
            'as_of_date': as_of_date.isoformat(),
            'company_name': 'Your Company Name',
            
            'liquidity_ratios': {
                'current_ratio': round(current_ratio, 2),
                'current_ratio_interpretation': 'Healthy' if 1.5 <= current_ratio <= 3 else 'Review Required'
            },
            
            'leverage_ratios': {
                'debt_to_equity': round(debt_to_equity, 2),
                'debt_to_equity_interpretation': 'Moderate' if debt_to_equity <= 2 else 'High Leverage'
            },
            
            'profitability_ratios': {
                'return_on_assets': round(roa, 2),
                'return_on_equity': round(roe, 2),
                'net_profit_margin': round(profit_margin, 2)
            },
            
            'financial_position': {
                'total_assets': float(total_assets),
                'total_liabilities': float(total_liabilities),
                'total_equity': float(total_equity),
                'net_income': float(net_income)
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
