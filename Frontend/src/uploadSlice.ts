import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import type { PayloadAction, ActionReducerMapBuilder } from "@reduxjs/toolkit";
import axios from "axios";

// 1) Define the state interface
interface UploadState {
  status: "idle" | "loading" | "succeeded" | "failed";
  data: any;           // or a more specific type for your response
  error: string | null;
}

const initialState: UploadState = {
  status: "idle",
  data: null,
  error: null,
};

// 2) createAsyncThunk with proper generics:
//    <Returned, ThunkArg, { rejectValue: RejectedValue }>
export const uploadFile = createAsyncThunk<
  any,         // what the payload creator returns on success
  File,        // single argument type
  { rejectValue: string }
>("upload/file", async (file, { rejectWithValue }) => {
  try {
    const form = new FormData();
    form.append("file", file);
    const resp = await axios.post("/api/upload", form);
    return resp.data;
  } catch (err: any) {
    return rejectWithValue(err.message);
  }
});

const uploadSlice = createSlice({
  name: "upload",
  initialState,
  reducers: {},
  extraReducers: (builder: ActionReducerMapBuilder<UploadState>) => {
    builder
      .addCase(uploadFile.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(uploadFile.fulfilled, (state, action: PayloadAction<any>) => {
        state.status = "succeeded";
        state.data = action.payload;
      })
      .addCase(uploadFile.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload as string;
      });
  },
});

export default uploadSlice.reducer;
