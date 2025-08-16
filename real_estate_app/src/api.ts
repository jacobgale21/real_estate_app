const API_BASE_URL = "http://localhost:8000";

export interface UploadedFile {
  file_id: string;
  filename: string;
  file_size: number;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  file_id?: string;
  filename?: string;
  file_size?: number;
  uploaded_files?: UploadedFile[];
}

export interface ReportData {
  property_comparison: Record<string, any>;
  price_analysis: Record<string, any>;
  appraisal_report: string[];
}

export interface ManualInputData {
  address: string;
  status: string;
  subdivision: string;
  yearBuilt: string;
  livingSqFt: string;
  totalSqFt: string;
  bedrooms: string;
  bathrooms: string;
  stories: string;
  garageSpaces: string;
  privatePool: string;
  listPrice: string;
  listPricePerSqFt: string;
  soldPrice: string;
  soldPricePerSqFt: string;
  daysOnMarket: string;
  isRental: boolean;
  interior: string;
  exterior: string;
  publicRemarks: string;
}

export interface GenerateReportResponse {
  success: boolean;
  message: string;
  report_data: ReportData;
  report_id: string;
  report_url: string;
  graphs_generated: string[];
}

export interface GeneratePromptResponse {
  success: boolean;
  message: string;
  prompt: string;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  // Upload single input PDF
  async uploadInputPdf(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${this.baseUrl}/upload-input-pdf`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Upload failed");
    }

    return response.json();
  }

  // Upload multiple comparison PDFs
  async uploadComparisonPdfs(files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(`${this.baseUrl}/upload-comparison-pdf`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Upload failed");
    }

    return response.json();
  }

  async generateChatgptPrompt(
    inputFileId: string,
    comparisonFileIds: string[]
  ): Promise<GeneratePromptResponse> {
    const url = `${this.baseUrl}/generate-report-chatgpt?input_file=${inputFileId}&comparison_files=${comparisonFileIds.join(",")}`;
    const response = await fetch(url, {
      method: "GET",
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Prompt generation failed");
    }
    return response.json();
  }

  async generateChatgptPromptManual(
    manualData: ManualInputData,
    comparisonFileIds: string[]
  ): Promise<GeneratePromptResponse> {
    const comparisonFilesParam = comparisonFileIds.join(",");
    const url = `${this.baseUrl}/generate-chatgpt-prompt-manual?comparison_files=${comparisonFilesParam}`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(manualData),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Prompt generation failed");
    }

    return response.json();
  }

  // Generate report with file input
  async generateReport(
    inputFileId: string,
    comparisonFileIds: string[]
  ): Promise<GenerateReportResponse> {
    const comparisonFilesParam = comparisonFileIds.join(",");
    const url = `${this.baseUrl}/generate-report?input_file=${inputFileId}&comparison_files=${comparisonFilesParam}`;

    const response = await fetch(url, {
      method: "GET",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Report generation failed");
    }

    return response.json();
  }

  // Generate report with manual input
  async generateReportWithManualInput(
    manualData: ManualInputData,
    comparisonFileIds: string[]
  ): Promise<GenerateReportResponse> {
    const comparisonFilesParam = comparisonFileIds.join(",");
    const url = `${this.baseUrl}/generate-report-manual?comparison_files=${comparisonFilesParam}`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(manualData),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Report generation failed");
    }

    return response.json();
  }
  // Download report
  async downloadReport(reportId: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/download-report/${reportId}`,
      {
        method: "GET",
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Download failed");
    }

    return response.blob();
  }

  // Get report view URL for embedding
  getReportViewUrl(reportId: string): string {
    return `${this.baseUrl}/view-report/${reportId}`;
  }

  // List uploaded files (for debugging)
  async listFiles(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/files`, {
      method: "GET",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to list files");
    }

    return response.json();
  }

  // Delete uploaded file
  async deleteFile(fileId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/files/${fileId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Delete failed");
    }

    return response.json();
  }
}

export const apiService = new ApiService();
