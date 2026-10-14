import type { CSSProperties } from 'react';

interface IconProps {
  size?: number;
  style?: CSSProperties;
  className?: string;
}

const base = (size: number): CSSProperties => ({
  width: size, height: size, display: 'block', flex: '0 0 auto',
});

export const PlusIcon = ({ size = 18, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const SendIcon = ({ size = 18, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const CopyIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.8" />
    <path d="M5 15V5a2 2 0 0 1 2-2h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

export const DownloadIcon = ({ size = 17, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M12 4v11m0 0 4.5-4.5M12 15l-4.5-4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M4.5 19.5h15" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

export const ThumbUpIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M7 11v9H4a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1h3Zm0 0 4-7a2 2 0 0 1 2 2v3h5a2 2 0 0 1 2 2.3l-1 6A2 2 0 0 1 17 20H7" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
  </svg>
);

export const ThumbDownIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M17 13V4h3a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1h-3Zm0 0-4 7a2 2 0 0 1-2-2v-3H6a2 2 0 0 1-2-2.3l1-6A2 2 0 0 1 7 4h10" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
  </svg>
);

export const RefreshIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M4 12a8 8 0 0 1 13.7-5.6L20 8M20 4v4h-4M20 12a8 8 0 0 1-13.7 5.6L4 16M4 20v-4h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const SearchIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
    <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

export const BrainIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-1 5.8A3 3 0 0 0 7 18a3 3 0 0 0 5 1V5a3 3 0 0 0-3-1Zm6 0a3 3 0 0 1 3 3 3 3 0 0 1 1 5.8A3 3 0 0 1 17 18a3 3 0 0 1-5 1" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
  </svg>
);

export const SidebarIcon = ({ size = 18, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.8" />
    <path d="M9 4v16" stroke="currentColor" strokeWidth="1.8" />
  </svg>
);

export const PanelIcon = ({ size = 18, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.8" />
    <path d="M15 4v16" stroke="currentColor" strokeWidth="1.8" />
  </svg>
);

export const SunIcon = ({ size = 18, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8" />
    <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

export const MoonIcon = ({ size = 18, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M20 14.5A8 8 0 0 1 9.5 4 7 7 0 1 0 20 14.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
  </svg>
);

export const CheckIcon = ({ size = 12, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="m5 12 5 5 9-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const ChevronDownIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const NewChatIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M4 5h16v11H8l-4 4V5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <path d="M12 9v4M10 11h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

export const ShieldIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M12 3 5 6v6c0 4 3 6.5 7 9 4-2.5 7-5 7-9V6l-7-3Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
  </svg>
);

export const GearIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.7" />
    <path d="M12 3.5v2.2M12 18.3v2.2M20.5 12h-2.2M5.7 12H3.5M17.9 6.1l-1.6 1.6M7.7 16.3l-1.6 1.6M17.9 17.9l-1.6-1.6M7.7 7.7 6.1 6.1"
      stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
  </svg>
);

export const PlugIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M9 7V4M15 7V4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <path d="M7 7h10v4a5 5 0 0 1-5 5 5 5 0 0 1-5-5V7Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    <path d="M12 16v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

export const FolderIcon = ({ size = 16, style, className }: IconProps) => (
  <svg viewBox="0 0 24 24" fill="none" style={{ ...base(size), ...style }} className={className}>
    <path d="M3.5 6.5A1.5 1.5 0 0 1 5 5h4l2 2.5h8a1.5 1.5 0 0 1 1.5 1.5v9A1.5 1.5 0 0 1 19 19.5H5A1.5 1.5 0 0 1 3.5 18V6.5Z"
      stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
  </svg>
);
