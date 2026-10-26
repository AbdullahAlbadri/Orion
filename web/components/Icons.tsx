// Simple line icons (24px grid, currentColor) so the UI needs no icon library.
import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;
const base = (props: P) => ({
  width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true, ...props,
});

export const HomeIcon = (p: P) => (<svg {...base(p)}><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V20h5v-6h4v6h5V9.5" /></svg>);
export const BoxIcon = (p: P) => (<svg {...base(p)}><path d="M3 7.5 12 3l9 4.5v9L12 21l-9-4.5z" /><path d="M3 7.5 12 12l9-4.5M12 12v9" /></svg>);
export const PlusIcon = (p: P) => (<svg {...base(p)}><path d="M12 5v14M5 12h14" /></svg>);
export const GlobeIcon = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9s1.3-6.4 3.8-9z" /></svg>);
export const LogoutIcon = (p: P) => (<svg {...base(p)}><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" /><path d="M10 17l-5-5 5-5M5 12h11" /></svg>);
export const ChatIcon = (p: P) => (<svg {...base(p)}><path d="M4 5h16v11H9l-5 4z" /></svg>);
export const FactoryIcon = (p: P) => (<svg {...base(p)}><path d="M3 21V10l6 3.5V10l6 3.5V6l6-3v18z" /><path d="M7 17h2M12 17h2M17 17h2" /></svg>);
export const ClockIcon = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>);
export const CheckIcon = (p: P) => (<svg {...base(p)}><path d="M5 12.5 10 17l9-10" /></svg>);
export const ShirtIcon = (p: P) => (<svg {...base(p)}><path d="M8 3 3 6l2 4 2-1v12h10V9l2 1 2-4-5-3c0 1.7-1.8 3-4 3S8 4.7 8 3z" /></svg>);
export const BellIcon = (p: P) => (<svg {...base(p)}><path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4z" /><path d="M10 20a2 2 0 0 0 4 0" /></svg>);
export const ArrowIcon = (p: P) => (<svg {...base(p)}><path d="M5 12h14M13 6l6 6-6 6" /></svg>);
export const PaletteIcon = (p: P) => (<svg {...base(p)}><path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.6-.8 1.6-1.6 0-1.2-1-1.5-1-2.6 0-.9.7-1.6 1.6-1.6H17a4 4 0 0 0 4-4C21 6.6 17 3 12 3z" /><circle cx="7.5" cy="11" r="1" /><circle cx="10" cy="7" r="1" /><circle cx="15" cy="7.5" r="1" /></svg>);
export const NeedleIcon = (p: P) => (<svg {...base(p)}><path d="M20 4 7 17M17 4h3v3" /><path d="M7 17c-1.5 1.5-3 2-4 1s-.5-2.5 1-4" /></svg>);
export const TargetIcon = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></svg>);
export const ImageIcon = (p: P) => (<svg {...base(p)}><rect x="3" y="4" width="18" height="16" rx="3" /><circle cx="9" cy="10" r="2" /><path d="m21 16-5-5-9 9" /></svg>);
export const LayersIcon = (p: P) => (<svg {...base(p)}><path d="m12 3 9 5-9 5-9-5z" /><path d="m3 13 9 5 9-5" /></svg>);
export const ScaleIcon = (p: P) => (<svg {...base(p)}><path d="M6 20h12l-2-12H8z" /><path d="M9 8a3 3 0 0 1 6 0" /></svg>);
export const RulerIcon = (p: P) => (<svg {...base(p)}><rect x="2.5" y="8" width="19" height="8" rx="2" /><path d="M6.5 8v3M10.5 8v4M14.5 8v3M18.5 8v4" /></svg>);
export const HashIcon = (p: P) => (<svg {...base(p)}><path d="M5 9h15M4 15h15M10 3 8 21M16 3l-2 18" /></svg>);
export const TagIcon = (p: P) => (<svg {...base(p)}><path d="M3 12V4h8l10 10-8 8z" /><circle cx="7.5" cy="8" r="1.3" /></svg>);
export const SparkleIcon = (p: P) => (<svg {...base(p)}><path d="M12 3c.6 3.7 2.3 5.4 6 6-3.7.6-5.4 2.3-6 6-.6-3.7-2.3-5.4-6-6 3.7-.6 5.4-2.3 6-6z" /><path d="M19 15c.3 1.6 1 2.3 2.5 2.5-1.5.3-2.2 1-2.5 2.5-.3-1.5-1-2.2-2.5-2.5 1.5-.2 2.2-.9 2.5-2.5z" /></svg>);
export const ShieldIcon = (p: P) => (<svg {...base(p)}><path d="M12 3 4 6v6c0 4.5 3.4 8 8 9 4.6-1 8-4.5 8-9V6z" /><path d="m9 12 2 2 4-4" /></svg>);
export const StepsIcon = (p: P) => (<svg {...base(p)}><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M9 4v16" /></svg>);
export const ListIcon = (p: P) => (<svg {...base(p)}><path d="M9 6h11M9 12h11M9 18h11" /><circle cx="4.5" cy="6" r="1" /><circle cx="4.5" cy="12" r="1" /><circle cx="4.5" cy="18" r="1" /></svg>);
export const ArrowNEIcon = (p: P) => (<svg {...base(p)} className={`arrow-ne ${p.className ?? ""}`}><path d="M7 17 17 7M9 7h8v8" /></svg>);
export const LightbulbIcon = (p: P) => (<svg {...base(p)}><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z" /></svg>);
export const BookIcon = (p: P) => (<svg {...base(p)}><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z" /><path d="M4 21V5M8 7h7" /></svg>);
export const HeartIcon = (p: P) => (<svg {...base(p)}><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" /></svg>);
export const ChevronIcon = (p: P) => (<svg {...base(p)}><path d="m6 9 6 6 6-6" /></svg>);
export const SendIcon = (p: P) => (<svg {...base(p)}><path d="M21 3 10 14M21 3l-7 18-4-7-7-4z" /></svg>);
export const LockIcon = (p: P) => (<svg {...base(p)}><rect x="5" y="11" width="14" height="10" rx="2.5" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>);
export const UsersIcon = (p: P) => (<svg {...base(p)}><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5" /><path d="M16 4.8a3.5 3.5 0 0 1 0 6.4M18 14.8c2 .7 3.2 2.4 3.5 5.2" /></svg>);
export const ReplayIcon = (p: P) => (<svg {...base(p)}><path d="M4 12a8 8 0 1 0 2.4-5.7L4 8.6" /><path d="M4 4v4.6h4.6" /></svg>);
export const MenuIcon = (p: P) => (<svg {...base(p)}><path d="M4 7h16M4 12h16M4 17h16" /></svg>);
export const CloseIcon = (p: P) => (<svg {...base(p)}><path d="M6 6l12 12M18 6 6 18" /></svg>);
export const TruckIcon = (p: P) => (<svg {...base(p)}><path d="M2.5 6h11v10h-11zM13.5 9.5h4l3 3.5V16h-7z" /><circle cx="6.5" cy="17.5" r="1.8" /><circle cx="17" cy="17.5" r="1.8" /></svg>);
export const CardIcon = (p: P) => (<svg {...base(p)}><rect x="3" y="5.5" width="18" height="13" rx="2.5" /><path d="M3 10h18M7 15h3" /></svg>);
export const ChartIcon = (p: P) => (<svg {...base(p)}><path d="M4 20V10M10 20V4M16 20v-7M21 20H3" /></svg>);
export const GearIcon = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="3" /><path d="M12 2.5v3M12 18.5v3M4.2 6.2l2.1 2.1M17.7 15.7l2.1 2.1M2.5 12h3M18.5 12h3M4.2 17.8l2.1-2.1M17.7 8.3l2.1-2.1" /></svg>);
export const InfoIcon = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7.5h.01" /></svg>);
export const HelpIcon = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9" /><path d="M9.5 9.5a2.5 2.5 0 1 1 3.4 2.3c-.6.3-.9.8-.9 1.4v.6M12 17h.01" /></svg>);
export const UserIcon = (p: P) => (<svg {...base(p)}><circle cx="12" cy="8" r="4" /><path d="M4 21c.8-4 4-6 8-6s7.2 2 8 6" /></svg>);
export const SearchIcon = (p: P) => (<svg {...base(p)}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>);
export const DownloadIcon = (p: P) => (<svg {...base(p)}><path d="M12 4v11M7 10l5 5 5-5M4 20h16" /></svg>);
export const PrinterIcon = (p: P) => (<svg {...base(p)}><path d="M7 9V3h10v6M7 17H4v-7h16v7h-3" /><path d="M7 14h10v7H7z" /></svg>);
export const CopyIcon = (p: P) => (<svg {...base(p)}><rect x="8" y="8" width="12" height="12" rx="2" /><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3" /></svg>);
export const PinIcon = (p: P) => (<svg {...base(p)}><path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.5" /></svg>);
export const BuildingIcon = (p: P) => (<svg {...base(p)}><path d="M4 21V5l8-2v18M12 8h8v13M2 21h20M8 8v.01M8 12v.01M8 16v.01M16 12v.01M16 16v.01" /></svg>);
export const FileIcon = (p: P) => (<svg {...base(p)}><path d="M6 3h8l5 5v13H6z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></svg>);
export const ArchiveIcon = (p: P) => (<svg {...base(p)}><rect x="3" y="4" width="18" height="5" rx="1.5" /><path d="M5 9v11h14V9M10 13h4" /></svg>);
export const MailIcon = (p: P) => (<svg {...base(p)}><rect x="3" y="5" width="18" height="14" rx="2.5" /><path d="m4 7 8 6 8-6" /></svg>);
export const PlaneIcon = (p: P) => (<svg {...base(p)}><path d="M2.5 13.5 20.6 8.6c1-.3 1.6 1 .7 1.5L8 17.2l-3.6-1.1z" /><path d="M9.5 10.6 6.5 5H9l5.4 4.2M3 21h18" /></svg>);
