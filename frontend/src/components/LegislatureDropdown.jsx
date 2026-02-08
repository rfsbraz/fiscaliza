import React, { useState, useEffect } from 'react';
import { ChevronDown, Calendar } from 'lucide-react';
import { apiFetch } from '../config/api';

/**
 * Reusable Legislature Dropdown Component
 * 
 * Features:
 * - Fetches available legislatures from API
 * - When deputyCadId provided: Shows only legislatures where deputy served
 * - When deputyCadId not provided: Shows all available legislatures  
 * - Defaults to current/most recent legislature
 * - Handles loading and error states
 * - Clean, consistent UI design
 * 
 * @param {string} selectedLegislature - Currently selected legislature
 * @param {function} onLegislatureChange - Callback when selection changes
 * @param {number} deputyCadId - Optional deputy ID to filter served legislatures
 * @param {string} className - Additional CSS classes
 * @param {string} size - Size variant: "sm", "default", "lg"
 */
const LegislatureDropdown = ({ 
  selectedLegislature, 
  onLegislatureChange, 
  deputyCadId = null,
  className = "",
  size = "default" // "sm", "default", "lg"
}) => {
  const [legislatures, setLegislatures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Size variants
  const sizeClasses = {
    sm: "px-2 py-1 text-xs",
    default: "px-3 py-2 text-sm", 
    lg: "px-4 py-3 text-base"
  };

  const iconSizes = {
    sm: "h-3 w-3",
    default: "h-4 w-4",
    lg: "h-5 w-5"
  };

  useEffect(() => {
    fetchLegislatures();
  }, [deputyCadId]);

  const fetchLegislatures = async () => {
    try {
      setLoading(true);
      
      let legislaturesToShow = [];
      
      if (deputyCadId) {
        // Fetch deputy-specific legislatures from deputy details
        const deputyResponse = await apiFetch(`deputados/${deputyCadId}/detalhes`);
        
        if (!deputyResponse.ok) {
          throw new Error(`HTTP ${deputyResponse.status}: ${deputyResponse.statusText}`);
        }
        
        const deputyData = await deputyResponse.json();
        
        if (deputyData.error) {
          throw new Error(deputyData.error);
        }

        // Extract served legislatures from mandatos_historico
        if (deputyData.mandatos_historico && deputyData.mandatos_historico.length > 0) {
          legislaturesToShow = deputyData.mandatos_historico.map(mandate => ({
            numero: mandate.legislatura_numero,
            designacao: mandate.legislatura_nome,
            data_inicio: mandate.mandato_inicio,
            data_fim: mandate.mandato_fim,
            is_current: mandate.is_current
          }));
        }
      } else {
        // Fetch all legislatures if no specific deputy
        const response = await apiFetch('legislaturas');
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
          throw new Error(data.error);
        }

        legislaturesToShow = data.legislatures || data.legislaturas || [];
      }

      // Sort legislatures by number (descending - most recent first)
      const sortedLegislatures = legislaturesToShow.sort((a, b) => {
        // Convert roman numerals to numbers for proper sorting
        const romanToNumber = (roman) => {
          const map = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000,
            'IV': 4, 'IX': 9, 'XL': 40, 'XC': 90, 'CD': 400, 'CM': 900
          };
          let result = 0;
          for (let i = 0; i < roman.length; i++) {
            const current = map[roman.slice(i, i + 2)] || map[roman[i]];
            const next = map[roman[i + 1]];
            if (current < next) {
              result += next - current;
              i++;
            } else {
              result += current;
            }
          }
          return result;
        };

        const aNum = romanToNumber(a.numero);
        const bNum = romanToNumber(b.numero);
        return bNum - aNum; // Descending order
      });

      setLegislatures(sortedLegislatures);

      // Set current legislature as default if no selection made
      if (!selectedLegislature && sortedLegislatures.length > 0) {
        const currentLeg = sortedLegislatures.find(leg => 
          leg.data_fim === null || leg.data_fim === undefined || leg.is_current === true
        );
        const defaultLeg = currentLeg || sortedLegislatures[0];
        onLegislatureChange(defaultLeg.numero);
      }
      
    } catch (err) {
      console.error('Error fetching legislatures:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (event) => {
    const newLegislature = event.target.value;
    onLegislatureChange(newLegislature);
  };

  // Show loading state
  if (loading) {
    return (
      <div className={`inline-flex items-center ${sizeClasses[size]} bg-gray-100 border border-gray-200 rounded-md ${className}`}>
        <Calendar className={`${iconSizes[size]} text-gray-400 mr-2`} />
        <span className="text-gray-500">Carregando...</span>
        <div className="ml-2 animate-spin">
          <ChevronDown className={iconSizes[size]} />
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className={`inline-flex items-center ${sizeClasses[size]} bg-red-50 border border-red-200 rounded-md ${className}`}>
        <Calendar className={`${iconSizes[size]} text-red-400 mr-2`} />
        <span className="text-red-600 text-xs">Erro ao carregar legislaturas</span>
      </div>
    );
  }

  // Show empty state
  if (legislatures.length === 0) {
    return (
      <div className={`inline-flex items-center ${sizeClasses[size]} bg-gray-100 border border-gray-200 rounded-md ${className}`}>
        <Calendar className={`${iconSizes[size]} text-gray-400 mr-2`} />
        <span className="text-gray-500">Nenhuma legislatura disponível</span>
      </div>
    );
  }

  return (
    <div className={`relative inline-block ${className}`}>
      <div className="relative">
        <select
          value={selectedLegislature || ''}
          onChange={handleChange}
          className={`
            ${sizeClasses[size]}
            appearance-none bg-white border border-gray-300 rounded-md shadow-sm
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            hover:border-gray-400 transition-colors duration-200
            pr-8 cursor-pointer
          `}
          aria-label="Selecionar Legislatura"
        >
          {legislatures.map((legislature) => {
            const isCurrent = legislature.data_fim === null || legislature.data_fim === undefined || legislature.is_current === true;
            const startYear = legislature.data_inicio ? new Date(legislature.data_inicio).getFullYear() : '';
            const endYear = legislature.data_fim ? new Date(legislature.data_fim).getFullYear() : '';
            const yearRange = startYear ? `(${startYear}${endYear ? `-${endYear}` : '-atual'})` : '';
            
            return (
              <option key={legislature.numero} value={legislature.numero}>
                {legislature.numero}ª Leg. {yearRange} {isCurrent ? '• Atual' : ''}
              </option>
            );
          })}
        </select>
        
        {/* Custom dropdown icon */}
        <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
          <Calendar className={`${iconSizes[size]} text-gray-400 mr-1`} />
          <ChevronDown className={`${iconSizes[size]} text-gray-400`} />
        </div>
      </div>
    </div>
  );
};

export default LegislatureDropdown;