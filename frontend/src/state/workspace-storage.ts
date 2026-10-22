export interface WorkspaceStorageAdapter<T> {
  load: () => T | null;
  save: (value: T) => void;
  clear: () => void;
}

function isBrowser() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function createLocalStorageAdapter<T>(key: string): WorkspaceStorageAdapter<T> {
  return {
    load: () => {
      if (!isBrowser()) return null;

      const raw = window.localStorage.getItem(key);
      if (!raw) return null;

      try {
        return JSON.parse(raw) as T;
      } catch {
        return null;
      }
    },
    save: (value) => {
      if (!isBrowser()) return;

      try {
        window.localStorage.setItem(key, JSON.stringify(value));
      } catch {
        // Ignore persistence failures so runtime state still works.
      }
    },
    clear: () => {
      if (!isBrowser()) return;
      window.localStorage.removeItem(key);
    }
  };
}
