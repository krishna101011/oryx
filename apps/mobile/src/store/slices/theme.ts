import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { ThemeMode } from '@oryx/shared-types';

export interface ThemeState {
  /**
   * The active mode. Defaults to dark (the brand baseline) until /auth/me
   * hydrates the account-synced preference; a Settings toggle sets it
   * optimistically and persists via PATCH /preferences.
   */
  mode: ThemeMode;
}

const initialState: ThemeState = { mode: 'dark' };

const slice = createSlice({
  name: 'theme',
  initialState,
  reducers: {
    modeSet(state, action: PayloadAction<ThemeMode>) {
      state.mode = action.payload;
    },
  },
});

export const themeActions = slice.actions;
export const themeReducer = slice.reducer;
