import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

interface UploadState {
  isUploading: boolean;
  taskId: string | null;
  error: string | null;
}

const initialState: UploadState = {
  isUploading: false,
  taskId: null,
  error: null,
};

export const uploadFile = createAsyncThunk(
  "upload/uploadFile",
  async (file: File, { rejectWithValue }) => {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await axios.post("http://localhost:8000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return response.data.task_id;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || "Upload failed");
    }
  }
);

const uploadSlice = createSlice({
  name: "upload",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(uploadFile.pending, (state) => {
        state.isUploading = true;
        state.error = null;
      })
      .addCase(uploadFile.fulfilled, (state, action) => {
        state.isUploading = false;
        state.taskId = action.payload;
      })
      .addCase(uploadFile.rejected, (state, action) => {
        state.isUploading = false;
        state.error = action.payload as string;
      });
  },
});

export default uploadSlice.reducer;
