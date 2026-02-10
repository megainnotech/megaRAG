import React, { useState, createContext, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import SearchPage from '@/pages/SearchPage';
import InputPage from '@/pages/InputPage';
import RetrievePage from '@/pages/RetrievePage';
import ConfigPage from '@/pages/ConfigPage';
import { Toaster } from '@/components/ui/sonner';

// Export ThemeContext so other components can use it
export const ThemeContext = createContext();

function App() {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      <Router>
        <AppLayout>
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/input" element={<InputPage />} />
            <Route path="/retrieve" element={<RetrievePage />} />
            <Route path="/config" element={<ConfigPage />} />
          </Routes>
        </AppLayout>
        <Toaster />
      </Router>
    </ThemeContext.Provider>
  );
}

export default App;
