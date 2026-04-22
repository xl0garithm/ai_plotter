/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Optional API origin for chess routes (e.g. `http://127.0.0.1:5000`). Empty = same-origin. */
  readonly VITE_CHESS_API_BASE?: string;
  /** Set to `false` to skip POSTing moves to the physical plotter backend. */
  readonly VITE_ENABLE_PHYSICAL_CHESS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
