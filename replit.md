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
- **RAG Interface**: Search-based interaction for enhanced character conversations

### Backend Architecture
- **Modular Component Design**: Five main processing classes (FileProcessor, EnhancedCharacterExtractor, VectorDBManager, Chatbot, DataManager) with clear separation of concerns
- **Multi-format Processing Pipeline**: PyMuPDF for PDF and encoding-aware TXT file processing with progress tracking
- **AI-Powered Analysis**: OpenAI GPT-4o integration for character extraction, chapter analysis, and conversational AI
- **Enhanced Character Extraction Engine**: Automatic chapter detection, detailed character analysis with personality, motivations, and relationships
- **RAG-based Processing**: Chunked processing for large files with vector embeddings for scalable analysis

### Data Management
- **Session-based Storage**: Application data stored in Streamlit session state
- **Vector Database**: OpenAI embeddings with cosine similarity search for semantic content retrieval
- **JSON Data Structures**: Character information, chat histories, and novel metadata stored as JSON objects
- **File-based Persistence**: DataManager handles local storage operations with vector data persistence

### AI Integration Architecture
- **OpenAI API Integration**: GPT-4o model for natural language processing and text-embedding-3-small for vector embeddings
- **Context-aware Conversations**: Character-specific system prompts with personality, background, and search context
- **RAG System**: Vector search for relevant content retrieval to enhance conversation accuracy
- **Multi-modal AI Features**: Character analysis, dialogue generation, story mode narratives, and semantic search
- **Token Management**: Chat history truncation and context optimization for large novel processing

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