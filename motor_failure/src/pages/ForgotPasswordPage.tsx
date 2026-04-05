import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Cpu, ArrowRight, AlertCircle, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import InteractiveBackground from "@/components/InteractiveBackground";
import apiClient from "@/lib/api-client";

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setError("");
    setLoading(true);
    try {
      await apiClient.post("/auth/forgot-password", {
        email: email.trim().toLowerCase(),
      });
      setSubmitted(true);
      toast.success("Check your email for password reset link");
      setTimeout(() => navigate("/login"), 3000);
    } catch (err: any) {
      const msg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        "Failed to send reset email";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative">
      <InteractiveBackground />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="p-8 w-full max-w-md rounded-2xl bg-white/10 backdrop-blur-2xl border border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_8px_32px_rgba(0,0,0,0.3)]"
      >
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Cpu className="text-primary" size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold">MotorPredict</h1>
            <p className="text-xs text-muted-foreground">
              Motor Failure Prediction System
            </p>
          </div>
        </div>

        {submitted ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            <div className="flex justify-center">
              <CheckCircle className="text-green-500" size={48} />
            </div>
            <div className="text-center">
              <h2 className="text-lg font-semibold mb-2">Check Your Email</h2>
              <p className="text-sm text-muted-foreground mb-4">
                If an account exists with this email, you'll receive a password
                reset link shortly. The link is valid for 1 hour.
              </p>
              <p className="text-xs text-muted-foreground">
                Redirecting to login in 3 seconds...
              </p>
            </div>
            <button
              onClick={() => navigate("/login")}
              className="w-full py-2 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 transition-opacity"
            >
              Back to Login
            </button>
          </motion.div>
        ) : (
          <>
            <h2 className="text-sm font-semibold text-muted-foreground mb-6">
              Reset Your Password
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="glass-input w-full"
                  placeholder="Enter your email"
                  autoFocus
                />
              </div>

              {error && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-2 text-sm text-destructive"
                >
                  <AlertCircle size={14} /> {error}
                </motion.div>
              )}

              <motion.button
                whileTap={{ scale: 0.97 }}
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl bg-primary text-primary-foreground font-semibold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {loading ? "Sending..." : "Send Reset Link"}
                {!loading && <ArrowRight size={16} />}
              </motion.button>

              <div className="text-center">
                <a
                  href="/login"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Back to Login
                </a>
              </div>
            </form>
          </>
        )}
      </motion.div>
    </div>
  );
};

export default ForgotPasswordPage;
