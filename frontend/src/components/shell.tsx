import Link from "next/link";

export function Shell({ children }: { children: React.ReactNode }) {
  return <div className="site-shell">
    <header className="site-header">
      <div className="header-inner">
        <Link href="/" className="brand" aria-label="DropVault home"><span className="brand-mark">↧</span><span>DropVault</span></Link>
        <nav aria-label="Main navigation" className="nav-links"><Link href="/">Upload</Link><Link href="/dashboard">My files</Link></nav>
      </div>
    </header>
    <main className="main-content">{children}</main>
    <footer className="site-footer"><span>DropVault</span><span>Private links. Simple sharing.</span></footer>
  </div>;
}
