import { combineReducers, configureStore, type UnknownAction } from "@reduxjs/toolkit";
import {
  FLUSH,
  PAUSE,
  PERSIST,
  PURGE,
  REGISTER,
  REHYDRATE,
  persistReducer,
  persistStore,
  type WebStorage,
} from "redux-persist";

import { authReducer } from "./slices";

const PERSIST_KEY = "{{PROJECT_SLUG}}";

/** Dispatched by `actions/auth/logout.ts`; resets every slice to its initial state. */
export const USER_LOGOUT = "session/logout";

/**
 * redux-persist touches `localStorage`, which does not exist during SSR. This
 * wrapper is a no-op on the server and swallows quota / privacy-mode errors on
 * the client.
 */
const createSafeStorage = (): WebStorage => {
  if (typeof window === "undefined") {
    return {
      getItem: () => Promise.resolve(null),
      setItem: () => Promise.resolve(),
      removeItem: () => Promise.resolve(),
    };
  }
  const attempt = <T>(operation: () => T, fallback: T) => {
    try {
      return Promise.resolve(operation());
    } catch {
      return Promise.resolve(fallback);
    }
  };
  return {
    getItem: (key) => attempt(() => window.localStorage.getItem(key), null),
    setItem: (key, value) => attempt(() => window.localStorage.setItem(key, value), undefined),
    removeItem: (key) => attempt(() => window.localStorage.removeItem(key), undefined),
  };
};

const appReducer = combineReducers({
  auth: authReducer,
});

export type AppState = ReturnType<typeof appReducer>;

/** One `USER_LOGOUT` resets the whole tree. Pure: side effects live in the logout action. */
const rootReducer = (state: AppState | undefined, action: UnknownAction): AppState =>
  appReducer(action.type === USER_LOGOUT ? undefined : state, action);

const persistedReducer = persistReducer(
  { key: PERSIST_KEY, storage: createSafeStorage(), whitelist: ["auth"] },
  rootReducer,
);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: { ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER] },
    }),
});

export const persistor = persistStore(store);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
