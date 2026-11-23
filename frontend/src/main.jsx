import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import AuthProvider from "./context/AuthContext";
import ErrorBoundary from "./components/common/ErrorBoundary";
import "./index.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")).render(
  <ErrorBoundary>
    <BrowserRouter>
      <AuthProvider>
        <App />
        <Toaster position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  </ErrorBoundary>
);
