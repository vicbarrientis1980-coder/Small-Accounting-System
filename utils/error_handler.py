import logging
from functools import wraps
from flask import request, jsonify
from app import db
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/accounting_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AuditLog:
    """Model for audit trail logging"""
    pass  # Will be created as a separate model

class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message, field=None, code=None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(self.message)

class InputValidator:
    """Comprehensive input validation class"""
    
    @staticmethod
    def validate_string(value, field_name, min_length=1, max_length=255, required=True):
        """Validate string input"""
        if value is None or value == '':
            if required:
                raise ValidationError(f'{field_name} is required', field_name, 'REQUIRED_FIELD')
            return None
        
        if not isinstance(value, str):
            raise ValidationError(f'{field_name} must be a string', field_name, 'INVALID_TYPE')
        
        value = value.strip()
        
        if len(value) < min_length:
            raise ValidationError(f'{field_name} must be at least {min_length} characters', field_name, 'MIN_LENGTH')
        
        if len(value) > max_length:
            raise ValidationError(f'{field_name} must not exceed {max_length} characters', field_name, 'MAX_LENGTH')
        
        return value
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email or not isinstance(email, str):
            raise ValidationError('Invalid email format', 'email', 'INVALID_EMAIL')
        
        email = email.strip().lower()
        
        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[1]:
            raise ValidationError('Invalid email format', 'email', 'INVALID_EMAIL_FORMAT')
        
        if len(email) > 120:
            raise ValidationError('Email too long', 'email', 'EMAIL_TOO_LONG')
        
        return email
    
    @staticmethod
    def validate_decimal(value, field_name, min_value=0, max_value=None, required=True):
        """Validate decimal/numeric input"""
        if value is None or value == '':
            if required:
                raise ValidationError(f'{field_name} is required', field_name, 'REQUIRED_FIELD')
            return None
        
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError(f'{field_name} must be a valid number', field_name, 'INVALID_NUMBER')
        
        if decimal_value < Decimal(str(min_value)):
            raise ValidationError(f'{field_name} must be at least {min_value}', field_name, 'MIN_VALUE')
        
        if max_value is not None and decimal_value > Decimal(str(max_value)):
            raise ValidationError(f'{field_name} must not exceed {max_value}', field_name, 'MAX_VALUE')
        
        return decimal_value
    
    @staticmethod
    def validate_date(date_string, field_name, required=True):
        """Validate date input"""
        if not date_string:
            if required:
                raise ValidationError(f'{field_name} is required', field_name, 'REQUIRED_FIELD')
            return None
        
        try:
            date_obj = datetime.strptime(date_string, '%Y-%m-%d').date()
            return date_obj
        except (ValueError, TypeError):
            raise ValidationError(f'{field_name} must be in YYYY-MM-DD format', field_name, 'INVALID_DATE_FORMAT')
    
    @staticmethod
    def validate_tin(tin):
        """Validate Tax Identification Number (TIN)"""
        if not tin:
            return None
        
        if not isinstance(tin, str):
            raise ValidationError('TIN must be a string', 'tin', 'INVALID_TIN_FORMAT')
        
        tin = tin.strip().replace('-', '')
        
        # Philippine TIN format: 9-12 digits
        if not tin.isdigit() or len(tin) < 9 or len(tin) > 12:
            raise ValidationError('TIN must be 9-12 digits', 'tin', 'INVALID_TIN_FORMAT')
        
        return tin
    
    @staticmethod
    def validate_account_code(code):
        """Validate account code format"""
        code = InputValidator.validate_string(code, 'Account Code', min_length=1, max_length=20)
        
        # Account code should be alphanumeric
        if not code.replace('-', '').replace('_', '').isalnum():
            raise ValidationError('Account Code must be alphanumeric', 'account_code', 'INVALID_FORMAT')
        
        return code
    
    @staticmethod
    def validate_phone(phone):
        """Validate phone number"""
        if not phone:
            return None
        
        phone = str(phone).strip()
        
        # Remove common phone formatting characters
        phone_digits = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        if len(phone_digits) < 7 or len(phone_digits) > 20:
            raise ValidationError('Phone number must be between 7 and 20 digits', 'phone', 'INVALID_PHONE')
        
        return phone

class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle_validation_error(error):
        """Handle validation errors"""
        logger.warning(f'Validation Error: {error.message} (Field: {error.field}, Code: {error.code})')
        return jsonify({
            'error': error.message,
            'field': error.field,
            'code': error.code,
            'timestamp': datetime.utcnow().isoformat()
        }), 400
    
    @staticmethod
    def handle_database_error(error):
        """Handle database errors"""
        logger.error(f'Database Error: {str(error)}')
        return jsonify({
            'error': 'Database error occurred. Please try again.',
            'code': 'DATABASE_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500
    
    @staticmethod
    def handle_unauthorized(message='Unauthorized access'):
        """Handle unauthorized access"""
        logger.warning(f'Unauthorized Access: {message}')
        return jsonify({
            'error': message,
            'code': 'UNAUTHORIZED',
            'timestamp': datetime.utcnow().isoformat()
        }), 401
    
    @staticmethod
    def handle_forbidden(message='Access forbidden'):
        """Handle forbidden access"""
        logger.warning(f'Forbidden Access: {message}')
        return jsonify({
            'error': message,
            'code': 'FORBIDDEN',
            'timestamp': datetime.utcnow().isoformat()
        }), 403
    
    @staticmethod
    def handle_not_found(resource_type='Resource'):
        """Handle resource not found"""
        logger.info(f'{resource_type} not found')
        return jsonify({
            'error': f'{resource_type} not found',
            'code': 'NOT_FOUND',
            'timestamp': datetime.utcnow().isoformat()
        }), 404
    
    @staticmethod
    def handle_conflict(message='Resource conflict'):
        """Handle resource conflict"""
        logger.warning(f'Conflict: {message}')
        return jsonify({
            'error': message,
            'code': 'CONFLICT',
            'timestamp': datetime.utcnow().isoformat()
        }), 409
    
    @staticmethod
    def handle_generic_error(error, status_code=500):
        """Handle generic errors"""
        logger.error(f'Unexpected Error: {str(error)}')
        return jsonify({
            'error': 'An unexpected error occurred',
            'code': 'INTERNAL_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), status_code

def log_action(action_type, resource_type, resource_id=None, details=None, user_id=None):
    """Log user actions for audit trail"""
    try:
        from models.audit_log import AuditLog as AuditLogModel
        
        audit_entry = AuditLogModel(
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            user_id=user_id,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request else None,
            timestamp=datetime.utcnow()
        )
        db.session.add(audit_entry)
        db.session.commit()
        
        logger.info(f'Action logged: {action_type} on {resource_type} (ID: {resource_id}) by User {user_id}')
    except Exception as e:
        logger.error(f'Failed to log action: {str(e)}')

def require_validation(f):
    """Decorator to validate request data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if request.method in ['POST', 'PUT', 'PATCH']:
                if not request.is_json:
                    return ErrorHandler.handle_validation_error(
                        ValidationError('Request must be JSON', 'content-type', 'INVALID_CONTENT_TYPE')
                    )
            return f(*args, **kwargs)
        except ValidationError as e:
            return ErrorHandler.handle_validation_error(e)
        except Exception as e:
            return ErrorHandler.handle_generic_error(e)
    return decorated_function

def audit_log_action(action_type, resource_type):
    """Decorator to automatically log actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            try:
                result = f(*args, **kwargs)
                
                # Log successful action
                resource_id = kwargs.get('id') or kwargs.get('account_id') or kwargs.get('entry_id')
                log_action(
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    user_id=current_user.id if current_user else None
                )
                
                return result
            except Exception as e:
                # Log failed action
                resource_id = kwargs.get('id') or kwargs.get('account_id') or kwargs.get('entry_id')
                log_action(
                    action_type=f'{action_type}_FAILED',
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=str(e),
                    user_id=current_user.id if current_user else None
                )
                raise
        return decorated_function
    return decorator
