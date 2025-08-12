# Real Estate Property Comparison Tool

A comprehensive web application for real estate professionals to analyze MLS reports, generate property comparisons, and create professional PDF reports with market analysis.

## 🏠 Features

### Core Functionality

- **PDF Processing**: Extract property data from MLS report PDFs
- **Property Comparison**: Compare multiple properties side-by-side
- **Data Visualization**: Generate comparative charts and graphs
- **Professional Reports**: Create branded PDF reports with analysis
- **Market Analysis**: Automated appraisal calculations and insights
- **Temporary File System**: Secure, automatic cleanup of uploaded files

### User Interface

- **Modern React Frontend**: Built with React + Vite and Tailwind CSS
- **Drag & Drop Upload**: Easy file upload interface
- **Real-time Processing**: Live status updates during report generation
- **PDF Viewer**: Built-in PDF viewing and download capabilities
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## 🏗️ Architecture

### Frontend (React + Vite)

- **React 18**: Modern React with hooks and functional components
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework for styling
- **TypeScript**: Type-safe JavaScript development
- **API Service Layer**: Clean separation of frontend and backend logic

### Backend (FastAPI + Python)

- **FastAPI**: Modern, fast web framework for building APIs
- **PyPDF2**: PDF text extraction and processing
- **Pandas**: Data manipulation and analysis
- **Matplotlib**: Chart and graph generation
- **ReportLab**: Professional PDF report creation
- **Temporary File System**: Secure file handling with automatic cleanup

## 📋 Prerequisites

Before running this application, ensure you have:

- **Python 3.8+** installed
- **Node.js 16+** and npm installed
- **Git** for version control

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd real_estate_app
```

### 2. Backend Setup

#### Install Python Dependencies

```bash
pip install fastapi uvicorn python-multipart pandas PyPDF2 matplotlib reportlab
```

#### Start the Backend Server

```bash
cd backend
python pdf_handle.py
```

The backend will start on `http://localhost:8000`

### 3. Frontend Setup

#### Install Node.js Dependencies

```bash
cd real_estate_app
npm install
```

#### Start the Development Server

```bash
npm run dev
```

The frontend will start on `http://localhost:5173`

## 📖 Usage

### 1. Upload MLS Report

- Click "Choose File" in the MLS Report section
- Select your main property PDF file
- The file will be uploaded and processed

### 2. Upload Comparison Properties

- Click "Choose Files" in the Comparison Properties section
- Select multiple PDF files for comparison
- All files will be uploaded and processed

### 3. Generate Report

- Click "Generate Property Analysis Report"
- The system will:
  - Extract data from all PDFs
  - Generate comparative charts
  - Create professional PDF report
  - Provide market analysis

### 4. View and Download

- View the report directly in the browser
- Download the complete PDF report
- Access charts and analysis data

## 🔧 API Endpoints

### File Upload

- `POST /upload-input-pdf` - Upload main MLS report
- `POST /upload-comparison-pdf` - Upload comparison properties

### Report Generation

- `GET /generate-report` - Generate comparison report
- `GET /download-report/{report_id}` - Download PDF report
- `GET /view-report/{report_id}` - View report in browser

### File Management

- `GET /files` - List uploaded files
- `DELETE /files/{file_id}` - Delete uploaded file

## 📊 Data Extraction

The application extracts the following property information from MLS reports:

### Property Features

- Address
- Status (Active/Closed)
- Subdivision
- Year Built
- Living Square Footage
- Total Square Footage
- Bedrooms
- Bathrooms
- Stories
- Garage Spaces
- Private Pool

### Price Information

- List Price
- List Price per Square Foot
- Sold Price
- Sold Price per Square Foot
- Days on Market

## 📈 Generated Reports

### Report Contents

1. **Property Features Comparison Table**
2. **Price & Market Analysis Table**
3. **List Price vs Sold Price Chart**
4. **Price per Square Foot Comparison Chart**
5. **Appraisal Report with Market Analysis**

### Chart Features

- Comparative bar charts
- Red circle highlighting for input property
- Professional styling and formatting
- Clear data visualization

## 🔒 Security Features

### File Handling

- **Temporary File System**: All uploaded files stored in temporary directory
- **Automatic Cleanup**: Files deleted after report generation
- **Secure Processing**: No persistent storage of sensitive data
- **File Validation**: PDF format validation and size limits

### Data Protection

- **No Data Persistence**: Temporary processing only
- **Secure Uploads**: File type validation
- **Clean Environment**: Automatic cleanup on server shutdown

## 🛠️ Development

### Project Structure

```
real_estate_app/
├── backend/
│   └── pdf_handle.py          # FastAPI backend with PDF processing
├── real_estate_app/
│   ├── src/
│   │   ├── App.tsx           # Main React component
│   │   ├── api.ts            # API service layer
│   │   └── App.css           # Tailwind CSS styles
│   ├── package.json          # Node.js dependencies
│   └── vite.config.js        # Vite configuration
├── reports/                  # Generated PDF reports (persistent)
└── README.md                 # This file
```

### Key Technologies

- **Backend**: FastAPI, PyPDF2, Pandas, Matplotlib, ReportLab
- **Frontend**: React, Vite, Tailwind CSS, TypeScript
- **File Processing**: Temporary file system with automatic cleanup
- **PDF Generation**: Professional reports with charts and analysis

## 🚀 Deployment

### Production Considerations

- **HTTPS**: Required for secure file uploads
- **File Storage**: Consider cloud storage (AWS S3, Azure Blob)
- **Database**: Add user management and report history
- **Scaling**: Load balancing for multiple users
- **Monitoring**: Add logging and error tracking

### Environment Variables

- `API_BASE_URL`: Backend API URL
- `MAX_FILE_SIZE`: Maximum file upload size
- `TEMP_DIR`: Temporary file directory path

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- Create an issue in the repository
- Check the API documentation at `http://localhost:8000/docs`
- Review the FastAPI interactive docs for endpoint testing

## 🔄 Version History

- **v1.0.0**: Initial release with PDF processing and report generation
- **v1.1.0**: Added temporary file system and automatic cleanup
- **v1.2.0**: Enhanced UI with Tailwind CSS and PDF viewer
- **v1.3.0**: Added red circle highlighting and improved charts

---

**Built for Real Estate Professionals** 🏠📊
