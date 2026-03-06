from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from app.utils.validators import validate_email, validate_password

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        if not validate_email(data.get('email')):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not validate_password(data.get('password')):
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        user = AuthService.register_user(
            email=data['email'],
            password=data['password'],
            full_name=data['full_name'],
            phone=data['phone'],
            role=data.get('role', 'customer')
        )
        
        return jsonify({
            'message': 'User registered successfully. OTP sent to phone.',
            'user_id': user.id,
            'requires_otp': True
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Registration error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        result = AuthService.login_user(
            email=data['email'],
            password=data['password'],
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        if result.get('requires_2fa'):
            return jsonify({
                'message': 'OTP sent to your phone',
                'user_id': result['user_id'],
                'requires_2fa': True
            }), 200
        
        return jsonify({
            'token': result['token'],
            'user': {
                'id': result['user'].id,
                'email': result['user'].email,
                'full_name': result['user'].full_name,
                'role': result['user'].role
            }
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        AuthService.verify_otp(data['user_id'], data['otp_code'])
        return jsonify({'message': 'Phone verified successfully'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"OTP verification error: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/verify-login-otp', methods=['POST'])
def verify_login_otp():
    try:
        data = request.get_json()
        token, user = AuthService.verify_login_otp(data['user_id'], data['otp_code'])
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role
            }
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Login OTP verification error: {e}")
        return jsonify({'error': str(e)}), 500
