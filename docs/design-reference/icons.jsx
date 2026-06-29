// Tiny inline SVG icon set — 14px stroke icons used throughout.
const I = (path, opts = {}) => (props) => {
  const { size = 14, stroke = 1.5, fill = "none", ...rest } = props || {};
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke="currentColor"
         strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" {...rest}>
      {path}
    </svg>
  );
};

const Icon = {
  Home: I(<><path d="M3 11l9-8 9 8" /><path d="M5 10v10h14V10" /></>),
  News: I(<><rect x="3" y="4" width="18" height="16" rx="1.5" /><path d="M7 8h10M7 12h10M7 16h6" /></>),
  Shield: I(<><path d="M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3z" /><path d="M9 12l2 2 4-4" /></>),
  Beaker: I(<><path d="M9 3v6L4 18a2 2 0 002 3h12a2 2 0 002-3l-5-9V3" /><path d="M9 3h6" /></>),
  Chart: I(<><path d="M3 3v18h18" /><path d="M7 14l4-4 3 3 5-6" /></>),
  Globe: I(<><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18" /></>),
  Target: I(<><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" fill="currentColor" /></>),
  Pen: I(<><path d="M4 20l4-1 11-11-3-3L5 16l-1 4z" /></>),
  Send: I(<><path d="M22 2L11 13" /><path d="M22 2l-7 20-4-9-9-4 20-7z" /></>),
  Zap: I(<path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" />),
  Bar: I(<><path d="M3 21h18" /><path d="M7 17V9M12 17V5M17 17v-6" /></>),
  Book: I(<><path d="M4 4h12a3 3 0 013 3v14H7a3 3 0 01-3-3V4z" /><path d="M4 4v13a3 3 0 003 3" /></>),
  Cpu: I(<><rect x="5" y="5" width="14" height="14" rx="1.5" /><rect x="9" y="9" width="6" height="6" /><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" /></>),
  Users: I(<><circle cx="9" cy="8" r="3.5" /><path d="M2 21c.5-4 3.5-6 7-6s6.5 2 7 6" /><circle cx="17" cy="9" r="2.5" /><path d="M16 15c3 0 5.5 1.5 6 5" /></>),
  Cog: I(<><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z" /></>),
  Inbox: I(<><path d="M22 12h-6l-2 3h-4l-2-3H2" /><path d="M5.5 5h13l3.5 7v6a2 2 0 01-2 2H4a2 2 0 01-2-2v-6L5.5 5z" /></>),
  Search: I(<><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.5-4.5" /></>),
  Bell: I(<><path d="M6 9a6 6 0 0112 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10 21a2 2 0 004 0" /></>),
  ChevDown: I(<path d="M6 9l6 6 6-6" />),
  ChevRight: I(<path d="M9 6l6 6-6 6" />),
  Plus: I(<><path d="M12 5v14M5 12h14" /></>),
  Dot: I(<circle cx="12" cy="12" r="4" fill="currentColor" />),
  Sparkles: I(<><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" /></>),
  Flag: I(<><path d="M4 22V4" /><path d="M4 4h14l-3 5 3 5H4" /></>),
  Check: I(<path d="M5 12l4 4L19 6" />),
  X: I(<><path d="M6 6l12 12M18 6L6 18" /></>),
  Filter: I(<path d="M3 5h18l-7 9v6l-4-2v-4L3 5z" />),
  Calendar: I(<><rect x="3" y="5" width="18" height="16" rx="1.5" /><path d="M3 10h18M8 3v4M16 3v4" /></>),
  Lock: I(<><rect x="4" y="11" width="16" height="10" rx="1.5" /><path d="M8 11V7a4 4 0 018 0v4" /></>),
  Eye: I(<><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" /><circle cx="12" cy="12" r="3" /></>),
  Mail: I(<><rect x="3" y="5" width="18" height="14" rx="1.5" /><path d="M3 7l9 7 9-7" /></>),
  Rss: I(<><path d="M4 11a9 9 0 019 9M4 4a16 16 0 0116 16" /><circle cx="5" cy="19" r="1.5" fill="currentColor" /></>),
  Webhook: I(<><circle cx="6" cy="18" r="3" /><circle cx="18" cy="18" r="3" /><circle cx="12" cy="6" r="3" /><path d="M9 18h6M12 9l-3 6M15 15l-3-6" /></>),
  Download: I(<><path d="M12 3v12" /><path d="M7 10l5 5 5-5" /><path d="M3 21h18" /></>),
  Upload: I(<><path d="M12 21V9" /><path d="M7 14l5-5 5 5" /><path d="M3 3h18" /></>),
  Play: I(<path d="M6 4l14 8-14 8V4z" fill="currentColor" />),
  Code: I(<><path d="M8 6l-5 6 5 6M16 6l5 6-5 6M14 4l-4 16" /></>),
  Layers: I(<><path d="M12 3l9 5-9 5-9-5 9-5z" /><path d="M3 13l9 5 9-5M3 18l9 5 9-5" /></>),
};

Object.assign(window, { Icon, I });
