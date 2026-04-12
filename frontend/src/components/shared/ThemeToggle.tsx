/**
 * ThemeToggle — Moon/Sun icon toggle for dark/light mode.
 */
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';

interface Props {
  className?: string;
}

export default function ThemeToggle({ className }: Props) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      className={`theme-toggle ${className || ''}`}
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
