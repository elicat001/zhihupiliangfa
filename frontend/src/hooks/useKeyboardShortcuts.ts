import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Global keyboard shortcuts hook
 *
 * Shortcuts:
 * - Alt+1: Navigate to Dashboard
 * - Alt+2: Navigate to Article Generate
 * - Alt+3: Navigate to Article List
 * - Alt+4: Navigate to Task Schedule
 * - Alt+5: Navigate to Publish History
 * - Alt+6: Navigate to Account Manage
 * - Alt+7: Navigate to Settings
 * - Alt+R: Refresh current page (re-render)
 */
export function useKeyboardShortcuts() {
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't trigger when typing in inputs
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      if (e.altKey) {
        switch (e.key) {
          case '1': e.preventDefault(); navigate('/'); break;
          case '2': e.preventDefault(); navigate('/generate'); break;
          case '3': e.preventDefault(); navigate('/articles'); break;
          case '4': e.preventDefault(); navigate('/tasks'); break;
          case '5': e.preventDefault(); navigate('/history'); break;
          case '6': e.preventDefault(); navigate('/accounts'); break;
          case '7': e.preventDefault(); navigate('/settings'); break;
        }
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [navigate]);
}
