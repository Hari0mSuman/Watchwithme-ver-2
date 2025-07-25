import os
import re
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    session, render_template, request, redirect, url_for, 
    flash, jsonify, send_from_directory, abort
)
from flask_login import login_user, logout_user, login_required, current_user

from app import app, db
from models import Room, RoomMember, ChatMessage, VideoFile, User

from dotenv import load_dotenv
load_dotenv()
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_key")


# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True





@app.route('/')
def index():
    """Landing page for logged out users, home page for logged in users"""
    if not current_user.is_authenticated:
        return render_template('index.html', show_landing=True)
    
    # Show user's rooms
    user_rooms = []
    memberships = RoomMember.query.filter_by(user_id=current_user.id, is_approved=True).all()
    for membership in memberships:
        user_rooms.append({
            'room': membership.room,
            'role': membership.role
        })
    
    return render_template('index.html', show_landing=False, user_rooms=user_rooms)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        # Validation
        if not username or not email or not password:
            flash('Username, email, and password are required', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('auth/register.html')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        user = User()
        user.username = username
        user.email = email
        user.first_name = first_name or None
        user.last_name = last_name or None
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user, remember=True)
        flash('Registration successful! Welcome to WatchWithMe!', 'success')
        return redirect(url_for('index'))
    
    return render_template('auth/register.html')


@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


@app.route('/create-room', methods=['GET', 'POST'])
@login_required
def create_room():
    """Create a new room"""
    if request.method == 'POST':
        room_name = request.form.get('room_name', '').strip()
        room_password = request.form.get('room_password', '').strip()
        
        if not room_name:
            flash('Room name is required', 'error')
            return redirect(url_for('index'))
        
        # Generate unique room code
        room_code = Room.generate_room_code()
        
        # Create new room
        room = Room()
        room.room_code = room_code
        room.name = room_name
        room.host_id = current_user.id
        
        if room_password:
            room.password = generate_password_hash(room_password)
        
        db.session.add(room)
        db.session.commit()
        
        # Add host as approved member
        host_member = RoomMember()
        host_member.room_id = room.id
        host_member.user_id = current_user.id
        host_member.role = 'host'
        host_member.is_approved = True
        db.session.add(host_member)
        
        # Add system message
        welcome_msg = ChatMessage()
        welcome_msg.room_id = room.id
        welcome_msg.message = f"Room '{room_name}' created by {current_user.display_name}"
        welcome_msg.message_type = 'system'
        db.session.add(welcome_msg)
        db.session.commit()
        
        flash(f'Room created successfully! Room code: {room_code}', 'success')
        return redirect(url_for('room', room_code=room_code))
    
    return redirect(url_for('index'))


@app.route('/join-room', methods=['POST'])
@login_required
def join_room():
    """Join an existing room"""
    room_code = request.form.get('room_code', '').strip().upper()
    room_password = request.form.get('room_password', '').strip()
    
    if not room_code:
        flash('Room code is required', 'error')
        return redirect(url_for('index'))
    
    room = Room.query.filter_by(room_code=room_code).first()
    if not room:
        flash('Room not found', 'error')
        return redirect(url_for('index'))
    
    # Check if user is already a member
    existing_member = room.get_member(current_user.id)
    if existing_member:
        if existing_member.is_approved:
            return redirect(url_for('room', room_code=room_code))
        else:
            flash('Your request to join this room is pending approval', 'info')
            return redirect(url_for('index'))
    
    # Check password if required
    if room.password:
        if not room_password or not check_password_hash(room.password, room_password):
            flash('Incorrect room password', 'error')
            return redirect(url_for('index'))
    
    # Add user as member
    member = RoomMember()
    member.room_id = room.id
    member.user_id = current_user.id
    member.role = 'guest'
    member.is_approved = True  # Auto-approve if password is correct or no password required
    db.session.add(member)
    
    # Add system message
    join_msg = ChatMessage()
    join_msg.room_id = room.id
    join_msg.message = f"{current_user.display_name} joined the room"
    join_msg.message_type = 'system'
    db.session.add(join_msg)
    db.session.commit()
    
    return redirect(url_for('room', room_code=room_code))


@app.route('/room/<room_code>')
@login_required
def room(room_code):
    """Display room interface"""
    room = Room.query.filter_by(room_code=room_code.upper()).first()
    if not room:
        flash('Room not found', 'error')
        return redirect(url_for('index'))
    
    # Check if user is a member
    member = room.get_member(current_user.id)
    if not member or not member.is_approved:
        flash('You are not authorized to access this room', 'error')
        return redirect(url_for('index'))
    
    # Get room members
    members = RoomMember.query.filter_by(room_id=room.id, is_approved=True).all()
    
    # Get recent chat messages (last 50)
    messages = ChatMessage.query.filter_by(room_id=room.id)\
                                .order_by(ChatMessage.created_at.desc())\
                                .limit(50).all()
    messages.reverse()  # Show oldest first
    
    return render_template('room.html', 
                          room=room, 
                          member=member, 
                          members=members,
                          messages=messages)


@app.route('/room/<room_code>/send-message', methods=['POST'])
@login_required
def send_message(room_code):
    """Send a chat message"""
    room = Room.query.filter_by(room_code=room_code.upper()).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    member = room.get_member(current_user.id)
    if not member or not member.is_approved:
        return jsonify({'error': 'Not authorized'}), 403
    
    data = request.get_json() or {}
    message_text = data.get('message', '').strip()
    if not message_text:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Create message
    message = ChatMessage()
    message.room_id = room.id
    message.user_id = current_user.id
    message.message = message_text
    message.message_type = 'user'
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'id': message.id,
        'user_name': current_user.display_name,
        'message': message.message,
        'time': message.formatted_time,
        'type': message.message_type
    })


@app.route('/room/<room_code>/messages')
@login_required
def get_messages(room_code):
    """Get recent chat messages (for polling)"""
    room = Room.query.filter_by(room_code=room_code.upper()).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    member = room.get_member(current_user.id)
    if not member or not member.is_approved:
        return jsonify({'error': 'Not authorized'}), 403
    
    # Get messages after a certain ID (for polling)
    after_id = request.args.get('after_id', 0, type=int)
    messages = ChatMessage.query.filter_by(room_id=room.id)\
                                .filter(ChatMessage.id > after_id)\
                                .order_by(ChatMessage.created_at.asc())\
                                .all()
    
    return jsonify([{
        'id': msg.id,
        'user_name': msg.user.display_name if msg.user else 'System',
        'message': msg.message,
        'time': msg.formatted_time,
        'type': msg.message_type
    } for msg in messages])


@app.route('/room/<room_code>/video-sync')
@login_required
def get_video_sync(room_code):
    """Get current video state for synchronization"""
    room = Room.query.filter_by(room_code=room_code.upper()).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    member = room.get_member(current_user.id)
    if not member or not member.is_approved:
        return jsonify({'error': 'Not authorized'}), 403
    
    # Calculate current time based on when the video was last synced
    current_time = room.current_video_time
    if room.is_playing and room.last_sync_time:
        elapsed_seconds = (datetime.now() - room.last_sync_time).total_seconds()
        current_time += elapsed_seconds
    
    return jsonify({
        'video_url': room.current_video_url,
        'video_type': room.current_video_type,
        'current_time': current_time,
        'is_playing': room.is_playing,
        'last_sync': room.last_sync_time.isoformat() if room.last_sync_time else None
    })


@app.route('/room/<room_code>/video-control', methods=['POST'])
@login_required
def video_control(room_code):
    """Control video playback (host only)"""
    room = Room.query.filter_by(room_code=room_code.upper()).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    member = room.get_member(current_user.id)
    if not member or not member.is_approved or member.role != 'host':
        return jsonify({'error': 'Only hosts can control video'}), 403
    
    data = request.get_json() or {}
    action = data.get('action')
    
    if action == 'play':
        room.is_playing = True
        room.current_video_time = data.get('time', 0)
        room.last_sync_time = datetime.now()
        
    elif action == 'pause':
        room.is_playing = False
        room.current_video_time = data.get('time', 0)
        room.last_sync_time = datetime.now()
        
    elif action == 'seek':
        room.current_video_time = data.get('time', 0)
        room.last_sync_time = datetime.now()
        
    elif action == 'heartbeat':
        # Host sending current video position to keep time synced
        room.current_video_time = data.get('time', 0)
        room.last_sync_time = datetime.now()
        
    elif action == 'load_youtube':
        youtube_url = data.get('url', '').strip()
        video_id = extract_youtube_id(youtube_url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        room.current_video_url = youtube_url
        room.current_video_type = 'youtube'
        room.current_video_time = 0
        room.is_playing = False
        room.last_sync_time = datetime.now()
        
        # Add system message
        system_msg = ChatMessage()
        system_msg.room_id = room.id
        system_msg.message = f"{current_user.display_name} loaded a YouTube video"
        system_msg.message_type = 'system'
        db.session.add(system_msg)
    
    db.session.commit()
    return jsonify({'success': True})


@app.route('/room/<room_code>/upload-video', methods=['POST'])
@login_required
def upload_video(room_code):
    """Upload a local video file (host only)"""
    room = Room.query.filter_by(room_code=room_code.upper()).first()
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    member = room.get_member(current_user.id)
    if not member or not member.is_approved or member.role != 'host':
        return jsonify({'error': 'Only hosts can upload videos'}), 403
    
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename and allowed_video_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file.save(file_path)
        
        # Save video info to database
        video_file = VideoFile()
        video_file.filename = filename
        video_file.original_filename = file.filename
        video_file.file_path = file_path
        video_file.file_size = os.path.getsize(file_path)
        video_file.uploaded_by = current_user.id
        video_file.room_id = room.id
        db.session.add(video_file)
        
        # Update room video state
        room.current_video_url = url_for('serve_video', filename=filename)
        room.current_video_type = 'local'
        room.current_video_time = 0
        room.is_playing = False
        room.last_sync_time = datetime.now()
        
        # Add system message
        system_msg = ChatMessage()
        system_msg.room_id = room.id
        system_msg.message = f"{current_user.display_name} uploaded video: {file.filename}"
        system_msg.message_type = 'system'
        db.session.add(system_msg)
        db.session.commit()
        
        return jsonify({'success': True, 'video_url': room.current_video_url})
    
    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/uploads/<filename>')
def serve_video(filename):
    """Serve uploaded video files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/room/<room_code>/leave', methods=['POST'])
@login_required
def leave_room(room_code):
    """Leave a room"""
    room = Room.query.filter_by(room_code=room_code.upper()).first()
    if not room:
        flash('Room not found', 'error')
        return redirect(url_for('index'))
    
    member = room.get_member(current_user.id)
    if member:
        # Add system message
        leave_msg = ChatMessage()
        leave_msg.room_id = room.id
        leave_msg.message = f"{current_user.display_name} left the room"
        leave_msg.message_type = 'system'
        db.session.add(leave_msg)
        
        # Remove member
        db.session.delete(member)
        db.session.commit()
    
    flash('You have left the room', 'info')
    return redirect(url_for('index'))


def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    youtube_regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
    match = re.search(youtube_regex, url)
    return match.group(1) if match else None


def allowed_video_file(filename):
    """Check if file extension is allowed for video uploads"""
    allowed_extensions = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


@app.errorhandler(404)
def not_found(error):
    return render_template('403.html', error_message="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('403.html', error_message="Internal server error"), 500
