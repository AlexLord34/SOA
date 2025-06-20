import unittest
import uuid
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime
from app import app, db
from app import User  # Импорт модели из app.py

class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Создаем тестового пользователя
        self.user = User(
            id=str(uuid.uuid4()),
            login='testuser',
            email='test@example.com'
        )
        self.user.set_password('TestPassword123')
        db.session.add(self.user)
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_password_hashing(self):
        self.assertTrue(self.user.check_password('TestPassword123'))
        self.assertFalse(self.user.check_password('WrongPassword'))
    
    def test_user_creation(self):
        self.assertEqual(User.query.count(), 1)
        user = User.query.first()
        self.assertEqual(user.login, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertIsNotNone(user.password_hash)
    
    def test_to_dict(self):
        user_data = self.user.to_dict()
        self.assertEqual(user_data['login'], 'testuser')
        self.assertEqual(user_data['email'], 'test@example.com')
        self.assertIsNone(user_data['first_name'])
        self.assertIsNotNone(user_data['created_at'])
    
    def test_timestamps(self):
        self.assertIsNotNone(self.user.created_at)
        self.assertIsNotNone(self.user.updated_at)
        self.assertEqual(self.user.created_at, self.user.updated_at)