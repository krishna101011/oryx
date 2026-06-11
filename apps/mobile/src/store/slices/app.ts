import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

export interface AppState {
  /** Online connectivity, updated by NetInfo (later phase). */
  online: boolean;
  /** Whether the app has finished its boot sequence. */
  booted: boolean;
}

const initialState: AppState = {
  online: true,
  booted: false,
};

const slice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    setOnline(state, action: PayloadAction<boolean>) {
      state.online = action.payload;
    },
    booted(state) {
      state.booted = true;
    },
  },
});

export const appActions = slice.actions;
export const appReducer = slice.reducer;
