import React, { createContext, useContext, useState, useEffect } from "react";
import { RUNTIME } from "@/lib/runtime";

interface MockState {
  isMock: boolean;
  setMock: (v: boolean) => void;
}

const MockContext = createContext<MockState>({ isMock: false, setMock: () => {} });

export const useMock = () => useContext(MockContext);

const ENV_FLAG = RUNTIME.enableMock;

export const MockProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isMock, setMock] = useState(() => {
    if (!RUNTIME.enableMock) return false;
    const stored = localStorage.getItem("mock_mode");
    return stored !== null ? stored === "true" : ENV_FLAG;
  });

  useEffect(() => {
    if (!RUNTIME.enableMock && isMock) {
      setMock(false);
    }
    if (!RUNTIME.enableMock) {
      localStorage.setItem("mock_mode", "false");
    }
  }, [isMock]);

  useEffect(() => {
    localStorage.setItem("mock_mode", String(isMock));
  }, [isMock]);

  const safeSetMock = (v: boolean) => {
    if (!RUNTIME.enableMock) {
      setMock(false);
      localStorage.setItem("mock_mode", "false");
      return;
    }
    setMock(v);
  };

  return (
    <MockContext.Provider value={{ isMock, setMock: safeSetMock }}>
      {children}
    </MockContext.Provider>
  );
};
