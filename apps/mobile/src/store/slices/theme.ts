import { createSlice } from '@reduxjs/toolkit';

export interface ThemeState {
  /** Phase 1 supports dark only; light is reserved. */
  mode: 'dark';
}

const initialState: ThemeState = { mode: 'dark' };

const slice = createSlice({
  name: 'theme',
  initialState,
  reducers: {},
});

export const themeReducer = slice.reducer;
