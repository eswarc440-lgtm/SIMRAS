/// <reference types="vite/client" />

declare const CESIUM_BASE_URL: string;

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_CESIUM_ION_TOKEN?: string;
  readonly VITE_DEFAULT_ASSET_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

