import os
import uuid
import re
import jwt
from sqlalchemy import text
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
if os.environ.get('TESTING') == 'true':
    # Используем SQLite в памяти для тестов
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    print("Using in-memory SQLite for tests")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URI', 'postgresql://user:password@db/userdb')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

@app.before_request
def initialize_database():
    if not hasattr(app, 'db_initialized'):
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
            app.db_initialized = True
        except Exception as e:
            app.logger.error(f"Database initialization error: {str(e)}")

@app.route('/health')
def health_check():
    try:
        # Исправленная проверка подключения к БД
        db.session.execute(text('SELECT 1'))
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "database": str(e)}), 500

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'login': self.login,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'phone': self.phone,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@app.route('/api/v1/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Валидация
    if not data.get('login') or not data.get('password') or not data.get('email'):
        return jsonify({'error': 'Missing required fields'}), 400

    email = data['email'].strip().lower()
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    if User.query.filter_by(login=data['login']).first():
        return jsonify({'error': 'Login already exists'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    # Создание пользователя
    new_user = User(
        login=data['login'],
        email=email,
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        phone=data.get('phone')
    )
    
    if data.get('birth_date'):
        try:
            new_user.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid birth date format. Use YYYY-MM-DD'}), 400
    
    new_user.set_password(data['password'])
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully', 'user_id': new_user.id}), 201

@app.route('/api/v1/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(login=data.get('login')).first()
    
    if not user or not user.check_password(data.get('password')):
        return jsonify({'error': 'Invalid login or password'}), 401
    
    # Генерация JWT токена
    token = jwt.encode({
        'sub': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({'access_token': token}), 200

@app.route('/api/v1/profile', methods=['GET'])
def get_profile():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid token'}), 401
    
    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['sub'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user.to_dict()), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/v1/profile', methods=['PUT'])
def update_profile():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid token'}), 401
    
    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['sub'])
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Обновление полей (кроме логина и пароля)
        if 'email' in data:
            try:
                user.email = validate_email(data['email']).email
            except EmailNotValidError:
                return jsonify({'error': 'Invalid email'}), 400
        
        if 'first_name' in data:
            user.first_name = data['first_name']
        
        if 'last_name' in data:
            user.last_name = data['last_name']
        
        if 'birth_date' in data:
            try:
                user.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid birth date format. Use YYYY-MM-DD'}), 400
        
        if 'phone' in data:
            user.phone = data['phone']
        
        db.session.commit()
        
        return jsonify(user.to_dict()), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
# Добавляем только если файл запущен напрямую
if __name__ == '__main__':
    # Создаем таблицы при первом запуске
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating database tables: {str(e)}")
    
    app.run(host='0.0.0.0', port=8000)