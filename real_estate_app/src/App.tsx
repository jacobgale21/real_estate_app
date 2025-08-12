import { useState } from "react";
import { apiService } from "./api";
import type { GenerateReportResponse } from "./api";

interface UploadedFile {
  name: string;
  size: number;
  type: string;
  file_id?: string;
}

function App() {
  const [mlsReport, setMlsReport] = useState<UploadedFile | null>(null);
  const [comparisonFiles, setComparisonFiles] = useState<UploadedFile[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [reportData, setReportData] = useState<GenerateReportResponse | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showPdfViewer, setShowPdfViewer] = useState(false);

  const handleMlsReportUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.type !== "application/pdf") {
      setError("Please select a valid PDF file for the MLS report.");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await apiService.uploadInputPdf(file);

      if (response.success) {
        setMlsReport({
          name: file.name,
          size: file.size,
          type: file.type,
          file_id: response.file_id,
        });
        setSuccess("MLS report uploaded successfully!");
      } else {
        setError(response.message || "Upload failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const handleComparisonFilesUpload = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const files = Array.from(event.target.files || []);
    const pdfFiles = files.filter((file) => file.type === "application/pdf");

    if (pdfFiles.length === 0) {
      setError("Please select at least one PDF file for comparison.");
      return;
    }

    if (pdfFiles.length !== files.length) {
      setError("Some files were not PDFs and have been filtered out.");
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await apiService.uploadComparisonPdfs(pdfFiles);

      if (response.success && response.uploaded_files) {
        const uploadedFiles = response.uploaded_files.map((apiFile, index) => ({
          name: pdfFiles[index].name,
          size: pdfFiles[index].size,
          type: pdfFiles[index].type,
          file_id: apiFile.file_id,
        }));

        setComparisonFiles(uploadedFiles);
        setSuccess(
          `${uploadedFiles.length} comparison file(s) uploaded successfully!`
        );
      } else {
        setError(response.message || "Upload failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const removeComparisonFile = (index: number) => {
    setComparisonFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleGenerateReport = async () => {
    if (!mlsReport || !mlsReport.file_id) {
      setError("Please upload an MLS report first.");
      return;
    }
    if (comparisonFiles.length === 0) {
      setError("Please upload at least one comparison property file.");
      return;
    }

    const comparisonFileIds = comparisonFiles
      .map((file) => file.file_id)
      .filter((id): id is string => id !== undefined);

    if (comparisonFileIds.length === 0) {
      setError("No valid comparison files found.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await apiService.generateReport(
        mlsReport.file_id,
        comparisonFileIds
      );

      if (response.success) {
        setReportData(response);
        setSuccess(
          "Report generated successfully! You can now download the PDF."
        );
      } else {
        setError(response.message || "Report generation failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report generation failed");
    } finally {
      setIsGenerating(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const handleDownloadReport = async () => {
    if (!reportData?.report_id) return;

    try {
      const blob = await apiService.downloadReport(reportData.report_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `property_comparison_${reportData.report_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setSuccess("Report downloaded successfully!");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    }
  };

  const handleViewReport = () => {
    setShowPdfViewer(true);
  };

  const handleClosePdfViewer = () => {
    setShowPdfViewer(false);
  };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-blue-500 to-purple-600">
      <header className="bg-white/95 backdrop-blur-md py-8 text-center shadow-lg w-full">
        <div className="max-w-7xl mx-auto px-4">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Real Estate Property Analysis
          </h1>
          <p className="text-lg font-medium text-gray-600">
            Professional MLS Report Comparison Tool for Realtors
          </p>
        </div>
      </header>

      <main className="flex-1 p-8 w-full">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Status Messages */}
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg flex justify-between items-center">
              <span>{error}</span>
              <button
                onClick={clearMessages}
                className="text-red-500 hover:text-red-700"
              >
                ✕
              </button>
            </div>
          )}

          {success && (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg flex justify-between items-center">
              <span>{success}</span>
              <button
                onClick={clearMessages}
                className="text-green-500 hover:text-green-700"
              >
                ✕
              </button>
            </div>
          )}

          <div className="bg-white rounded-3xl p-8 shadow-xl">
            {/* MLS Report Upload */}
            <div className="mb-8 p-6 border-2 border-dashed border-gray-200 rounded-2xl transition-all duration-300 hover:border-blue-500 hover:bg-blue-50">
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                Step 1: Upload MLS Report
              </h2>
              <p className="text-gray-600 mb-6">
                Upload the main property MLS report you want to analyze
              </p>

              <div className="relative">
                <input
                  type="file"
                  id="mls-report"
                  accept=".pdf"
                  onChange={handleMlsReportUpload}
                  disabled={isUploading}
                  className="absolute opacity-0 w-full h-full cursor-pointer"
                />
                <label
                  htmlFor="mls-report"
                  className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-blue-500 rounded-xl bg-blue-50 cursor-pointer transition-all duration-300 hover:bg-blue-100 min-h-[150px]"
                >
                  <div className="text-5xl mb-4">📄</div>
                  <span className="text-lg font-medium text-gray-800 mb-2">
                    {isUploading ? "Uploading..." : "Choose MLS Report PDF"}
                  </span>
                  <span className="text-sm text-gray-500">
                    {isUploading ? "Please wait..." : "or drag and drop here"}
                  </span>
                </label>
              </div>

              {mlsReport && (
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg mt-4 border border-gray-200">
                  <div className="flex flex-col gap-1">
                    <span className="font-medium text-gray-800">
                      📋 {mlsReport.name}
                    </span>
                    <span className="text-sm text-gray-500">
                      {formatFileSize(mlsReport.size)}
                    </span>
                  </div>
                  <button
                    className="bg-red-500 text-white rounded-full w-8 h-8 flex items-center justify-center text-lg transition-colors duration-300 hover:bg-red-600"
                    onClick={() => setMlsReport(null)}
                  >
                    ✕
                  </button>
                </div>
              )}
            </div>

            {/* Comparison Properties Upload */}
            <div className="mb-8 p-6 border-2 border-dashed border-gray-200 rounded-2xl transition-all duration-300 hover:border-blue-500 hover:bg-blue-50">
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                Step 2: Upload Comparison Properties
              </h2>
              <p className="text-gray-600 mb-6">
                Upload PDF files of comparable properties for market analysis
              </p>

              <div className="relative">
                <input
                  type="file"
                  id="comparison-files"
                  accept=".pdf"
                  multiple
                  onChange={handleComparisonFilesUpload}
                  disabled={isUploading}
                  className="absolute opacity-0 w-full h-full cursor-pointer"
                />
                <label
                  htmlFor="comparison-files"
                  className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-blue-500 rounded-xl bg-blue-50 cursor-pointer transition-all duration-300 hover:bg-blue-100 min-h-[150px]"
                >
                  <div className="text-5xl mb-4">📊</div>
                  <span className="text-lg font-medium text-gray-800 mb-2">
                    {isUploading
                      ? "Uploading..."
                      : "Choose Comparison Property PDFs"}
                  </span>
                  <span className="text-sm text-gray-500">
                    {isUploading ? "Please wait..." : "select multiple files"}
                  </span>
                </label>
              </div>

              {comparisonFiles.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    Uploaded Comparison Files ({comparisonFiles.length})
                  </h3>
                  {comparisonFiles.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg mb-2 border border-gray-200"
                    >
                      <div className="flex flex-col gap-1">
                        <span className="font-medium text-gray-800">
                          🏠 {file.name}
                        </span>
                        <span className="text-sm text-gray-500">
                          {formatFileSize(file.size)}
                        </span>
                      </div>
                      <button
                        className="bg-red-500 text-white rounded-full w-8 h-8 flex items-center justify-center text-lg transition-colors duration-300 hover:bg-red-600"
                        onClick={() => removeComparisonFile(index)}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Generate Report Button */}
            <div className="text-center py-8">
              <button
                className={`inline-flex items-center gap-2 px-8 py-4 text-lg font-semibold rounded-full transition-all duration-300 shadow-lg ${
                  !mlsReport || comparisonFiles.length === 0 || isGenerating
                    ? "bg-gray-400 cursor-not-allowed"
                    : "bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:shadow-xl hover:-translate-y-0.5"
                }`}
                onClick={handleGenerateReport}
                disabled={
                  !mlsReport || comparisonFiles.length === 0 || isGenerating
                }
              >
                {isGenerating ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Generating Report...
                  </>
                ) : (
                  "Generate Property Analysis Report"
                )}
              </button>

              {(!mlsReport || comparisonFiles.length === 0) && (
                <p className="text-red-500 text-sm font-medium mt-4">
                  Please upload both an MLS report and at least one comparison
                  property to generate the analysis.
                </p>
              )}

              {/* Report Actions */}
              {reportData && (
                <div className="mt-6 space-y-4">
                  <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <button
                      onClick={handleViewReport}
                      className="inline-flex items-center gap-2 px-6 py-3 text-lg font-semibold rounded-full transition-all duration-300 shadow-lg bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:shadow-xl hover:-translate-y-0.5"
                    >
                      👁️ View Report
                    </button>
                    <button
                      onClick={handleDownloadReport}
                      className="inline-flex items-center gap-2 px-6 py-3 text-lg font-semibold rounded-full transition-all duration-300 shadow-lg bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:shadow-xl hover:-translate-y-0.5"
                    >
                      📥 Download Report
                    </button>
                  </div>
                  <p className="text-gray-600 text-sm font-medium text-center">
                    View the report in your browser or download the complete PDF
                    with property comparisons, charts, and appraisal analysis.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Features Section */}
          <div className="bg-white rounded-3xl p-8 shadow-xl">
            <h2 className="text-3xl font-semibold text-gray-800 text-center mb-8">
              What This Tool Provides
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center p-6 rounded-2xl bg-blue-50 border border-blue-100 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg">
                <div className="text-5xl mb-4">📊</div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  Property Comparison
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  Side-by-side analysis of property features, pricing, and
                  market data
                </p>
              </div>
              <div className="text-center p-6 rounded-2xl bg-blue-50 border border-blue-100 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg">
                <div className="text-5xl mb-4">📈</div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  Market Analysis
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  Visual charts comparing list prices vs sold prices and price
                  per square foot
                </p>
              </div>
              <div className="text-center p-6 rounded-2xl bg-blue-50 border border-blue-100 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg">
                <div className="text-5xl mb-4">💰</div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  Appraisal Report
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  Professional appraisal estimates based on comparable market
                  analysis
                </p>
              </div>
              <div className="text-center p-6 rounded-2xl bg-blue-50 border border-blue-100 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg">
                <div className="text-5xl mb-4">📄</div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  PDF Report
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  Downloadable professional report ready for client
                  presentations
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* PDF Viewer Modal */}
      {showPdfViewer && reportData && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl h-full max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-2xl font-semibold text-gray-800">
                Property Analysis Report
              </h2>
              <button
                onClick={handleClosePdfViewer}
                className="text-gray-500 hover:text-gray-700 text-2xl font-bold transition-colors duration-300"
              >
                ✕
              </button>
            </div>

            {/* PDF Viewer */}
            <div className="flex-1 p-4">
              <iframe
                src={apiService.getReportViewUrl(reportData.report_id)}
                className="w-full h-full border-0 rounded-lg"
                title="Property Analysis Report"
              />
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between p-6 border-t border-gray-200">
              <p className="text-gray-600 text-sm">
                Use the browser's zoom controls to adjust the view
              </p>
              <button
                onClick={handleDownloadReport}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-300 bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:shadow-lg"
              >
                📥 Download PDF
              </button>
            </div>
          </div>
        </div>
      )}

      <footer className="bg-white/95 backdrop-blur-md py-6 text-center border-t border-gray-200 mt-auto w-full">
        <div className="max-w-7xl mx-auto px-4">
          <p className="text-gray-600 font-medium">
            Professional Real Estate Analysis Tool • Built for Realtors
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
