---
title: Mozhii RAG Data Platform
emoji: 🏗️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# 🏗️ Mozhii RAG Data Platform v0.1

## Creating Universal Tamil AI Ecosystem

A web-based data platform for RAG (Retrieval-Augmented Generation) dataset creation, specifically designed for Tamil language content with enterprise-grade workflow management.

---

## 📁 Project Structure

```
mozhii-platform/
├── app/
│   ├── __init__.py              # Flask app initialization
│   ├── config.py                # Configuration settings
│   ├── routes/
│   │   ├── __init__.py          # Routes initialization
│   │   ├── raw_data.py          # Raw data tab API endpoints
│   │   ├── cleaning.py          # Cleaning tab API endpoints
│   │   ├── chunking.py          # Chunking tab API endpoints
│   │   └── admin.py             # Admin approval endpoints
│   ├── services/
│   │   ├── __init__.py          # Services initialization
│   │   ├── huggingface.py       # HuggingFace API integration
│   │   └── storage.py           # Local storage management
│   └── models/
│       ├── __init__.py          # Models initialization
│       └── schemas.py           # Data schemas/models
├── static/
│   ├── css/
│   │   └── styles.css           # Modern UI styles
│   ├── js/
│   │   ├── main.js              # Main JavaScript
│   │   ├── raw-data.js          # Raw data tab logic
│   │   ├── cleaning.js          # Cleaning tab logic
│   │   └── chunking.js          # Chunking tab logic
│   └── assets/
│       └── logo.svg             # Platform logo
├── templates/
│   └── index.html               # Main HTML template
├── data/
│   ├── pending/                 # Files awaiting approval
│   │   ├── raw/                 # Pending raw files
│   │   ├── cleaned/             # Pending cleaned files
│   │   └── chunked/             # Pending chunks
│   └── approved/                # Approved files (synced with HF)
│       ├── raw/
│       ├── cleaned/
│       └── chunked/
├── requirements.txt             # Python dependencies
├── run.py                       # Application entry point
└── README.md                    # This file
```

---

## 🔄 Data Flow Architecture

```
┌─────────────────┐
│   RAW DATA TAB  │ → Collector submits Tamil content
└────────┬────────┘
         ↓
┌─────────────────┐
│  Admin Review   │ → Approve/Reject
└────────┬────────┘
         ↓
┌─────────────────┐
│ HF: mozhii-raw  │ → HuggingFace Repository #1
└────────┬────────┘
         ↓
┌─────────────────┐
│  CLEANING TAB   │ → NLP team cleans content
└────────┬────────┘
         ↓
┌─────────────────┐
│  Admin Review   │ → Approve/Reject
└────────┬────────┘
         ↓
┌─────────────────┐
│ HF: mozhii-clean│ → HuggingFace Repository #2
└────────┬────────┘
         ↓
┌─────────────────┐
│  CHUNKING TAB   │ → QA team creates chunks
└────────┬────────┘
         ↓
┌─────────────────┐
│  Admin Review   │ → Approve/Reject
└────────┬────────┘
         ↓
┌─────────────────┐
│ HF: mozhii-chunk│ → HuggingFace Repository #3 (RAG-READY)
└────────┬────────┘
         ↓
┌─────────────────┐
│Embedding Pipeline│ → External (FAISS/Chroma)
└─────────────────┘
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd mozhii-platform
pip install -r requirements.txt
```

### 2. Configure HuggingFace
Create a `.env` file:
```
HF_TOKEN=your_huggingface_token
HF_RAW_REPO=your-org/mozhii-raw-data
HF_CLEANED_REPO=your-org/mozhii-cleaned-data
HF_CHUNKED_REPO=your-org/mozhii-chunked-data
```

### 3. Run the Application
```bash
python run.py
```

### 4. Open in Browser
Navigate to `http://localhost:5000`

---

## 🔐 Features

- ✅ **Evidence at every stage** - Complete audit trail
- ✅ **Team parallelism** - Multiple users can work simultaneously
- ✅ **Admin approval workflow** - Quality control gate with editing
- ✅ **Edit before approval** - Fix mistakes without rejecting submissions
- ✅ **HuggingFace integration** - Direct push to your HF repositories
- ✅ **Custom HF repos** - Use your own HuggingFace account
- ✅ **Role-based access** - Collector, Cleaner, Chunker, Admin
- ✅ **Tamil language optimized** - RTL support, Tamil fonts

---

## ⚙️ Admin Panel Features

### Edit Functionality
The admin panel now includes powerful editing capabilities:

- **✏️ Edit Button**: Click the edit icon next to any pending item to modify its content
- **Live Preview**: See changes in real-time before saving
- **Character Count**: Track content length while editing
- **Save & Continue**: Save edits without approving
- **Reject with Reason**: Provide feedback when rejecting submissions

### HuggingFace Integration
Push approved data directly to your HuggingFace repositories:

1. **Configure Credentials**: Enter your HF token in the admin panel
2. **Set Repository**: Specify your target repository (e.g., `username/mozhii-data`)
3. **One-Click Push**: Upload all approved data with a single click
4. **Detailed Results**: See upload status for raw, cleaned, and chunked data

**Setup Instructions:**
```bash
# 1. Get your HuggingFace token
# Visit: https://huggingface.co/settings/tokens

# 2. Create dataset repositories
# Visit: https://huggingface.co/new-dataset
# Create: username/mozhii-raw-data
# Create: username/mozhii-cleaned-data
# Create: username/mozhii-chunked-data

# 3. Enter credentials in Admin Panel or .env file
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
HF_RAW_REPO=your-username/mozhii-raw-data
```

### Workflow
```
┌─────────────────────┐
│ User Submits Data   │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Admin Reviews       │
└──────────┬──────────┘
           ↓
    ┌──────┴──────┐
    ↓             ↓
┌─────────┐  ┌─────────┐
│  Edit   │  │ Approve │
└────┬────┘  └────┬────┘
     ↓            ↓
┌─────────┐  ┌─────────┐
│  Save   │  │Push to  │
└────┬────┘  │   HF    │
     ↓       └─────────┘
┌─────────┐
│ Approve │
└─────────┘
```

---

## 👥 Roles

| Role | Access |
|------|--------|
| Collector | RAW DATA tab only |
| Cleaner | CLEANING tab only |
| Chunker | CHUNKING tab only |
| Admin | All tabs + Approval queue |

---

## 📝 License

MIT License - Mozhii AI Team 2026
