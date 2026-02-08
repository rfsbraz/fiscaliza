import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';

/**
 * Navigation - Data Observatory Style
 *
 * Editorial, authoritative navigation inspired by ProPublica/Guardian data journalism.
 * Clean typography, minimal decoration, green underline active state.
 */
const Navigation = () => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Panorama' },
    { path: '/deputados', label: 'Deputados' },
    { path: '/partidos', label: 'Partidos' },
    { path: '/agenda', label: 'Agenda' },
    { path: '/transparencia', label: 'Transparência' },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <nav
      style={{
        backgroundColor: '#FFFFFF',
        borderBottom: '1px solid #E5E5E5',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      <div
        style={{
          maxWidth: '1280px',
          margin: '0 auto',
          padding: '0 1.5rem',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: '64px',
          }}
        >
          {/* Logo */}
          <Link
            to="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              textDecoration: 'none',
            }}
          >
            {/* Logo mark */}
            <div
              style={{
                width: '32px',
                height: '32px',
                backgroundColor: '#1B4332',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M3 21h18" />
                <path d="M5 21V7l8-4v18" />
                <path d="M19 21V11l-6-4" />
                <path d="M9 9v.01" />
                <path d="M9 12v.01" />
                <path d="M9 15v.01" />
                <path d="M9 18v.01" />
              </svg>
            </div>
            {/* Logo text */}
            <span
              style={{
                fontFamily: "'Libre Baskerville', Georgia, serif",
                fontSize: '1.375rem',
                fontWeight: 700,
                color: '#1A1A1A',
                letterSpacing: '-0.01em',
              }}
            >
              Fiscaliza
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
            className="nav-desktop"
          >
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  position: 'relative',
                  padding: '0.5rem 1rem',
                  fontFamily: "'Source Sans 3', sans-serif",
                  fontSize: '0.9375rem',
                  fontWeight: isActive(item.path) ? 600 : 500,
                  color: isActive(item.path) ? '#1B4332' : '#4A4A4A',
                  textDecoration: 'none',
                  transition: 'color 150ms ease',
                }}
                onMouseEnter={(e) => {
                  if (!isActive(item.path)) {
                    e.target.style.color = '#1B4332';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive(item.path)) {
                    e.target.style.color = '#4A4A4A';
                  }
                }}
              >
                {item.label}
                {/* Active underline */}
                {isActive(item.path) && (
                  <span
                    style={{
                      position: 'absolute',
                      bottom: '0',
                      left: '1rem',
                      right: '1rem',
                      height: '2px',
                      backgroundColor: '#1B4332',
                    }}
                  />
                )}
              </Link>
            ))}
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="nav-mobile-toggle"
            style={{
              display: 'none',
              padding: '0.5rem',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#4A4A4A',
            }}
            aria-label={isOpen ? 'Fechar menu' : 'Abrir menu'}
          >
            {isOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div
            className="nav-mobile"
            style={{
              display: 'none',
              paddingBottom: '1rem',
              borderTop: '1px solid #E5E5E5',
            }}
          >
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                style={{
                  display: 'block',
                  padding: '0.875rem 0',
                  fontFamily: "'Source Sans 3', sans-serif",
                  fontSize: '1rem',
                  fontWeight: isActive(item.path) ? 600 : 400,
                  color: isActive(item.path) ? '#1B4332' : '#4A4A4A',
                  textDecoration: 'none',
                  borderBottom: '1px solid #F5F5F5',
                }}
              >
                {isActive(item.path) && (
                  <span
                    style={{
                      display: 'inline-block',
                      width: '3px',
                      height: '1rem',
                      backgroundColor: '#1B4332',
                      marginRight: '0.75rem',
                      verticalAlign: 'middle',
                    }}
                  />
                )}
                {item.label}
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Responsive styles */}
      <style>{`
        @media (max-width: 768px) {
          .nav-desktop {
            display: none !important;
          }
          .nav-mobile-toggle {
            display: block !important;
          }
          .nav-mobile {
            display: block !important;
          }
        }
      `}</style>
    </nav>
  );
};

export default Navigation;
