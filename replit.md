# 📚 소설 캐릭터 AI 챗봇 시스템

## Overview

This is an AI-powered chatbot system designed for novel character interaction. The application allows users to upload PDF novels, automatically extract and analyze chapters and characters, and engage in conversations with fictional characters from the uploaded novels. The system features a story mode for immersive narrative experiences and maintains chat histories for each character interaction.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Streamlit Framework**: Web-based user interface with sidebar navigation for different features
- **Session State Management**: Persistent storage of application state including current novel, chat histories, and component instances
- **Multi-page Layout**: Five main sections - Novel Upload, Chapter Analysis, Character Management, Character Chat, and Story Mode

### Backend Architecture
- **Modular Component Design**: Four main processing classes (PDFProcessor, CharacterExtractor, Chatbot, DataManager) with clear separation of concerns
- **PDF Processing Pipeline**: PyMuPDF-based text extraction with progress tracking and text cleaning
- **AI-Powered Analysis**: OpenAI GPT-4o integration for character extraction, chapter analysis, and conversational AI
- **Character Extraction Engine**: Automatic chapter detection, character identification, and personality analysis from novel text

### Data Management
- **Session-based Storage**: Application data stored in Streamlit session state
- **JSON Data Structures**: Character information, chat histories, and novel metadata stored as JSON objects
- **File-based Persistence**: DataManager handles local storage operations for novel and character data

### AI Integration Architecture
- **OpenAI API Integration**: GPT-4o model for natural language processing tasks
- **Context-aware Conversations**: Character-specific system prompts with personality and background information
- **Multi-modal AI Features**: Character analysis, dialogue generation, and story mode narratives
- **Token Management**: Chat history truncation to manage API token limits

## External Dependencies

### AI Services
- **OpenAI API**: GPT-4o model for character extraction, analysis, and conversational AI
- **Environment Variables**: OPENAI_API_KEY for API authentication

### Python Libraries
- **Streamlit**: Web application framework and user interface
- **PyMuPDF (fitz)**: PDF text extraction and processing
- **OpenAI Python Client**: Official OpenAI API client library

### Development Tools
- **JSON**: Data serialization and storage format
- **Regular Expressions**: Text processing and pattern matching for chapter detection
- **OS Module**: Environment variable access and file operations