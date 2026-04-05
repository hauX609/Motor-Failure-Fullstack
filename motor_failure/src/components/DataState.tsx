import React from "react";
import { AlertCircle, RefreshCw, Inbox } from "lucide-react";
import { motion } from "framer-motion";

interface Props {
  isLoading?: boolean;
  isError?: boolean;
  isEmpty?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  loadingText?: string;
  emptyText?: string;
  children: React.ReactNode;
}

const DataState: React.FC<Props> = ({ isLoading, isError, isEmpty, error, onRetry, loadingText = "Loading...", emptyText = "No data available", children }) => {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
          <RefreshCw size={24} className="text-muted-foreground" />
        </motion.div>
        <p className="text-sm text-muted-foreground">{loadingText}</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <AlertCircle size={24} className="text-destructive" />
        <p className="text-sm text-destructive">{error?.message || "Something went wrong"}</p>
        {onRetry && (
          <button onClick={onRetry} className="text-sm text-primary hover:underline flex items-center gap-1">
            <RefreshCw size={14} /> Retry
          </button>
        )}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <Inbox size={24} className="text-muted-foreground" />
        <p className="text-sm text-muted-foreground">{emptyText}</p>
      </div>
    );
  }

  return <>{children}</>;
};

export default DataState;
