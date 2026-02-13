# SalesBot Frontend - Quick Start Guide

## Overview

A lightweight HTML/CSS/JavaScript frontend to test and demonstrate SalesBot's agentic CRM capabilities.

## Files

- `static/index.html` - Main HTML structure
- `static/styles.css` - Styling and layout
- `static/app.js` - JavaScript for API communication

## How to Run

1. **Start the FastAPI server:**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Open your browser:**
   - Navigate to: `http://localhost:8000`
   - The frontend will automatically load

3. **Test SalesBot:**
   - Type messages in the input field
   - Or click quick command buttons
   - Watch SalesBot respond with agentic actions

## Features

- **Real-time chat interface** - Send messages and get responses
- **Quick commands** - Pre-filled buttons for common operations
- **Status indicator** - Shows connection and processing status
- **Responsive design** - Works on desktop and mobile
- **Typing indicator** - Shows when SalesBot is processing

## Example Commands

- "list all leads"
- "create a lead named John Doe with email john@example.com and phone 555-1234"
- "create a task subject Follow up priority High status Not Started task_type Call"
- "create a campaign named Q1 Email Campaign with status Active type Email campaign_owner Sales Team"

## API Endpoints Used

- `POST /session/start-anonymous` - Creates a new session
- `POST /chat/message` - Sends messages to SalesBot

## Notes

- The frontend automatically creates a session on load
- All messages are persisted in the database
- Agentic actions (create, update, delete) are executed in real-time
- Responses show success/error messages clearly

