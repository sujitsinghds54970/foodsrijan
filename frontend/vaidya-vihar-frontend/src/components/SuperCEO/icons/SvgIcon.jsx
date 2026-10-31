import { useId } from 'react';

export default function SvgIcon({ children, size = 24, title, gradient = false, ...props }) {
  const gradientId = useId().replace(/:/g, '');
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden={title ? undefined : true} role={title ? 'img' : undefined} {...props}>
      {title && <title>{title}</title>}
      {gradient && <defs><linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#D6A84F" /><stop offset="0.52" stopColor="#8C78F5" /><stop offset="1" stopColor="#57C7F2" /></linearGradient></defs>}
      <g stroke={gradient ? `url(#${gradientId})` : 'currentColor'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">{children}</g>
    </svg>
  );
}
