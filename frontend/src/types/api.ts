export interface DocumentSummary {
  document_id: string;
  filename: string;
  chunk_count: number;
  upload_date: string;
  file_type: string;
}

export interface SearchResultItem {
  document_id: string;
  filename: string;
  chunk_number: number;
  page: number | null;
  text: string;
  semantic_score: number;
  keyword_score: number;
  combined_score: number;
}

export interface Citation {
  document_id: string;
  filename: string;
  chunk_number: number;
  page: number | null;
  snippet: string;
  score: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export interface ImageSearchResultItem {
  image_id: string;
  filename: string;
  ocr_text: string;
  image_path: string;
  score: number;
}
