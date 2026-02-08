import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiFetch } from '../config/api';

const LegislaturaContext = createContext();

export const useLegislatura = () => {
  const context = useContext(LegislaturaContext);
  if (!context) {
    throw new Error('useLegislatura must be used within a LegislaturaProvider');
  }
  return context;
};

export const LegislaturaProvider = ({ children }) => {
  const [selectedLegislatura, setSelectedLegislatura] = useState(null);
  const [legislaturas, setLegislaturas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLegislaturas();
  }, []);

  const fetchLegislaturas = async () => {
    try {
      const response = await apiFetch('legislaturas');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const text = await response.text();

      let data;
      try {
        data = JSON.parse(text);
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        console.error('Response text:', text);
        throw new Error(`Invalid JSON response: ${parseError.message}`);
      }
      
      setLegislaturas(data);
      
      // Set the active legislatura as default, or the first one if none is active
      const activeLegislatura = data.find(leg => leg.ativa);
      if (activeLegislatura) {
        setSelectedLegislatura(activeLegislatura);
      } else if (data.length > 0) {
        setSelectedLegislatura(data[0]);
      }
    } catch (error) {
      console.error('Erro ao carregar legislaturas:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectLegislatura = (legislatura) => {
    setSelectedLegislatura(legislatura);
  };

  const value = {
    selectedLegislatura,
    legislaturas,
    loading,
    selectLegislatura
  };

  return (
    <LegislaturaContext.Provider value={value}>
      {children}
    </LegislaturaContext.Provider>
  );
};