import { configureStore } from "@reduxjs/toolkit";
import uploadReducer from "./uploadSlice";

export const store = configureStore({
  reducer: {
    upload: uploadReducer,
  },
});

// these inferred types will be used by your hooks.ts
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export default store;
