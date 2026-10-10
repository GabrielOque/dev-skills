/** Error body of every non-2xx answer: `{code, message, detail?}`. */
export interface ApiErrorBody {
  /** Stable SCREAMING_SNAKE_CASE code. Map it in `libs/api-messages.ts`. */
  code?: string;
  /** English, for developers. Never shown to people. */
  message?: string;
  detail?: unknown;
  [key: string]: unknown;
}

/** Envelope of every paginated listing. */
export interface PaginatedResponse<TItem> {
  results: TItem[];
  page: number;
  page_size: number;
  total_pages: number;
  total_rows: number;
}
