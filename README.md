# Small Accounting System

A comprehensive accounting system built with Flask and MySQL, featuring complete double-entry bookkeeping, financial reporting, and user management.

## Features

- **User Management**: Secure authentication with role-based access control
- **Chart of Accounts**: Complete account hierarchy with multiple account types
- **Journal Entries**: Double-entry bookkeeping transaction recording
- **General Ledger**: Complete ledger tracking with running balances
- **Financial Reports**:
  - Trial Balance
  - Balance Sheet
  - Income Statement
  - General Ledger (per account)
- **Account Management**: Create, update, and manage accounts
- **Transaction Tracking**: Full audit trail with user and timestamp tracking

## Installation

### Prerequisites
- Python 3.8+
- MySQL 5.7+
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/vicbarrientis1980-coder/Small-Accounting-System.git
   cd Small-Accounting-System
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env file with your MySQL credentials
   ```

5. **Create database**
   ```bash
   mysql -u root -p
   CREATE DATABASE accounting_system;
   EXIT;
   ```

6. **Initialize database**
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

7. **Run the application**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/profile` - Get user profile

### Accounts
- `POST /api/accounts` - Create new account
- `GET /api/accounts` - List all accounts
- `GET /api/accounts/<id>` - Get account details
- `PUT /api/accounts/<id>` - Update account
- `DELETE /api/accounts/<id>` - Deactivate account

### Transactions
- `POST /api/transactions` - Create journal entry
- `GET /api/transactions` - List journal entries
- `GET /api/transactions/<id>` - Get journal entry details
- `PUT /api/transactions/<id>` - Update journal entry

### Reports
- `GET /api/reports/trial-balance` - Trial Balance Report
- `GET /api/reports/balance-sheet` - Balance Sheet Report
- `GET /api/reports/income-statement` - Income Statement Report
- `GET /api/reports/general-ledger/<account_id>` - General Ledger Report

## Database Schema

### Tables
- **users** - User accounts and authentication
- **accounts** - Chart of Accounts
- **journal_entries** - Transaction entries
- **ledger** - General Ledger with running balances

## Account Types
- **Asset** - Resources owned (Cash, Accounts Receivable, Equipment)
- **Liability** - Obligations (Accounts Payable, Loans)
- **Equity** - Owner's stake (Capital, Retained Earnings)
- **Revenue** - Income sources
- **Expense** - Operating costs

## Example Usage

### Register User
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepassword",
    "full_name": "John Doe"
  }'
```

### Create Account
```bash
curl -X POST http://localhost:5000/api/accounts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "account_code": "1000",
    "account_name": "Cash",
    "account_type": "Asset",
    "account_category": "Current Asset",
    "description": "Cash in hand and bank accounts"
  }'
```

### Create Journal Entry
```bash
curl -X POST http://localhost:5000/api/transactions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "entry_date": "2024-01-15",
    "description": "Initial cash deposit",
    "account_id": 1,
    "debit": 10000.00,
    "credit": 0,
    "reference": "DEP-001"
  }'
```

## Project Structure

```
Small-Accounting-System/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── models/              # Database models
│   ├── __init__.py
│   ├── user.py
│   ├── account.py
│   ├── journal_entry.py
│   └── ledger.py
├── routes/              # API routes
│   ├── __init__.py
│   ├── auth.py
│   ├── accounts.py
│   ├── transactions.py
│   └── reports.py
└── README.md           # This file
```

## Security Considerations

- Use strong secret keys in production
- Enable HTTPS for all API endpoints
- Implement rate limiting
- Validate all input data
- Use environment variables for sensitive data
- Implement comprehensive audit logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions, please open an issue on GitHub.

## Future Enhancements

- [ ] Multi-currency support
- [ ] Tax calculations
- [ ] Invoice generation
- [ ] Advanced reporting
- [ ] Data export (PDF, Excel)
- [ ] Dashboard and visualizations
- [ ] API documentation with Swagger
- [ ] Mobile application
