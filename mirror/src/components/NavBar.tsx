'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const TABS = [
  { href: '/', label: 'Home', icon: '◎' },
  { href: '/capture', label: 'Capture', icon: '⊙' },
  { href: '/compare', label: 'Compare', icon: '◧' },
  { href: '/log', label: 'Log', icon: '✎' },
  { href: '/stack', label: 'Stack', icon: '☰' },
];

export function NavBar() {
  const pathname = usePathname();
  // Hide the tab bar on auth screens.
  if (pathname.startsWith('/login') || pathname.startsWith('/auth')) return null;

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-edge bg-panel/95 backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-stretch justify-around">
        {TABS.map((tab) => {
          const active =
            tab.href === '/' ? pathname === '/' : pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] ${
                active ? 'text-accent' : 'text-mute'
              }`}
            >
              <span className="text-lg leading-none">{tab.icon}</span>
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
