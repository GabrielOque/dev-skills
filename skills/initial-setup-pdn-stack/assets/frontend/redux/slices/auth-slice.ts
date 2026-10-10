import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import type { OrganizationInfo, SessionState, UserInfo } from "@/t/auth";

const initialState: SessionState = {
  user: null,
  organization: null,
};

/**
 * The persisted half of the session: who is signed in and in which
 * organization. Tokens are not here — they live in cookies so `proxy.ts` can
 * read them (see `libs/cookies.ts`).
 *
 * Reducers stay pure: writing cookies, purging storage and navigating happen
 * in `actions/auth/*`, never inside a reducer.
 */
const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setSession: (state, action: PayloadAction<{ user: UserInfo; organization: OrganizationInfo }>) => {
      state.user = action.payload.user;
      state.organization = action.payload.organization;
    },
    setUser: (state, action: PayloadAction<UserInfo>) => {
      state.user = action.payload;
    },
  },
});

export const { setSession, setUser } = authSlice.actions;

export default authSlice.reducer;
