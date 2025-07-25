// Room-specific JavaScript functionality

let youtubePlayer = null;
let localVideo = null;
let lastMessageId = 0;
let syncInterval = null;
let chatPollInterval = null;
let roomCode = '';
let isHost = false;
let currentVideoType = '';
let isSyncing = false;

// Initialize room functionality
function initializeRoom(code, hostStatus, videoType, videoUrl) {
    roomCode = code;
    isHost = hostStatus;
    currentVideoType = videoType;
    
    // Initialize video player based on type
    if (videoType === 'youtube' && videoUrl) {
        initializeYouTubePlayer(videoUrl);
    } else if (videoType === 'local') {
        localVideo = document.getElementById('localVideo');
        if (localVideo) {
            setupLocalVideoEvents();
        }
    }
    
    // Initialize chat
    initializeChat();
    
    // Start polling for updates
    startPolling();
    
    // Set up file upload handler
    setupFileUpload();
    
    console.log('Room initialized:', { roomCode, isHost, currentVideoType });
}

// YouTube Player Integration
function initializeYouTubePlayer(videoUrl) {
    const videoId = extractYouTubeId(videoUrl);
    if (!videoId) return;
    
    if (typeof YT !== 'undefined' && YT.Player) {
        createYouTubePlayer(videoId);
    } else {
        // Wait for YouTube API to load
        window.onYouTubeIframeAPIReady = () => createYouTubePlayer(videoId);
    }
}

function createYouTubePlayer(videoId) {
    youtubePlayer = new YT.Player('youtubePlayer', {
        height: '100%',
        width: '100%',
        videoId: videoId,
        playerVars: {
            controls: isHost ? 1 : 0,
            disablekb: !isHost,
            fs: 0,
            rel: 0,
            showinfo: 0
        },
        events: {
            onReady: onYouTubePlayerReady,
            onStateChange: onYouTubePlayerStateChange
        }
    });
}

function onYouTubePlayerReady(event) {
    console.log('YouTube player ready');
    // Sync with current room state
    syncVideoState();
}

function onYouTubePlayerStateChange(event) {
    if (!isHost || isSyncing) return;
    
    const currentTime = youtubePlayer.getCurrentTime();
    let action = null;
    
    switch (event.data) {
        case YT.PlayerState.PLAYING:
            action = 'play';
            break;
        case YT.PlayerState.PAUSED:
            action = 'pause';
            break;
    }
    
    if (action) {
        sendVideoControl(action, currentTime);
    }
}

// Local Video Integration
function setupLocalVideoEvents() {
    if (!localVideo) return;
    
    // Only hosts can control local video
    if (!isHost) {
        localVideo.removeAttribute('controls');
        return;
    }
    
    localVideo.addEventListener('play', () => {
        if (!isSyncing) {
            sendVideoControl('play', localVideo.currentTime);
        }
    });
    
    localVideo.addEventListener('pause', () => {
        if (!isSyncing) {
            sendVideoControl('pause', localVideo.currentTime);
        }
    });
    
    localVideo.addEventListener('seeked', () => {
        if (!isSyncing) {
            sendVideoControl('seek', localVideo.currentTime);
        }
    });
}

// Video Control Functions
function loadYouTubeVideo() {
    const urlInput = document.getElementById('youtubeUrl');
    const url = urlInput.value.trim();
    
    if (!url) {
        WatchWithMe.showNotification('Please enter a YouTube URL', 'error');
        return;
    }
    
    const videoId = extractYouTubeId(url);
    if (!videoId) {
        WatchWithMe.showNotification('Invalid YouTube URL', 'error');
        return;
    }
    
    fetch(`/room/${roomCode}/video-control`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'load_youtube',
            url: url
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            WatchWithMe.showNotification('YouTube video loaded successfully', 'success');
            urlInput.value = '';
            
            // Reload page to show new video
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            WatchWithMe.showNotification(data.error || 'Failed to load video', 'error');
        }
    })
    .catch(error => {
        console.error('Error loading YouTube video:', error);
        WatchWithMe.showNotification('Failed to load video', 'error');
    });
}

function sendVideoControl(action, time = 0) {
    fetch(`/room/${roomCode}/video-control`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: action,
            time: time
        })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('Video control failed:', data.error);
        }
    })
    .catch(error => {
        console.error('Error sending video control:', error);
    });
}

// Video Synchronization
function syncVideoState() {
    fetch(`/room/${roomCode}/video-sync`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Sync error:', data.error);
                return;
            }
            
            isSyncing = true;
            
            if (youtubePlayer && currentVideoType === 'youtube') {
                syncYouTubePlayer(data);
            } else if (localVideo && currentVideoType === 'local') {
                syncLocalVideo(data);
            }
            
            setTimeout(() => {
                isSyncing = false;
            }, 500);
        })
        .catch(error => {
            console.error('Error syncing video:', error);
        });
}

function syncYouTubePlayer(data) {
    if (!youtubePlayer || typeof youtubePlayer.getPlayerState !== 'function') return;
    
    const currentTime = youtubePlayer.getCurrentTime();
    const targetTime = data.current_time;
    const timeDiff = Math.abs(currentTime - targetTime);
    
    console.log('YouTube sync:', { currentTime, targetTime, timeDiff, isPlaying: data.is_playing });
    
    // Sync time if difference is more than 1 second
    if (timeDiff > 1) {
        console.log('Seeking to:', targetTime);
        youtubePlayer.seekTo(targetTime, true);
    }
    
    // Sync play/pause state
    const playerState = youtubePlayer.getPlayerState();
    if (data.is_playing && (playerState === YT.PlayerState.PAUSED || playerState === YT.PlayerState.CUED)) {
        console.log('Playing video');
        youtubePlayer.playVideo();
    } else if (!data.is_playing && playerState === YT.PlayerState.PLAYING) {
        console.log('Pausing video');
        youtubePlayer.pauseVideo();
    }
}

function syncLocalVideo(data) {
    if (!localVideo) return;
    
    const currentTime = localVideo.currentTime;
    const targetTime = data.current_time;
    const timeDiff = Math.abs(currentTime - targetTime);
    
    // Sync time if difference is more than 1 second
    if (timeDiff > 1) {
        localVideo.currentTime = targetTime;
    }
    
    // Sync play/pause state
    if (data.is_playing && localVideo.paused) {
        localVideo.play().catch(console.error);
    } else if (!data.is_playing && !localVideo.paused) {
        localVideo.pause();
    }
}

// Chat Functions
function initializeChat() {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    
    if (chatForm) {
        chatForm.addEventListener('submit', sendChatMessage);
    }
    
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage(e);
            }
        });
    }
    
    // Get the last message ID for polling
    const lastMessage = document.querySelector('#chatMessages .message:last-child');
    if (lastMessage && lastMessage.dataset.messageId) {
        lastMessageId = parseInt(lastMessage.dataset.messageId);
    }
}

function sendChatMessage(event) {
    event.preventDefault();
    
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();
    
    if (!message) return;
    
    fetch(`/room/${roomCode}/send-message`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        if (data.id) {
            chatInput.value = '';
            addChatMessage(data);
            lastMessageId = data.id;
        } else {
            WatchWithMe.showNotification(data.error || 'Failed to send message', 'error');
        }
    })
    .catch(error => {
        console.error('Error sending message:', error);
        WatchWithMe.showNotification('Failed to send message', 'error');
    });
}

function addChatMessage(messageData) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.dataset.messageId = messageData.id;
    
    if (messageData.type === 'system') {
        messageDiv.innerHTML = `
            <div class="text-center">
                <span class="text-xs text-gray-500 bg-discord-darkest px-2 py-1 rounded">
                    ${messageData.message}
                </span>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="space-y-1">
                <div class="flex items-center space-x-2">
                    <span class="text-sm font-medium text-white">${messageData.user_name}</span>
                    <span class="text-xs text-gray-500">${messageData.time}</span>
                </div>
                <p class="text-discord-text text-sm">${messageData.message}</p>
            </div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function pollChatMessages() {
    fetch(`/room/${roomCode}/messages?after_id=${lastMessageId}`)
        .then(response => response.json())
        .then(messages => {
            messages.forEach(message => {
                addChatMessage(message);
                lastMessageId = Math.max(lastMessageId, message.id);
            });
        })
        .catch(error => {
            console.error('Error polling chat messages:', error);
        });
}

// File Upload
function setupFileUpload() {
    const fileInput = document.getElementById('videoFile');
    if (!fileInput) return;
    
    fileInput.addEventListener('change', handleVideoUpload);
}

function handleVideoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validate file type
    const allowedTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/webm'];
    if (!allowedTypes.includes(file.type)) {
        WatchWithMe.showNotification('Please select a valid video file', 'error');
        return;
    }
    
    // Check file size (max 500MB)
    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
        WatchWithMe.showNotification('File size must be less than 500MB', 'error');
        return;
    }
    
    uploadVideoFile(file);
}

function uploadVideoFile(file) {
    const formData = new FormData();
    formData.append('video', file);
    
    const progressDiv = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('uploadBar');
    
    progressDiv.classList.remove('hidden');
    progressBar.style.width = '0%';
    
    fetch(`/room/${roomCode}/upload-video`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        progressDiv.classList.add('hidden');
        
        if (data.success) {
            WatchWithMe.showNotification('Video uploaded successfully', 'success');
            
            // Reload page to show new video
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            WatchWithMe.showNotification(data.error || 'Upload failed', 'error');
        }
    })
    .catch(error => {
        progressDiv.classList.add('hidden');
        console.error('Upload error:', error);
        WatchWithMe.showNotification('Upload failed', 'error');
    });
    
    // Simulate upload progress (since we can't track real progress with fetch)
    simulateUploadProgress(progressBar);
}

function simulateUploadProgress(progressBar) {
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress >= 95) {
            clearInterval(interval);
            return;
        }
        progressBar.style.width = progress + '%';
    }, 200);
}

// Polling Functions
function startPolling() {
    // Sync video state every 2 seconds for better synchronization
    syncInterval = setInterval(syncVideoState, 2000);
    
    // Poll chat messages every 2 seconds
    chatPollInterval = setInterval(pollChatMessages, 2000);
    
    // Host heartbeat to update video position every 3 seconds
    if (isHost) {
        setInterval(sendHeartbeat, 3000);
    }
}

function sendHeartbeat() {
    if (!isHost) return;
    
    let currentTime = 0;
    if (youtubePlayer && typeof youtubePlayer.getCurrentTime === 'function') {
        currentTime = youtubePlayer.getCurrentTime();
    } else if (localVideo && !localVideo.paused) {
        currentTime = localVideo.currentTime;
    }
    
    if (currentTime > 0) {
        sendVideoControl('heartbeat', currentTime);
    }
}

function stopPolling() {
    if (syncInterval) {
        clearInterval(syncInterval);
        syncInterval = null;
    }
    
    if (chatPollInterval) {
        clearInterval(chatPollInterval);
        chatPollInterval = null;
    }
}

// Utility Functions
function extractYouTubeId(url) {
    const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

// Cleanup when leaving page
window.addEventListener('beforeunload', () => {
    stopPolling();
});

// Handle visibility change to pause/resume polling
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopPolling();
    } else {
        startPolling();
        syncVideoState(); // Immediate sync when returning
    }
});

// Mobile chat toggle
function toggleMobileChat() {
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.classList.toggle('open');
    }
}


// Export functions for global access
window.roomFunctions = {
    loadYouTubeVideo,
    toggleMobileChat,
    syncVideoState
};
