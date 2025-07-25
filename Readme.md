# WatchWithMe - Real-Time Collaborative Video Watching Platform

## Overview

WatchWithMe is a real-time collaborative video-watching web application built with Flask that allows users to create rooms, share YouTube videos or upload local files, and watch content together with synchronized playback and real-time chat functionality.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web framework with Python
- **Database**: SQLAlchemy ORM with PostgreSQL (configurable via DATABASE_URL environment variable)
- **Authentication**: Replit Auth integration with OAuth2 flow
- **Session Management**: Flask sessions with permanent session configuration
- **File Handling**: Local file upload system with 500MB size limit

### Frontend Architecture
- **Styling**: Tailwind CSS with custom Discord/YouTube-inspired theme
- **JavaScript**: Vanilla JavaScript with modular approach
- **Video Players**: 
  - YouTube API integration for YouTube videos
  - HTML5 video element for local file playback
- **Real-Time Features**: Polling-based synchronization for chat and video state

### Database Schema
- **Users**: Store user profiles with username, email, password hash, and optional names
- **Rooms**: Room management with unique codes and optional passwords
- **RoomMembers**: User-room relationships with role-based access (host/guest)
- **ChatMessages**: Real-time messaging within rooms
- **VideoFiles**: Local video file metadata and storage

## Key Components

### Authentication System  
- **Custom User Authentication**: Traditional username/password authentication with Flask-Login
- **User Registration**: Self-service account creation with email and optional name fields
- **Session Management**: Secure Flask sessions with remember-me functionality
- **Role-Based Access**: Host and guest roles with different permissions in rooms

### Room Management
- **Room Creation**: 6-character unique room codes with optional password protection
- **Member Management**: Host approval system for guest access
- **Role System**: Hosts control video playback, guests can chat and view

### Video Synchronization
- **YouTube Integration**: Embed and sync YouTube videos using YouTube IFrame API
- **Local File Support**: Upload and stream local video files up to 500MB
- **Sync Mechanism**: Polling-based synchronization for play/pause/seek events
- **State Management**: Track video position, play state, and current video source

### Chat System
- **Real-Time Messaging**: Polling-based chat updates
- **System Messages**: Automatic notifications for user joins/leaves
- **Message History**: Persistent chat storage per room

### File Upload System
- **Local Storage**: Files stored in uploads directory
- **Security**: Filename sanitization and file type validation
- **Progress Tracking**: Upload progress indication
- **Streaming**: Direct file serving for video playback

## Data Flow

### User Authentication Flow
1. User registers with username, email, and password
2. Password is hashed and stored securely
3. User logs in with username/password credentials
4. Flask-Login manages session and user state
5. Remember-me functionality for persistent sessions

### Room Creation Flow
1. Authenticated user submits room creation form
2. Generate unique 6-character room code
3. Create room record with user as host
4. Create room membership record
5. Redirect to room page

### Video Synchronization Flow
1. Host initiates video action (play/pause/seek)
2. Action stored in room state
3. All users poll for room state updates
4. Video players sync to current state
5. State changes broadcast to all room members

### Chat Flow
1. User submits chat message
2. Message stored in database with timestamp
3. All users poll for new messages
4. New messages displayed in real-time
5. System messages generated for user events

## External Dependencies

### Frontend Dependencies
- **Tailwind CSS**: Utility-first CSS framework via CDN
- **Font Awesome**: Icon library via CDN
- **YouTube IFrame API**: Video player integration for YouTube content

### Backend Dependencies
- **Flask**: Web framework
- **Flask-SQLAlchemy**: Database ORM
- **Flask-Login**: User session management
- **Flask-Dance**: OAuth integration
- **Werkzeug**: WSGI utilities and security helpers
- **PyJWT**: JWT token handling

### Authentication Service
- **Replit Auth**: OAuth2 provider for user authentication
- **OAuth2 Flow**: Standard authorization code flow implementation

## Deployment Strategy

### Environment Configuration
- **DATABASE_URL**: PostgreSQL connection string
- **SESSION_SECRET**: Flask session encryption key
- **OAuth Credentials**: Replit Auth client configuration

### File Storage
- **Local Storage**: Upload directory for video files
- **Static Assets**: CSS, JavaScript, and image files served directly
- **Database Storage**: User data, room state, and chat messages

### Scalability Considerations
- **Polling-Based Updates**: Simple but may need WebSocket upgrade for higher concurrency
- **File Storage**: Local storage limits scalability, could migrate to cloud storage
- **Database Connection Pooling**: Configured for connection reuse and health checks

### Security Measures
- **Password Hashing**: Werkzeug security for room passwords
- **File Upload Validation**: Filename sanitization and size limits
- **Session Security**: Secure session management with proper secret key
- **CSRF Protection**: Form-based CSRF protection through Flask sessions