"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { translate, type NavKey } from "@/lib/i18n";
import { useWorkspace } from "@/lib/workspace/store";
import type { Language, Role } from "@/lib/workspace/types";

import { FloatingChatbot } from "./floating-chatbot";
import { Icon, type IconName } from "./ui";

interface NavItem {
  href: string;
  key: NavKey;
  icon: IconName;
  roles?: Role[];
  badge?: "queue" | "reviews";
}

interface NavGroup {
  key: NavKey;
  items: NavItem[];
}

const NAV: NavGroup[] = [
  {
    key: "nav.workspace",
    items: [
      { href: "/", key: "nav.dashboard", icon: "dashboard" },
      { href: "/farms", key: "nav.farms", icon: "farm" },
      { href: "/scan", key: "nav.scan", icon: "scan", badge: "queue" },
      { href: "/analysis", key: "nav.analysis", icon: "analysis" },
      { href: "/assistant", key: "nav.assistant", icon: "assistant" },
    ],
  },
  {
    key: "nav.intelligence",
    items: [
      { href: "/map", key: "nav.farmMap", icon: "map" },
      { href: "/hotspots", key: "nav.hotspots", icon: "hotspot" },
      { href: "/monitoring", key: "nav.monitoring", icon: "monitoring" },
    ],
  },
  {
    key: "nav.operations",
    items: [
      {
        href: "/expert",
        key: "nav.expert",
        icon: "expert",
        roles: ["expert", "agent", "admin"],
        badge: "reviews",
      },
      { href: "/notifications", key: "nav.notifications", icon: "bell" },
      { href: "/help", key: "nav.help", icon: "help" },
    ],
  },
  {
    key: "nav.account",
    items: [
      { href: "/profile", key: "nav.profile", icon: "user" },
      { href: "/settings", key: "nav.settings", icon: "settings" },
    ],
  },
];

const ROLE_LABEL: Record<Role, string> = {
  farmer: "Farmer",
  expert: "Agricultural expert",
  agent: "Field agent",
  admin: "Administrator",
};

const LANGUAGES: { value: Language; label: string }[] = [
  { value: "en", label: "English" },
  { value: "hi", label: "हिन्दी" },
  { value: "kn", label: "ಕನ್ನಡ" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function currentTitle(pathname: string, t: (key: NavKey) => string): string {
  for (const group of NAV) {
    for (const item of group.items) {
      if (isActive(pathname, item.href)) return t(item.key);
    }
  }
  if (pathname.startsWith("/chat")) return "Photo assessment (legacy)";
  if (pathname.startsWith("/login")) return "Sign in";
  if (pathname.startsWith("/register")) return "Create account";
  return "CropSentinel";
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { state, role, setRole, setLanguage, markAllNotificationsRead } = useWorkspace();
  const [navOpen, setNavOpen] = useState(false);
  const [menu, setMenu] = useState<"none" | "profile" | "notifications" | "language">("none");
  const menuRef = useRef<HTMLDivElement>(null);
  const [previousPathname, setPreviousPathname] = useState(pathname);

  const t = (key: NavKey) => translate(state.currentUser.language, key);
  const unread = state.notifications.filter((item) => !item.read).length;
  const queued = state.captures.filter((item) => item.syncState !== "synced").length;
  const pendingReviews = state.analyses.filter((item) => item.reviewStatus === "pending").length;

  if (previousPathname !== pathname) {
    setPreviousPathname(pathname);
    setNavOpen(false);
    setMenu("none");
  }

  useEffect(() => {
    if (menu === "none") return;
    const onDown = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenu("none");
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [menu]);

  if (pathname.startsWith("/login") || pathname.startsWith("/register")) {
    return <div className="ws-auth-shell">{children}</div>;
  }

  return (
    <div className="ws-shell">
      {navOpen ? (
        <button
          type="button"
          className="ws-scrim"
          aria-label="Close navigation"
          onClick={() => setNavOpen(false)}
        />
      ) : null}

      <aside className={navOpen ? "ws-sidebar ws-sidebar-open" : "ws-sidebar"}>
        <div className="ws-brand-row">
          <Link href="/" className="ws-brand" aria-label="CropSentinel dashboard">
            <span className="ws-brand-mark">
              <Icon name="leaf" size={22} />
            </span>
            <span className="ws-brand-text">
              <strong>CropSentinel</strong>
              <span>Pest & disease network</span>
            </span>
          </Link>
          <button
            type="button"
            className="ws-icon-button ws-sidebar-close"
            onClick={() => setNavOpen(false)}
            aria-label="Close navigation"
          >
            <Icon name="close" size={18} />
          </button>
        </div>

        <div className="ws-farm-switcher">
          <span className="ws-farm-switcher-label">Active farm</span>
          <strong>{state.farms[0]?.name ?? "No farm yet"}</strong>
          <span className="ws-farm-switcher-meta">
            {state.farms[0]?.village}, {state.farms[0]?.district}
          </span>
        </div>

        <nav className="ws-nav" aria-label="Main navigation">
          {NAV.map((group) => {
            const items = group.items.filter((item) => !item.roles || item.roles.includes(role));
            if (items.length === 0) return null;
            return (
              <div key={group.key} className="ws-nav-group">
                <p className="ws-nav-heading">{t(group.key)}</p>
                <ul>
                  {items.map((item) => {
                    const active = isActive(pathname, item.href);
                    const count =
                      item.badge === "queue" ? queued : item.badge === "reviews" ? pendingReviews : 0;
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          className={active ? "ws-nav-link ws-nav-link-active" : "ws-nav-link"}
                          aria-current={active ? "page" : undefined}
                        >
                          <Icon name={item.icon} size={18} />
                          <span>{t(item.key)}</span>
                          {count > 0 ? <span className="ws-nav-count">{count}</span> : null}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </nav>

        <div className="ws-sidebar-foot">
          <div className="ws-role-card">
            <span className="ws-avatar ws-avatar-sm">{state.currentUser.initials}</span>
            <div>
              <strong>{state.currentUser.name}</strong>
              <span>{ROLE_LABEL[role]}</span>
            </div>
            <Link href="/login" className="ws-icon-button" aria-label={t("action.signOut")}>
              <Icon name="logout" size={16} />
            </Link>
          </div>
          <p className="ws-demo-note">
            <span>Demo</span> Data is stored on this device. Existing API client is preserved.
          </p>
        </div>
      </aside>

      <div className="ws-main">
        <header className="ws-topbar">
          <div className="ws-topbar-left">
            <button
              type="button"
              className="ws-icon-button ws-menu-button"
              onClick={() => setNavOpen(true)}
              aria-label="Open navigation"
            >
              <Icon name="menu" size={20} />
            </button>
            <div>
              <p className="ws-topbar-eyebrow">
                {state.farms[0]?.village ?? "Krishnagiri"} · {new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
              </p>
              <p className="ws-topbar-title">{currentTitle(pathname, t)}</p>
            </div>
          </div>

          <div className="ws-topbar-right" ref={menuRef}>
            {queued > 0 ? (
              <Link href="/scan" className="ws-sync-chip">
                <span className="ws-sync-dot" />
                {queued} queued
              </Link>
            ) : (
              <span className="ws-sync-chip ws-sync-ok">
                <Icon name="check" size={14} />
                Synced
              </span>
            )}

            <div className="ws-menu-wrap">
              <button
                type="button"
                className="ws-icon-button"
                aria-label="Change language"
                aria-expanded={menu === "language"}
                onClick={() => setMenu(menu === "language" ? "none" : "language")}
              >
                <Icon name="globe" size={18} />
              </button>
              {menu === "language" ? (
                <div className="ws-menu ws-menu-small" role="menu">
                  <p className="ws-menu-heading">Language</p>
                  {LANGUAGES.map((language) => (
                    <button
                      key={language.value}
                      type="button"
                      role="menuitemradio"
                      aria-checked={state.currentUser.language === language.value}
                      className={
                        state.currentUser.language === language.value
                          ? "ws-menu-item ws-menu-item-active"
                          : "ws-menu-item"
                      }
                      onClick={() => {
                        setLanguage(language.value);
                        setMenu("none");
                      }}
                    >
                      {language.label}
                      {state.currentUser.language === language.value ? (
                        <Icon name="check" size={15} />
                      ) : null}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>

            <div className="ws-menu-wrap">
              <button
                type="button"
                className="ws-icon-button ws-bell"
                aria-label={`Notifications, ${unread} unread`}
                aria-expanded={menu === "notifications"}
                onClick={() => setMenu(menu === "notifications" ? "none" : "notifications")}
              >
                <Icon name="bell" size={19} />
                {unread > 0 ? <span className="ws-bell-dot">{unread}</span> : null}
              </button>
              {menu === "notifications" ? (
                <div className="ws-menu ws-menu-wide" role="menu">
                  <div className="ws-menu-head">
                    <p>Notifications</p>
                    <button
                      type="button"
                      className="ws-link-button"
                      onClick={markAllNotificationsRead}
                    >
                      Mark all read
                    </button>
                  </div>
                  <div className="ws-notification-list">
                    {state.notifications.slice(0, 5).map((notification) => (
                      <Link
                        key={notification.id}
                        href={notification.href}
                        className={
                          notification.read
                            ? "ws-notification"
                            : "ws-notification ws-notification-unread"
                        }
                        onClick={() => setMenu("none")}
                      >
                        <span className={`ws-notif-dot ws-notif-${notification.kind}`} />
                        <span>
                          <strong>{notification.title}</strong>
                          <small>{notification.body}</small>
                        </span>
                      </Link>
                    ))}
                  </div>
                  <Link href="/notifications" className="ws-menu-foot" onClick={() => setMenu("none")}>
                    View all notifications
                    <Icon name="arrow" size={14} />
                  </Link>
                </div>
              ) : null}
            </div>

            <div className="ws-menu-wrap">
              <button
                type="button"
                className="ws-avatar-button"
                aria-label="Account menu"
                aria-expanded={menu === "profile"}
                onClick={() => setMenu(menu === "profile" ? "none" : "profile")}
              >
                <span className="ws-avatar">{state.currentUser.initials}</span>
                <span className="ws-avatar-meta">
                  <strong>{state.currentUser.name}</strong>
                  <small>{ROLE_LABEL[role]}</small>
                </span>
              </button>
              {menu === "profile" ? (
                <div className="ws-menu" role="menu">
                  <p className="ws-menu-heading">Switch demo role</p>
                  {(Object.keys(ROLE_LABEL) as Role[]).map((option) => (
                    <button
                      key={option}
                      type="button"
                      role="menuitemradio"
                      aria-checked={role === option}
                      className={role === option ? "ws-menu-item ws-menu-item-active" : "ws-menu-item"}
                      onClick={() => {
                        setRole(option);
                        setMenu("none");
                      }}
                    >
                      {ROLE_LABEL[option]}
                      {role === option ? <Icon name="check" size={15} /> : null}
                    </button>
                  ))}
                  <div className="ws-menu-divider" />
                  <Link href="/profile" className="ws-menu-item" onClick={() => setMenu("none")}>
                    <Icon name="user" size={16} /> Profile
                  </Link>
                  <Link href="/settings" className="ws-menu-item" onClick={() => setMenu("none")}>
                    <Icon name="settings" size={16} /> Settings
                  </Link>
                  <Link href="/login" className="ws-menu-item" onClick={() => setMenu("none")}>
                    <Icon name="logout" size={16} /> {t("action.signOut")}
                  </Link>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <main className="ws-content">{children}</main>

        <footer className="ws-footer">
          <span>CropSentinel · Assistive decision support, not a diagnosis or a confirmed outbreak.</span>
          <span className="ws-footer-links">
            <Link href="/help">Data & safety</Link>
            <Link href="/settings">Settings</Link>
          </span>
        </footer>
      </div>

      <FloatingChatbot />
    </div>
  );
}
