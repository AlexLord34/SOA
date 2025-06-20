# User Service

## Зона ответственности
Сервис отвечает за управление пользовательскими данными и аутентификацией в социальной сети. Основные функции:
- Регистрация новых пользователей
- Аутентификация и управление сессиями
- Управление профилями пользователей
- Управление ролями и правами доступа
- Валидация и безопасное хранение учетных данных

## Границы сервиса
### Включает:
- Хранение и управление учетными данными
- Генерация и верификация JWT-токенов
- Управление профилями (имя, аватар, контактные данные)
- Назначение системных ролей (пользователь, модератор, администратор)
- История операций с аккаунтом

### Не включает:
- Управление контентом (посты/комментарии)
- Систему уведомлений
- Аналитику активности
- Социальные связи (друзья/подписки)

## ER-диаграмма базы данных
```mermaid
erDiagram
    users ||--o{ user_roles : "имеет"
    users ||--o{ user_sessions : "создает"
    users {
        uuid id PK "Уникальный идентификатор"
        string username "Логин (уникальный)"
        string email "Email (уникальный)"
        string password_hash "Хеш пароля"
        string full_name "Полное имя"
        string avatar_url "URL аватара"
        datetime created_at "Дата регистрации"
        datetime updated_at "Последнее обновление"
        boolean is_active "Активен ли аккаунт"
        boolean is_verified "Подтвержден ли email"
    }
    
    roles {
        uuid id PK "ID роли"
        string name "Название роли"
        string description "Описание прав"
        int priority "Уровень приоритета"
        boolean is_default "Роль по умолчанию"
        datetime created_at "Дата создания"
    }
    
    user_roles {
        uuid user_id FK "Ссылка на пользователя"
        uuid role_id FK "Ссылка на роль"
        datetime assigned_at "Дата назначения"
        uuid assigned_by "Кто назначил"
    }
    
    user_sessions {
        uuid session_id PK "ID сессии"
        uuid user_id FK "Ссылка на пользователя"
        string device_info "Информация об устройстве"
        string ip_address "IP-адрес входа"
        datetime login_at "Время входа"
        datetime expires_at "Время истечения"
        boolean is_active "Активна ли сессия"
    }
