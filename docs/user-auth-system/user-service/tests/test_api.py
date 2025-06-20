import unittest
import jwt
import time
from datetime import datetime, timedelta
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import current_app
from app import app, db, User

class APITestCase(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
            
            # Создаем тестового пользователя
            self.user = User(
                login='testuser',
                email='test@example.com',
                first_name='Test',
                last_name='User'
            )
            self.user.set_password('TestPassword123')
            db.session.add(self.user)
            db.session.commit()
            
            # Генерируем тестовый токен
            self.token = jwt.encode({
                'sub': self.user.id,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm='HS256')
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_health_check(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'ok')
        self.assertEqual(response.json['database'], 'connected')
    
    def test_user_registration(self):
        response = self.app.post('/api/v1/register', json={
            'login': 'newuser',
            'password': 'NewPassword123',
            'email': 'new@example.com'
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn('user_id', response.json)
    
    def test_user_login(self):
        response = self.app.post('/api/v1/login', json={
            'login': 'testuser',
            'password': 'TestPassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.json)
    
    def test_profile_access(self):
        # Без токена
        response = self.app.get('/api/v1/profile')
        self.assertEqual(response.status_code, 401)
        
        # С токеном
        headers = {'Authorization': f'Bearer {self.token}'}
        response = self.app.get('/api/v1/profile', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['login'], 'testuser')
    
    def test_profile_update(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Получаем исходный профиль
        initial_response = self.app.get('/api/v1/profile', headers=headers)
        initial_profile = initial_response.json
        original_updated_at = initial_profile['updated_at']
        
        # Небольшая задержка для SQLite
        time.sleep(0.1)
        
        # Обновляем профиль
        update_response = self.app.put('/api/v1/profile', json={
            'first_name': 'Updated',
            'phone': '+1234567890'
        }, headers=headers)
        
        self.assertEqual(update_response.status_code, 200)
        
        # Получаем обновленный профиль
        updated_response = self.app.get('/api/v1/profile', headers=headers)
        updated_profile = updated_response.json
        
        # Проверяем изменения
        self.assertEqual(updated_profile['first_name'], 'Updated')
        self.assertEqual(updated_profile['phone'], '+1234567890')
        self.assertEqual(updated_profile['last_name'], 'User')  # Не изменяли
        
        # Проверяем обновление временной метки
        self.assertNotEqual(
            original_updated_at, 
            updated_profile['updated_at'],
            "updated_at should change after profile update"
        )
        
        # Дополнительная проверка: created_at не должен меняться
        self.assertEqual(
            initial_profile['created_at'],
            updated_profile['created_at'],
            "created_at should not change"
        )
    
    def test_invalid_login(self):
        response = self.app.post('/api/v1/login', json={
            'login': 'testuser',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 401)
        self.assertIn('Invalid login or password', response.json['error'])
    
    def test_duplicate_registration(self):
        response = self.app.post('/api/v1/register', json={
            'login': 'testuser',  # Существующий логин
            'password': 'Password',
            'email': 'duplicate@example.com'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Login already exists', response.json['error'])