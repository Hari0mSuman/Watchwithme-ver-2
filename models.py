from datetime import datetime
import random
import string
from app import db

from flask_login import UserMixin
from sqlalchemy import UniqueConstraint


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime,
                           default=datetime.now,
                           onupdate=datetime.now)

    # Relationships
    hosted_rooms = db.relationship('Room', backref='host', lazy=True, foreign_keys='Room.host_id')
    room_memberships = db.relationship('RoomMember', backref='user', lazy=True)
    chat_messages = db.relationship('ChatMessage', backref='user', lazy=True)

    @property
    def display_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.username
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)





class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(6), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(128), nullable=True)  # hashed password
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Video state
    current_video_url = db.Column(db.String(500), nullable=True)
    current_video_type = db.Column(db.String(20), nullable=True)  # 'youtube' or 'local'
    current_video_time = db.Column(db.Float, default=0.0)
    is_playing = db.Column(db.Boolean, default=False)
    last_sync_time = db.Column(db.DateTime, default=datetime.now)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    members = db.relationship('RoomMember', backref='room', lazy=True, cascade='all, delete-orphan')
    chat_messages = db.relationship('ChatMessage', backref='room', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generate_room_code():
        """Generate a unique 6-character room code"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not Room.query.filter_by(room_code=code).first():
                return code
    
    @property
    def member_count(self):
        return RoomMember.query.filter_by(room_id=self.id, is_approved=True).count()
    
    def get_member(self, user_id):
        return RoomMember.query.filter_by(room_id=self.id, user_id=user_id).first()
    
    def is_member(self, user_id):
        return self.get_member(user_id) is not None
    
    def is_host(self, user_id):
        return self.host_id == user_id


class RoomMember(db.Model):
    __tablename__ = 'room_members'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='guest')  # 'host' or 'guest'
    joined_at = db.Column(db.DateTime, default=datetime.now)
    is_approved = db.Column(db.Boolean, default=False)
    
    __table_args__ = (UniqueConstraint('room_id', 'user_id', name='uq_room_user'),)


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # None for system messages
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='user')  # 'user' or 'system'
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    @property
    def formatted_time(self):
        return self.created_at.strftime('%H:%M')


class VideoFile(db.Model):
    __tablename__ = 'video_files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    uploader = db.relationship('User', backref='uploaded_videos')
    room = db.relationship('Room', backref='video_files')
