import { create } from "zustand";

type WalletConnectionStatus = "disconnected" | "connecting" | "connected";

interface WalletState {
  status: WalletConnectionStatus;
  address: string | null;
}

interface WalletActions {
  setStatus: (status: WalletConnectionStatus) => void;
  setAddress: (address: string | null) => void;
  disconnect: () => void;
}

export type WalletStore = WalletState & WalletActions;

const initialState: WalletState = {
  status: "disconnected",
  address: null
};

export const useWalletStore = create<WalletStore>((set) => ({
  ...initialState,
  setStatus: (status) => set({ status }),
  setAddress: (address) => set({ address: address?.trim() || null }),
  disconnect: () => set(initialState)
}));

