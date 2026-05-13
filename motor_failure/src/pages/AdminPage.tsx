import React, { useState } from "react";
import { motion } from "framer-motion";
import { UserPlus, AlertCircle, CheckCircle, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import GlassCard from "@/components/GlassCard";
import apiClient from "@/lib/api-client";

const AdminPage: React.FC = () => {
  const { user } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("operator");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [generatedCredentials, setGeneratedCredentials] = useState<{
    username: string;
    email: string;
    password: string;
  } | null>(null);

  // Check if user is admin
  if (!user || !["admin", "owner"].includes(user.role || "")) {
    return (
      <div className="p-6">
        <GlassCard>
          <div className="flex items-center gap-3 text-destructive mb-4">
            <AlertCircle size={24} />
            <h1 className="text-xl font-bold">Access Denied</h1>
          </div>
          <p className="text-muted-foreground">
            You don't have permission to access this page. Only administrators can create new users.
          </p>
        </GlassCard>
      </div>
    );
  }

  const handleGeneratePassword = () => {
    const chars =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*";
    let pass = "";
    for (let i = 0; i < 12; i++) {
      pass += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setPassword(pass);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);

    if (!username.trim() || !email.trim() || !password.trim()) {
      setError("Please fill in all fields");
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.post("/auth/admin/create-user", {
        username: username.trim(),
        email: email.trim().toLowerCase(),
        password,
        role,
      });

      setGeneratedCredentials({
        username: response.data.username,
        email: response.data.email,
        password: response.data.temporary_password,
      });

      setSuccess(true);
      setUsername("");
      setEmail("");
      setPassword("");
      setRole("operator");
      toast.success("User created successfully!");
    } catch (err: any) {
      const msg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        "Failed to create user";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">User Management</h1>
        <p className="text-muted-foreground">
          Create new user accounts and manage permissions
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Create User Form */}
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-6">
            <UserPlus className="text-primary" size={24} />
            <h2 className="text-lg font-semibold">Create New User</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-foreground mb-2 block">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="glass-input w-full"
                placeholder="Enter username"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-foreground mb-2 block">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="glass-input w-full"
                placeholder="Enter email"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-foreground mb-2 block">
                Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="glass-input w-full"
              >
                <option value="operator">Operator</option>
                <option value="supervisor">Supervisor</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-foreground">
                  Temporary Password
                </label>
                <button
                  type="button"
                  onClick={handleGeneratePassword}
                  className="text-xs text-primary hover:underline"
                >
                  Generate
                </button>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="glass-input w-full pr-10"
                  placeholder="Enter or generate password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
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
              className="w-full py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create User"}
            </motion.button>
          </form>
        </GlassCard>

        {/* Success Credentials */}
        {success && generatedCredentials && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <GlassCard className="p-6 border-green-500/50 bg-green-500/5">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle className="text-green-500" size={24} />
                <h2 className="text-lg font-semibold">User Created Successfully</h2>
              </div>

              <div className="space-y-4">
                <div className="bg-black/20 rounded-lg p-4 space-y-3">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Username</p>
                    <p className="text-sm font-mono">{generatedCredentials.username}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Email</p>
                    <p className="text-sm font-mono">{generatedCredentials.email}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Temporary Password</p>
                    <p className="text-sm font-mono break-all">
                      {generatedCredentials.password}
                    </p>
                  </div>
                </div>

                <p className="text-xs text-muted-foreground">
                  The user has been sent this information via email. They should change
                  their password on first login.
                </p>

                <button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `Username: ${generatedCredentials.username}\nEmail: ${generatedCredentials.email}\nPassword: ${generatedCredentials.password}`
                    );
                    toast.success("Credentials copied to clipboard");
                  }}
                  className="w-full py-2 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary font-semibold text-sm transition-colors"
                >
                  Copy Credentials
                </button>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Help Text */}
        <GlassCard className="p-6 lg:col-span-2">
          <h3 className="font-semibold mb-3">User Creation Guidelines</h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>
              • <strong>Username:</strong> 3-30 characters (letters, numbers, _.-). Must be unique.
            </li>
            <li>
              • <strong>Email:</strong> Must be a valid email address and unique in the system.
            </li>
            <li>
              • <strong>Password:</strong> Minimum 8 characters. Share securely and ask user to change on first login.
            </li>
            <li>
              • <strong>Role:</strong> Operator (basic access), Supervisor (monitoring), Admin (full control).
            </li>
            <li>
              • Password reset emails will be automatically sent to the new user's email address.
            </li>
          </ul>
        </GlassCard>
      </div>
    </div>
  );
};

export default AdminPage;
