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
  type_mismatch?: boolean;
  extracted_data?: Record<string, any>;
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
  async uploadInputPdf(file: File, token: string): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${this.baseUrl}/upload-input-pdf`, {
      method: "POST",
      body: formData,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Upload failed");
    }

    return response.json();
  }

  // Upload multiple comparison PDFs
  async uploadComparisonPdfs(
    files: File[],
    token: string
  ): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(`${this.baseUrl}/upload-comparison-pdf`, {
      method: "POST",
      body: formData,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Upload failed");
    }

    return response.json();
  }

  async generateChatgptPrompt(
    inputFileId: string,
    comparisonFileIds: string[],
    token: string
  ): Promise<GeneratePromptResponse> {
    const url = `${this.baseUrl}/generate-report-chatgpt?input_file=${inputFileId}&comparison_files=${comparisonFileIds.join(",")}`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Prompt generation failed");
    }
    return response.json();
  }

  async generateChatgptPromptManual(
    manualData: ManualInputData,
    comparisonFileIds: string[],
    token: string
  ): Promise<GeneratePromptResponse> {
    const comparisonFilesParam = comparisonFileIds.join(",");
    const url = `${this.baseUrl}/generate-chatgpt-prompt-manual?comparison_files=${comparisonFilesParam}`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
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
    comparisonFileIds: string[],
    token: string
  ): Promise<GenerateReportResponse> {
    const comparisonFilesParam = comparisonFileIds.join(",");
    const url = `${this.baseUrl}/generate-report?input_file=${inputFileId}&comparison_files=${comparisonFilesParam}`;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
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
    comparisonFileIds: string[],
    token: string
  ): Promise<GenerateReportResponse> {
    const comparisonFilesParam = comparisonFileIds.join(",");
    const url = `${this.baseUrl}/generate-report-manual?comparison_files=${comparisonFilesParam}`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
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
  async downloadReport(reportId: string, token: string): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/download-report/${reportId}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Download failed");
    }

    return response.blob();
  }

  // Get report view URL for embedding
  getReportViewUrl(reportId: string, token: string): string {
    return `${this.baseUrl}/view-report/${reportId}?token=${token}`;
  }

  // List uploaded files (for debugging)
  async listFiles(token: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/files`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to list files");
    }

    return response.json();
  }

  // Delete uploaded file
  async deleteFile(fileId: string, token: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/files/${fileId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Delete failed");
    }

    return response.json();
  }
}

export const apiService = new ApiService();
