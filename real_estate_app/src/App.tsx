import { useState } from "react";
import { apiService } from "./api";
import type { GenerateReportResponse, ManualInputData } from "./api";
import {
  withAuthenticator,
  View,
  useTheme,
  Heading,
  Text,
} from "@aws-amplify/ui-react";
import { Amplify } from "aws-amplify";
import { signOut } from "aws-amplify/auth";
import awsExports from "./aws-exports";
import "@aws-amplify/ui-react/styles.css";
import "./authenticator.css";

Amplify.configure(awsExports);

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
  const [hasInputMLS, setHasInputMLS] = useState(true);
  const [showInputForm, setShowInputForm] = useState(false);
  const [chatgptPrompt, setChatgptPrompt] = useState<string | null>(null);
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState(false);
  const [showPromptSection, setShowPromptSection] = useState(false);
  const [manualInputData, setManualInputData] = useState({
    address: "",
    status: "Active",
    subdivision: "",
    yearBuilt: "",
    livingSqFt: "",
    totalSqFt: "",
    bedrooms: "",
    bathrooms: "",
    stories: "",
    garageSpaces: "",
    privatePool: "No",
    listPrice: "",
    listPricePerSqFt: "",
    soldPrice: "",
    soldPricePerSqFt: "",
    daysOnMarket: "",
    isRental: false,
    internalFeatures: "",
    exteriorFeatures: "",
    publicRemarks: "",
  });
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
    // Reset prompt when files change
    setChatgptPrompt(null);
    setShowPromptSection(false);
  };

  const handleGenerateChatgptPrompt = async () => {
    if (hasInputMLS) {
      if (!mlsReport || !mlsReport.file_id) {
        setError("Please upload an MLS report first.");
        return;
      }
    } else {
      if (
        !manualInputData.address ||
        !manualInputData.livingSqFt ||
        !manualInputData.listPrice
      ) {
        setError(
          "Please enter at least Address, Living Square Feet, and List Price."
        );
        return;
      }
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

    setIsGeneratingPrompt(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await apiService.generateChatgptPrompt(
        hasInputMLS ? mlsReport!.file_id! : "manual",
        comparisonFileIds
      );

      if (response.success) {
        setChatgptPrompt(response.prompt);
        setShowPromptSection(true);
        setSuccess("ChatGPT prompt generated successfully!");
      } else {
        setError(response.message || "Prompt generation failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prompt generation failed");
    } finally {
      setIsGeneratingPrompt(false);
    }
  };

  const handleGenerateReport = async () => {
    if (hasInputMLS) {
      if (!mlsReport || !mlsReport.file_id) {
        setError("Please upload an MLS report first.");
        return;
      }
    } else {
      if (
        !manualInputData.address ||
        !manualInputData.livingSqFt ||
        !manualInputData.listPrice
      ) {
        setError(
          "Please enter at least Address, Living Square Feet, and List Price."
        );
        return;
      }
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
      let response;
      if (hasInputMLS) {
        response = await apiService.generateReport(
          mlsReport!.file_id!,
          comparisonFileIds
        );
      } else {
        // Generate report with manual input data
        response = await apiService.generateReportWithManualInput(
          manualInputData as ManualInputData,
          comparisonFileIds
        );
      }

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

  const toggleInputMethod = () => {
    setHasInputMLS(!hasInputMLS);
    setMlsReport(null);
    setManualInputData({
      address: "",
      status: "Active",
      subdivision: "",
      yearBuilt: "",
      livingSqFt: "",
      totalSqFt: "",
      bedrooms: "",
      bathrooms: "",
      stories: "",
      garageSpaces: "",
      privatePool: "No",
      listPrice: "",
      listPricePerSqFt: "",
      soldPrice: "",
      soldPricePerSqFt: "",
      daysOnMarket: "",
      isRental: false,
      internalFeatures: "",
      exteriorFeatures: "",
      publicRemarks: "",
    });
    setShowInputForm(false);
    setError(null);
    setSuccess(null);
    // Reset prompt when input method changes
    setChatgptPrompt(null);
    setShowPromptSection(false);
  };

  const handleManualInputChange = (field: string, value: string | boolean) => {
    setManualInputData((prev) => {
      const updatedData = {
        ...prev,
        [field]: value,
      };

      // Auto-calculate list price per sq ft when both living sq ft and list price are available
      if (field === "livingSqFt" || field === "listPrice") {
        const livingSqFt =
          field === "livingSqFt"
            ? typeof value === "string"
              ? value
              : ""
            : prev.livingSqFt;
        const listPrice =
          field === "listPrice"
            ? typeof value === "string"
              ? value
              : ""
            : prev.listPrice;

        if (livingSqFt && listPrice) {
          // Remove commas and $ signs for calculation
          const cleanSqFt = livingSqFt.replace(/[,$]/g, "");
          const cleanPrice = listPrice.replace(/[,$]/g, "");

          const sqFtNum = parseFloat(cleanSqFt);
          const priceNum = parseFloat(cleanPrice);

          if (!isNaN(sqFtNum) && !isNaN(priceNum) && sqFtNum > 0) {
            const pricePerSqFt = priceNum / sqFtNum;
            updatedData.listPricePerSqFt = `$${pricePerSqFt.toFixed(2)}`;
          }
        }
      }

      return updatedData;
    });
  };

  const handleManualInputSubmit = () => {
    // Validate required fields
    if (
      !manualInputData.address ||
      !manualInputData.livingSqFt ||
      !manualInputData.listPrice
    ) {
      setError(
        "Please fill in at least Address, Living Square Feet, and List Price."
      );
      return;
    }

    setShowInputForm(false);
    setSuccess("Manual input data saved successfully!");
  };

  const handleSignOut = async () => {
    try {
      await signOut();
      setSuccess("Signed out successfully!");
    } catch (error) {
      setError("Error signing out. Please try again.");
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-blue-500 to-purple-600">
      <header className="bg-white/95 backdrop-blur-md py-8 text-center shadow-lg w-full relative">
        <div className="max-w-7xl mx-auto px-4">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Real Estate Property Analysis
          </h1>
          <p className="text-lg font-medium text-gray-600">
            Professional MLS Report Comparison Tool for Realtors
          </p>
        </div>
        <button
          onClick={handleSignOut}
          className="absolute top-4 right-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-300 bg-gradient-to-r from-red-500 to-red-600 text-white hover:shadow-lg hover:-translate-y-0.5"
        >
          🚪 Sign Out
        </button>
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
            {/* Input Method Selection */}
            <div className="mb-8 p-6 border-2 border-gray-200 rounded-2xl bg-gray-50">
              <h2 className="text-2xl font-semibold text-gray-800 mb-4">
                Step 1: Choose Input Method
              </h2>
              <div className="flex flex-col sm:flex-row gap-4">
                <button
                  onClick={toggleInputMethod}
                  className={`flex-1 p-4 rounded-xl border-2 transition-all duration-300 ${
                    hasInputMLS
                      ? "border-blue-500 bg-blue-50 text-blue-700"
                      : "border-gray-300 bg-white text-gray-700 hover:border-blue-300"
                  }`}
                >
                  <div className="text-2xl mb-2">📄</div>
                  <div className="font-semibold">I have an MLS Report</div>
                  <div className="text-sm opacity-75">Upload a PDF file</div>
                </button>
                <button
                  onClick={toggleInputMethod}
                  className={`flex-1 p-4 rounded-xl border-2 transition-all duration-300 ${
                    !hasInputMLS
                      ? "border-blue-500 bg-blue-50 text-blue-700"
                      : "border-gray-300 bg-white text-gray-700 hover:border-blue-300"
                  }`}
                >
                  <div className="text-2xl mb-2">✏️</div>
                  <div className="font-semibold">Manual Input</div>
                  <div className="text-sm opacity-75">Enter data manually</div>
                </button>
              </div>
            </div>

            {/* MLS Report Upload */}
            {hasInputMLS && (
              <div className="mb-8 p-6 border-2 border-dashed border-gray-200 rounded-2xl transition-all duration-300 hover:border-blue-500 hover:bg-blue-50">
                <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                  Upload MLS Report
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
                      onClick={() => {
                        setMlsReport(null);
                        // Reset prompt when MLS report is removed
                        setChatgptPrompt(null);
                        setShowPromptSection(false);
                      }}
                    >
                      ✕
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Manual Input Form */}
            {!hasInputMLS && (
              <div className="mb-8 p-6 border-2 border-gray-200 rounded-2xl bg-blue-50">
                <h2 className="text-2xl font-semibold text-gray-800 mb-4">
                  Manual Property Data Input
                </h2>
                <p className="text-gray-600 mb-6">
                  Enter the property information manually. At minimum, please
                  provide Address, Living Square Feet, and List Price.
                </p>

                {!showInputForm ? (
                  <button
                    onClick={() => setShowInputForm(true)}
                    className="inline-flex items-center gap-2 px-6 py-3 text-lg font-semibold rounded-full transition-all duration-300 shadow-lg bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:shadow-xl hover:-translate-y-0.5"
                  >
                    ✏️ Enter Property Data
                  </button>
                ) : (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Basic Information */}
                      <div className="space-y-4">
                        <h3 className="text-lg font-semibold text-gray-800 border-b pb-2">
                          Basic Information
                        </h3>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Address *
                          </label>
                          <input
                            type="text"
                            value={manualInputData.address}
                            onChange={(e) =>
                              handleManualInputChange("address", e.target.value)
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="123 Main St"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Status
                          </label>
                          <select
                            value={manualInputData.status}
                            onChange={(e) =>
                              handleManualInputChange("status", e.target.value)
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          >
                            <option value="Active">Active</option>
                            <option value="Closed">Closed</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Subdivision
                          </label>
                          <input
                            type="text"
                            value={manualInputData.subdivision}
                            onChange={(e) =>
                              handleManualInputChange(
                                "subdivision",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Windsor Park"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Year Built
                          </label>
                          <input
                            type="text"
                            value={manualInputData.yearBuilt}
                            onChange={(e) =>
                              handleManualInputChange(
                                "yearBuilt",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="2015"
                          />
                        </div>
                      </div>

                      {/* Property Details */}
                      <div className="space-y-4">
                        <h3 className="text-lg font-semibold text-gray-800 border-b pb-2">
                          Property Details
                        </h3>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Living Square Feet *
                          </label>
                          <input
                            type="text"
                            value={manualInputData.livingSqFt}
                            onChange={(e) =>
                              handleManualInputChange(
                                "livingSqFt",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="2,500"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Total Square Feet
                          </label>
                          <input
                            type="text"
                            value={manualInputData.totalSqFt}
                            onChange={(e) =>
                              handleManualInputChange(
                                "totalSqFt",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="3,200"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Bedrooms
                          </label>
                          <input
                            type="text"
                            value={manualInputData.bedrooms}
                            onChange={(e) =>
                              handleManualInputChange(
                                "bedrooms",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="4"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Bathrooms
                          </label>
                          <input
                            type="text"
                            value={manualInputData.bathrooms}
                            onChange={(e) =>
                              handleManualInputChange(
                                "bathrooms",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="3"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Additional Details */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-4">
                        <h3 className="text-lg font-semibold text-gray-800 border-b pb-2">
                          Additional Features
                        </h3>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Stories
                          </label>
                          <input
                            type="text"
                            value={manualInputData.stories}
                            onChange={(e) =>
                              handleManualInputChange("stories", e.target.value)
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="2"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Garage Spaces
                          </label>
                          <input
                            type="text"
                            value={manualInputData.garageSpaces}
                            onChange={(e) =>
                              handleManualInputChange(
                                "garageSpaces",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="2"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Private Pool
                          </label>
                          <select
                            value={manualInputData.privatePool}
                            onChange={(e) =>
                              handleManualInputChange(
                                "privatePool",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          >
                            <option value="Yes">Yes</option>
                            <option value="No">No</option>
                          </select>
                        </div>
                      </div>

                      {/* Pricing Information */}
                      <div className="space-y-4">
                        <h3 className="text-lg font-semibold text-gray-800 border-b pb-2">
                          Pricing Information
                        </h3>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            List Price *
                          </label>
                          <input
                            type="text"
                            value={manualInputData.listPrice}
                            onChange={(e) =>
                              handleManualInputChange(
                                "listPrice",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="$450,000"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            List Price per Sq Ft
                            {manualInputData.listPricePerSqFt &&
                              manualInputData.livingSqFt &&
                              manualInputData.listPrice && (
                                <span className="text-xs text-green-600 ml-2">
                                  (Auto-calculated)
                                </span>
                              )}
                          </label>
                          <input
                            type="text"
                            value={manualInputData.listPricePerSqFt}
                            onChange={(e) =>
                              handleManualInputChange(
                                "listPricePerSqFt",
                                e.target.value
                              )
                            }
                            className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                              manualInputData.listPricePerSqFt &&
                              manualInputData.livingSqFt &&
                              manualInputData.listPrice
                                ? "bg-green-50 border-green-300"
                                : ""
                            }`}
                            placeholder="$180"
                            readOnly={
                              !!(
                                manualInputData.listPricePerSqFt &&
                                manualInputData.livingSqFt &&
                                manualInputData.listPrice
                              )
                            }
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Sold Price
                          </label>
                          <input
                            type="text"
                            value={manualInputData.soldPrice}
                            onChange={(e) =>
                              handleManualInputChange(
                                "soldPrice",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="$440,000"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Sold Price per Sq Ft
                          </label>
                          <input
                            type="text"
                            value={manualInputData.soldPricePerSqFt}
                            onChange={(e) =>
                              handleManualInputChange(
                                "soldPricePerSqFt",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="$176"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Days on Market
                          </label>
                          <input
                            type="text"
                            value={manualInputData.daysOnMarket}
                            onChange={(e) =>
                              handleManualInputChange(
                                "daysOnMarket",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="45"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Additional Property Information */}
                    <div className="mb-6">
                      <h3 className="text-lg font-semibold text-gray-800 mb-4">
                        Additional Property Information
                      </h3>

                      <div className="grid grid-cols-1 gap-4">
                        {/* Rental Property Toggle */}
                        <div className="flex items-center space-x-3">
                          <input
                            type="checkbox"
                            id="isRental"
                            checked={manualInputData.isRental}
                            onChange={(e) =>
                              handleManualInputChange(
                                "isRental",
                                e.target.checked
                              )
                            }
                            className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                          />
                          <label
                            htmlFor="isRental"
                            className="text-sm font-medium text-gray-700"
                          >
                            This is a rental property
                          </label>
                        </div>

                        {/* Internal Features */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Internal Features
                          </label>
                          <textarea
                            value={manualInputData.internalFeatures}
                            onChange={(e) =>
                              handleManualInputChange(
                                "internalFeatures",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="e.g., Granite countertops, hardwood floors, stainless steel appliances..."
                            rows={3}
                          />
                        </div>

                        {/* Exterior Features */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Exterior Features
                          </label>
                          <textarea
                            value={manualInputData.exteriorFeatures}
                            onChange={(e) =>
                              handleManualInputChange(
                                "exteriorFeatures",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="e.g., Brick exterior, covered patio, mature landscaping..."
                            rows={3}
                          />
                        </div>

                        {/* Public Remarks */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Public Remarks
                          </label>
                          <textarea
                            value={manualInputData.publicRemarks}
                            onChange={(e) =>
                              handleManualInputChange(
                                "publicRemarks",
                                e.target.value
                              )
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Detailed description of the property, any special features, recent updates, or notable characteristics..."
                            rows={5}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Form Actions */}
                    <div className="flex gap-4 pt-4 border-t">
                      <button
                        onClick={handleManualInputSubmit}
                        className="inline-flex items-center gap-2 px-6 py-3 text-lg font-semibold rounded-full transition-all duration-300 shadow-lg bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:shadow-xl hover:-translate-y-0.5"
                      >
                        ✅ Save Property Data
                      </button>
                      <button
                        onClick={() => setShowInputForm(false)}
                        className="inline-flex items-center gap-2 px-6 py-3 text-lg font-semibold rounded-full transition-all duration-300 shadow-lg bg-gray-500 text-white hover:shadow-xl hover:-translate-y-0.5"
                      >
                        ❌ Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Display saved data */}
                {!showInputForm && manualInputData.address && (
                  <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                    <h4 className="font-semibold text-green-800 mb-2">
                      ✅ Property Data Saved
                    </h4>
                    <p className="text-green-700 text-sm">
                      Address: {manualInputData.address} | Living Sq Ft:{" "}
                      {manualInputData.livingSqFt} | List Price:{" "}
                      {manualInputData.listPrice}
                    </p>
                  </div>
                )}
              </div>
            )}

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

            {/* ChatGPT Prompt Generation Button */}
            {((hasInputMLS && mlsReport) ||
              (!hasInputMLS && manualInputData.address)) &&
              comparisonFiles.length > 0 && (
                <div className="mb-8 p-6 border-2 border-gray-200 rounded-2xl bg-green-50">
                  <h2 className="text-2xl font-semibold text-gray-800 mb-4">
                    Step 3: Generate ChatGPT Prompt
                  </h2>
                  <p className="text-gray-600 mb-6">
                    Generate a professional ChatGPT prompt for property analysis
                    that you can use with ChatGPT or other AI tools.
                  </p>

                  <div className="text-center">
                    <button
                      className={`inline-flex items-center gap-2 px-6 py-3 text-lg font-semibold rounded-full transition-all duration-300 shadow-lg ${
                        isGeneratingPrompt
                          ? "bg-gray-400 cursor-not-allowed"
                          : "bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:shadow-xl hover:-translate-y-0.5"
                      }`}
                      onClick={handleGenerateChatgptPrompt}
                      disabled={isGeneratingPrompt}
                    >
                      {isGeneratingPrompt ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                          Generating Prompt...
                        </>
                      ) : (
                        <>🤖 Generate ChatGPT Prompt</>
                      )}
                    </button>
                  </div>
                </div>
              )}

            {/* ChatGPT Prompt Suggestion Section */}
            {showPromptSection && chatgptPrompt && (
              <div className="mb-8 p-6 border-2 border-gray-200 rounded-2xl bg-blue-50">
                <h2 className="text-2xl font-semibold text-gray-800 mb-4">
                  🤖 ChatGPT Prompt Suggestion
                </h2>
                <p className="text-gray-600 mb-6">
                  Copy this prompt and use it with ChatGPT or other AI tools for
                  professional property analysis.
                </p>

                <div className="relative">
                  <textarea
                    value={chatgptPrompt}
                    readOnly
                    className="w-full h-64 p-4 border border-gray-300 rounded-lg bg-white font-mono text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Generated prompt will appear here..."
                  />
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(chatgptPrompt);
                      setSuccess("Prompt copied to clipboard!");
                    }}
                    className="absolute top-2 right-2 bg-blue-500 text-white px-3 py-1 rounded-md text-sm hover:bg-blue-600 transition-colors duration-300"
                  >
                    📋 Copy
                  </button>
                </div>

                <div className="mt-4 text-sm text-gray-600">
                  <p>
                    <strong>How to use:</strong>
                  </p>
                  <ol className="list-decimal list-inside mt-2 space-y-1">
                    <li>Copy the prompt above</li>
                    <li>Go to ChatGPT or your preferred AI tool</li>
                    <li>Paste the prompt and send it</li>
                    <li>Review the generated analysis</li>
                  </ol>
                </div>
              </div>
            )}

            {/* Generate Report Button */}
            <div className="text-center py-8">
              <h2 className="text-2xl font-semibold text-gray-800 mb-4">
                Step 4: Generate Property Analysis Report
              </h2>
              <p className="text-gray-600 mb-6">
                Generate a comprehensive PDF report with property comparisons,
                charts, and appraisal analysis.
              </p>

              <button
                className={`inline-flex items-center gap-2 px-8 py-4 text-lg font-semibold rounded-full transition-all duration-300 shadow-lg ${
                  (hasInputMLS && !mlsReport) ||
                  (!hasInputMLS && !manualInputData.address) ||
                  comparisonFiles.length === 0 ||
                  isGenerating
                    ? "bg-gray-400 cursor-not-allowed"
                    : "bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:shadow-xl hover:-translate-y-0.5"
                }`}
                onClick={handleGenerateReport}
                disabled={
                  (hasInputMLS && !mlsReport) ||
                  (!hasInputMLS && !manualInputData.address) ||
                  comparisonFiles.length === 0 ||
                  isGenerating
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

              {((hasInputMLS && !mlsReport) ||
                (!hasInputMLS && !manualInputData.address) ||
                comparisonFiles.length === 0) && (
                <p className="text-red-500 text-sm font-medium mt-4">
                  {hasInputMLS
                    ? "Please upload both an MLS report and at least one comparison property to generate the analysis."
                    : "Please enter property data and upload at least one comparison property to generate the analysis."}
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

export default withAuthenticator(App, {
  components: {
    Header() {
      const { tokens } = useTheme();
      return (
        <View
          textAlign="center"
          padding={tokens.space.large}
          backgroundColor="transparent"
        >
          <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>🏠</div>
          <Heading
            level={3}
            color="white"
            style={{ fontWeight: "bold", marginBottom: "0.5rem" }}
          >
            Real Estate Property Analysis
          </Heading>
          <Text color="white" style={{ opacity: 0.9 }}>
            Professional MLS Report Comparison Tool
          </Text>
        </View>
      );
    },
  },
});
