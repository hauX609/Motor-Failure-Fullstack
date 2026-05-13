import React from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { useMock } from "@/context/MockContext";
import { LayoutDashboard, Cpu, Bell, Info, LogOut, Sun, Moon, Menu, X, FlaskConical, Wifi } from "lucide-react";
import { useState } from "react";
import InteractiveBackground from "@/components/InteractiveBackground";
import { RUNTIME } from "@/lib/runtime";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/motors", icon: Cpu, label: "Motors" },
  { to: "/alerts", icon: Bell, label: "Alerts" },
  { to: "/about", icon: Info, label: "About" },
];

const AppLayout: React.FC = () => {
  const { logout, user } = useAuth();
  const { theme, resolved, setTheme } = useTheme();
  const { isMock, setMock } = useMock();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const cycleTheme = () => {
    const current = theme === "system" ? resolved : theme;
    setTheme(current === "dark" ? "light" : "dark");
  };

  const ThemeIcon = (theme === "system" ? resolved : theme) === "dark" ? Moon : Sun;

  return (
    <div className="min-h-screen flex flex-col relative">
      <InteractiveBackground />
      {/* Navbar */}
      <nav className="sticky top-0 z-50 isolate border-b px-4 md:px-8 h-16 flex items-center justify-between bg-white/12 dark:bg-white/10 backdrop-blur-2xl backdrop-saturate-150 border-white/15 dark:border-white/15 shadow-[inset_0_1px_1px_rgba(255,255,255,0.08),0_10px_28px_rgba(0,0,0,0.18)]">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-background/22 via-background/14 to-background/8" />
        <div className="relative z-10 flex items-center gap-3">
          <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden min-w-[2.75rem] min-h-[2.75rem] flex items-center justify-center rounded-xl hover:bg-accent transition-colors">
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <h1 className="text-lg font-bold tracking-tight">
            <span className="text-primary">Motor</span>
            <span className="text-muted-foreground">Predict</span>
          </h1>
          {isMock && (
            <span className="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400 text-[10px] font-bold uppercase tracking-widest border border-amber-500/20">
              Mock
            </span>
          )}
        </div>

        <div className="relative z-10 hidden md:flex items-center gap-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2 px-4 py-2 min-h-[2.75rem] rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`
              }
            >
              <item.icon size={16} />
              {item.label}
            </NavLink>
          ))}
        </div>

        <div className="relative z-10 flex items-center gap-2">
          {user && <span className="text-xs text-muted-foreground hidden sm:block">{user.email}</span>}
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={cycleTheme}
            className="min-w-[2.75rem] min-h-[2.75rem] flex items-center justify-center rounded-xl hover:bg-accent transition-colors text-muted-foreground"
            title={`Theme: ${theme} (click to toggle light/dark)`}
          >
            <ThemeIcon size={18} />
          </motion.button>
          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={handleLogout}
            className="min-w-[2.75rem] min-h-[2.75rem] flex items-center justify-center rounded-xl hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
          >
            <LogOut size={18} />
          </motion.button>
        </div>
      </nav>

      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="md:hidden mx-4 mt-2 p-2 flex flex-col gap-1 rounded-2xl bg-white/10 backdrop-blur-2xl border border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_8px_32px_rgba(0,0,0,0.3)]"
        >
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 min-h-[2.75rem] rounded-xl text-sm font-medium transition-all ${
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground"
                }`
              }
            >
              <item.icon size={16} />
              {item.label}
            </NavLink>
          ))}
        </motion.div>
      )}

      <main className="flex-1 px-4 md:px-8 pb-4 md:pb-8 pt-6 md:pt-10 max-w-[1440px] mx-auto w-full">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        >
          <Outlet />
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="px-4 md:px-8 py-3 flex items-center justify-between border-t border-white/10 bg-white/5 backdrop-blur-sm">
        <span className="text-[10px] text-muted-foreground">MotorPredict © {new Date().getFullYear()}</span>
        {RUNTIME.isProductionLike ? (
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium bg-status-healthy/10 text-status-healthy border border-status-healthy/20">
            <Wifi size={12} />
            Live API
          </span>
        ) : (
          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={() => {
              setMock(!isMock);
              window.location.reload();
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
              isMock
                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                : "bg-status-healthy/10 text-status-healthy border border-status-healthy/20"
            }`}
            title={isMock ? "Switch to Live API" : "Switch to Mock Data"}
          >
            {isMock ? <FlaskConical size={12} /> : <Wifi size={12} />}
            {isMock ? "Mock Mode" : "Live API"}
          </motion.button>
        )}
      </footer>
    </div>
  );
};

export default AppLayout;
