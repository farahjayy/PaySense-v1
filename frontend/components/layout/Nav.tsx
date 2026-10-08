"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "◫" },
  { href: "/transactions", label: "Transactions", icon: "⇄" },
  { href: "/plans", label: "BNPL Plans", icon: "▤" },
  { href: "/risk-checker", label: "Risk Checker", icon: "◎" },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname.startsWith(href);
}

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 hidden h-screen w-56 shrink-0 flex-col border-r border-line bg-surface px-4 py-6 md:flex">
      <Link href="/" className="mb-8 block px-2 text-lg font-bold tracking-tight text-ink">
        Pay<span className="text-accent">Sense</span>
      </Link>
      <nav aria-label="Main navigation" className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors ${
                active
                  ? "bg-accent-bg font-semibold text-accent"
                  : "text-ink-secondary hover:bg-surface-2 hover:text-ink"
              }`}
            >
              <span aria-hidden className="text-sm">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <p className="mt-auto px-2 text-[10px] leading-relaxed text-ink-muted">
        AI financial copilot for BNPL-aware budgeting · FYP demo
      </p>
    </aside>
  );
}

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Main navigation"
      className="fixed inset-x-0 bottom-0 z-40 flex border-t border-line bg-surface md:hidden"
    >
      {NAV_ITEMS.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] font-medium ${
              active ? "text-accent" : "text-ink-muted"
            }`}
          >
            <span aria-hidden className="text-base leading-none">{item.icon}</span>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
