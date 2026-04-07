import React from "react";
import GlassCard from "@/components/GlassCard";
import { motion } from "framer-motion";
import { FaGithub } from "react-icons/fa";
import { Cpu, Database, Brain, Wifi, Shield, BarChart3 } from "lucide-react";

const features = [
  { icon: Cpu, title: "Motor Monitoring", desc: "Real-time sensor data ingestion from industrial motors" },
  { icon: Brain, title: "AI Predictions", desc: "Machine learning models for predictive failure analysis" },
  { icon: Wifi, title: "Live Streaming", desc: "Server-Sent Events for near real-time dashboard updates" },
  { icon: Database, title: "Data Pipeline", desc: "Efficient time-series storage and historical analysis" },
  { icon: Shield, title: "Alert System", desc: "Intelligent alerting with severity classification" },
  { icon: BarChart3, title: "Fleet Analytics", desc: "Comprehensive fleet-wide health insights and trends" },
];

const AboutPage: React.FC = () => {
  return (
    <div className="space-y-12 max-w-4xl mx-auto">
      {/* Hero */}
      <div className="text-center py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
            <Cpu size={16} /> Motor Failure Prediction System
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-tight">
            Predict. Prevent.
            <br />
            <span className="text-primary">Protect.</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
            An intelligent industrial monitoring platform that leverages machine learning
            to predict motor failures before they happen, reducing downtime and maintenance costs.
          </p>
          <motion.a
            href="https://github.com/hauX609/Motor-Failure-Fullstack"
            target="_blank"
            rel="noopener noreferrer"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            className="inline-flex items-center gap-3 px-6 py-3 rounded-xl bg-foreground text-background font-semibold text-sm hover:opacity-90 transition-opacity"
          >
            <FaGithub size={20} />
            View on GitHub
          </motion.a>
        </motion.div>
      </div>

      {/* Architecture Features */}
      <div>
        <h2 className="text-xl font-bold mb-6 text-center">System Architecture</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <GlassCard hover className="h-full">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-3">
                  <f.icon size={18} className="text-primary" />
                </div>
                <h3 className="font-semibold mb-1">{f.title}</h3>
                <p className="text-sm text-muted-foreground">{f.desc}</p>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Tech Stack */}
      <GlassCard>
        <h2 className="text-lg font-bold mb-4">Technology Stack</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {["React + TypeScript", "FastAPI + Python", "PostgreSQL", "Scikit-learn / TensorFlow", "SSE Live Streaming", "Recharts", "Tailwind CSS", "React Query"].map((tech) => (
            <div key={tech} className="px-3 py-2 rounded-xl bg-accent text-sm text-center font-medium">{tech}</div>
          ))}
        </div>
      </GlassCard>

      <div className="text-center py-6 text-sm text-muted-foreground">
        Built with precision for industrial reliability
      </div>
    </div>
  );
};

export default AboutPage;
