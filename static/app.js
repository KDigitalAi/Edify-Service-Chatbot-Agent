// API Configuration
const API_BASE_URL = window.location.origin; // Use same origin as frontend
const API_ENDPOINTS = {
    startSession: '/session/start-anonymous',
    sendMessage: '/chat/message',
    getHistory: '/chat/history',
    health: '/health'
};

// Application State
let sessionId = null;
let isConnected = false;
let messageHistory = [];

// DOM Elements
const chatContainer = document.getElementById('chatContainer');
const messagesDiv = document.getElementById('messages');
const welcomeMessage = document.getElementById('welcomeMessage');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const chatForm = document.getElementById('chatForm');
const clearBtn = document.getElementById('clearBtn');
const historyBtn = document.getElementById('historyBtn');
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const statusDot = document.querySelector('.status-dot');
const historyModal = document.getElementById('historyModal');
const closeHistoryBtn = document.getElementById('closeHistoryBtn');
const historyContent = document.getElementById('historyContent');

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
    await checkHealth();
    await initializeSession();
    setupEventListeners();
    autoResizeTextarea();
});

// Check API Health
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.health}`);
        if (response.ok) {
            updateStatus('connected', 'Connected');
        } else {
            updateStatus('error', 'API Error');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        updateStatus('error', 'Offline');
    }
}

// Initialize Session
async function initializeSession() {
    try {
        updateStatus('connecting', 'Connecting...');
        
        const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.startSession}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        sessionId = data.session_id;
        isConnected = true;
        updateStatus('connected', 'Connected');
        
        console.log('Session initialized:', sessionId);
    } catch (error) {
        console.error('Failed to initialize session:', error);
        updateStatus('error', 'Connection Failed');
        showError('Failed to connect to the server. Please refresh the page.');
    }
}

// Setup Event Listeners
function setupEventListeners() {
    // Send message on form submit
    chatForm.addEventListener('submit', handleSendMessage);
    
    // Send on Enter (but allow Shift+Enter for new line)
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) {
                handleSendMessage(e);
            }
        }
    });

    // Enable/disable send button based on input
    messageInput.addEventListener('input', () => {
        sendBtn.disabled = !messageInput.value.trim() || !isConnected;
    });

    // Clear chat
    clearBtn.addEventListener('click', clearChat);

    // Show history
    historyBtn.addEventListener('click', showHistory);

    // Close history modal
    closeHistoryBtn.addEventListener('click', () => {
        historyModal.classList.remove('show');
    });

    // Close modal on outside click
    historyModal.addEventListener('click', (e) => {
        if (e.target === historyModal) {
            historyModal.classList.remove('show');
        }
    });
}

// Auto-resize textarea
function autoResizeTextarea() {
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
}

// Handle Send Message
async function handleSendMessage(e) {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    if (!message || !isConnected || !sessionId) {
        return;
    }

    // Add user message to UI
    addMessage('user', message);
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.disabled = true;

    // Hide welcome message
    if (welcomeMessage) {
        welcomeMessage.classList.add('hidden');
    }

    // Show loading indicator
    const loadingId = addMessage('assistant', '', true);

    try {
        const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.sendMessage}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Remove loading indicator
        removeMessage(loadingId);
        
        // Add assistant response
        addMessage('assistant', data.response);
        
        // Store in history
        messageHistory.push({
            user: message,
            assistant: data.response,
            timestamp: new Date()
        });

    } catch (error) {
        console.error('Error sending message:', error);
        
        // Remove loading indicator
        removeMessage(loadingId);
        
        // Show error message
        addMessage('assistant', `Sorry, I encountered an error: ${error.message}. Please try again.`);
    } finally {
        sendBtn.disabled = !messageInput.value.trim() || !isConnected;
    }
}

// Add Message to UI
function addMessage(role, content, isLoading = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}${isLoading ? ' loading' : ''}`;
    
    const messageId = `msg-${Date.now()}-${Math.random()}`;
    messageDiv.id = messageId;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'U' : 'AI';

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    if (isLoading) {
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            typingIndicator.appendChild(dot);
        }
        messageContent.appendChild(typingIndicator);
    } else {
        // Format message content (preserve line breaks)
        const formattedContent = formatMessage(content);
        messageContent.innerHTML = formattedContent;

        // Add timestamp
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        messageContent.appendChild(timeDiv);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);
    messagesDiv.appendChild(messageDiv);

    // Scroll to bottom
    scrollToBottom();

    return messageId;
}

// Remove Message from UI
function removeMessage(messageId) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        messageElement.remove();
    }
}

// Format Message Content (preserve formatting)
function formatMessage(content) {
    if (!content) return '';
    
    // Escape HTML to prevent XSS
    const escapeHtml = (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    // Replace newlines with <br>
    let formatted = escapeHtml(content);
    formatted = formatted.replace(/\n/g, '<br>');
    
    // Format numbered lists (basic support)
    formatted = formatted.replace(/^(\d+\.\s.+)$/gm, '<strong>$1</strong>');
    
    return formatted;
}

// Clear Chat
function clearChat() {
    if (confirm('Are you sure you want to clear the chat? This will only clear the display, not the history.')) {
        messagesDiv.innerHTML = '';
        messageHistory = [];
        
        // Show welcome message again
        if (welcomeMessage) {
            welcomeMessage.classList.remove('hidden');
        }
    }
}

// Show History
async function showHistory() {
    if (!sessionId) {
        alert('No active session. Please refresh the page.');
        return;
    }

    historyModal.classList.add('show');
    historyContent.innerHTML = '<p class="loading-text">Loading history...</p>';

    try {
        const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.getHistory}/${sessionId}?limit=50`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.history && data.history.length > 0) {
            historyContent.innerHTML = '';
            
            // Reverse to show newest first
            const reversedHistory = [...data.history].reverse();
            
            reversedHistory.forEach(item => {
                const historyItem = document.createElement('div');
                historyItem.className = 'history-item';
                
                const header = document.createElement('div');
                header.className = 'history-item-header';
                header.innerHTML = `
                    <span>${new Date(item.created_at).toLocaleString()}</span>
                    ${item.source_type ? `<span>Source: ${item.source_type}</span>` : ''}
                `;
                
                const userMsg = document.createElement('div');
                userMsg.className = 'history-item-message';
                userMsg.innerHTML = `<strong>You:</strong> ${escapeHtml(item.user_message)}`;
                
                const assistantMsg = document.createElement('div');
                assistantMsg.className = 'history-item-response';
                assistantMsg.innerHTML = `<strong>Assistant:</strong> ${escapeHtml(item.assistant_response)}`;
                
                historyItem.appendChild(header);
                historyItem.appendChild(userMsg);
                historyItem.appendChild(assistantMsg);
                historyContent.appendChild(historyItem);
            });
        } else {
            historyContent.innerHTML = '<p class="loading-text">No chat history found.</p>';
        }
    } catch (error) {
        console.error('Error loading history:', error);
        historyContent.innerHTML = `
            <div class="error-message">
                Failed to load chat history: ${error.message}
            </div>
        `;
    }
}

// Update Status Indicator
function updateStatus(status, text) {
    statusText.textContent = text;
    statusDot.className = 'status-dot';
    
    switch (status) {
        case 'connected':
            statusDot.classList.add('connected');
            isConnected = true;
            break;
        case 'error':
            statusDot.classList.add('error');
            isConnected = false;
            break;
        case 'connecting':
            isConnected = false;
            break;
    }
}

// Scroll to Bottom
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Show Error Message
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    messagesDiv.appendChild(errorDiv);
    scrollToBottom();
}

// Escape HTML helper
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

