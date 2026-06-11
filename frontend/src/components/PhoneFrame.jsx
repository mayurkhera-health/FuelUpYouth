import { useEffect, useState } from "react";
import "./PhoneFrame.css";

export default function PhoneFrame({ children, showFrame = true }) {
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const check = () => setIsDesktop(window.innerWidth > 600);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  if (!isDesktop || !showFrame) {
    return <>{children}</>;
  }

  return (
    <div className="pf-outer">
      <div className="pf-shell">
        {/* Left side buttons */}
        <div className="pf-btn pf-silent" />
        <div className="pf-btn pf-vol-up" />
        <div className="pf-btn pf-vol-down" />

        {/* Right side button */}
        <div className="pf-btn pf-power" />

        {/* Screen area */}
        <div className="pf-screen">
          {/* Dynamic island */}
          <div className="pf-island" aria-hidden="true" />

          {/* App content — scrolls inside the phone */}
          <div className="pf-content">{children}</div>

          {/* Home indicator */}
          <div className="pf-home" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}
