import React, { useState, useEffect } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { motion } from "framer-motion";
import { ShieldCheck, RefreshCw, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import InteractiveBackground from "@/components/InteractiveBackground";

const OtpPage: React.FC = () => {
  const location = useLocation();
  const email = (location.state as any)?.email;
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lockedUntil, setLockedUntil] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const { verifyOtp, resendOtp } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  if (!email) return <Navigate to="/login" replace />;

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    const normalizedOtp = otp.replace(/\D/g, "").slice(0, 6);
    if (!normalizedOtp) return;
    setError("");
    setLockedUntil(null);
    setLoading(true);
    try {
      await verifyOtp(email, normalizedOtp);
      toast.success("Authenticated successfully");
      navigate("/", { replace: true });
    } catch (err: any) {
      const lockUntil = err.response?.data?.locked_until || null;
      if (lockUntil) setLockedUntil(lockUntil);
      const msg = err.response?.data?.error || err.response?.data?.detail || err.response?.data?.message || "Invalid OTP";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0) return;
    try {
      await resendOtp(email);
      setCooldown(60);
      setLockedUntil(null);
      setError("");
      toast.success("OTP resent to your email");
    } catch (err: any) {
      const msg = err.response?.data?.error || err.response?.data?.detail || "Failed to resend OTP";
      if (err.response?.status === 429) {
        const remaining = Number(err.response?.data?.cooldown_remaining_seconds);
        const requestsLastHour = Number(err.response?.data?.requests_last_hour);
        const maxPerHour = Number(err.response?.data?.max_per_hour);

        if (Number.isFinite(remaining) && remaining > 0) {
          const waitSeconds = Math.ceil(remaining);
          setCooldown(waitSeconds);
          setError(`Please wait ${waitSeconds} seconds before requesting another OTP.`);
        } else if (
          Number.isFinite(requestsLastHour) &&
          Number.isFinite(maxPerHour) &&
          requestsLastHour >= maxPerHour
        ) {
          setError("Hourly OTP limit reached. Please try again later.");
        } else {
          setError(msg);
        }
        toast.error(msg);
      } else {
        setError(msg);
        toast.error(msg);
      }
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
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <ShieldCheck className="text-primary" size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold">Verify OTP</h1>
            <p className="text-xs text-muted-foreground">Sent to {email}</p>
          </div>
        </div>

        <form onSubmit={handleVerify} className="space-y-4">
          <input
            type="text"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
            className="glass-input w-full text-center text-2xl tracking-[0.5em] font-mono"
            placeholder="000000"
            maxLength={6}
            inputMode="numeric"
            autoFocus
          />

          {error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle size={14} /> {error}
            </motion.div>
          )}

          {lockedUntil && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs text-amber-300">
              OTP locked until {new Date(lockedUntil).toLocaleString()}
            </motion.div>
          )}

          <motion.button
            whileTap={{ scale: 0.97 }}
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? "Verifying..." : "Verify & Continue"}
          </motion.button>
        </form>

        <div className="mt-4 text-center">
          <button
            onClick={handleResend}
            disabled={cooldown > 0}
            className="text-sm text-primary hover:underline disabled:text-muted-foreground disabled:no-underline flex items-center gap-1 mx-auto"
          >
            <RefreshCw size={14} />
            {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend OTP"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default OtpPage;
