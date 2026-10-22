import { useEffect, useRef, type PropsWithChildren } from "react";
import { LazyMotion, MotionConfig, domAnimation } from "framer-motion";

export function AppMotionProvider({ children }: PropsWithChildren) {
  const pointerFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const finePointerQuery = window.matchMedia("(pointer: fine)");
    const applyCursorMode = () => {
      document.body.classList.toggle("motion-custom-cursor", finePointerQuery.matches);
    };

    applyCursorMode();
    finePointerQuery.addEventListener("change", applyCursorMode);
    return () => {
      finePointerQuery.removeEventListener("change", applyCursorMode);
      document.body.classList.remove("motion-custom-cursor", "motion-cursor-interactive");
    };
  }, []);

  useEffect(() => {
    const clickSelector = "button, a, [role='button']";

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target instanceof Element ? event.target.closest<HTMLElement>(clickSelector) : null;
      if (!target || target.dataset.motionClick === "off") return;

      const rect = target.getBoundingClientRect();
      target.style.setProperty("--motion-click-x", `${event.clientX - rect.left}px`);
      target.style.setProperty("--motion-click-y", `${event.clientY - rect.top}px`);
      target.classList.remove("motion-click-active");
      window.requestAnimationFrame(() => {
        target.classList.add("motion-click-active");
      });
      window.setTimeout(() => target.classList.remove("motion-click-active"), 680);
    };

    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  useEffect(() => {
    const hoverSelector = "button, a, input, textarea, select, [role='button'], .premium-interactive";

    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerType === "touch") return;
      if (pointerFrameRef.current !== null) {
        window.cancelAnimationFrame(pointerFrameRef.current);
      }

      pointerFrameRef.current = window.requestAnimationFrame(() => {
        document.documentElement.style.setProperty("--motion-pointer-x", `${event.clientX}px`);
        document.documentElement.style.setProperty("--motion-pointer-y", `${event.clientY}px`);
        document.body.classList.add("motion-pointer-ready");
        pointerFrameRef.current = null;
      });
    };

    const onPointerOver = (event: PointerEvent) => {
      if (event.pointerType === "touch") return;
      const target = event.target instanceof Element ? event.target.closest(hoverSelector) : null;
      document.body.classList.toggle("motion-cursor-interactive", Boolean(target));
    };

    const onPointerOut = (event: PointerEvent) => {
      if (event.pointerType === "touch") return;
      const relatedTarget = event.relatedTarget instanceof Element ? event.relatedTarget.closest(hoverSelector) : null;
      if (!relatedTarget) {
        document.body.classList.remove("motion-cursor-interactive");
      }
    };

    document.addEventListener("pointermove", onPointerMove, { passive: true });
    document.addEventListener("pointerover", onPointerOver, { passive: true });
    document.addEventListener("pointerout", onPointerOut, { passive: true });
    return () => {
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerover", onPointerOver);
      document.removeEventListener("pointerout", onPointerOut);
      if (pointerFrameRef.current !== null) {
        window.cancelAnimationFrame(pointerFrameRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const revealSelector = ".premium-glass-panel, .premium-interactive, .premium-icon-surface, .animated-input, [data-motion-reveal]";
    const observed = new WeakSet<Element>();
    let revealIndex = 0;

    if (!("IntersectionObserver" in window)) {
      document.querySelectorAll<HTMLElement>(revealSelector).forEach((target) => target.classList.add("motion-reveal-visible"));
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("motion-reveal-visible");
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );

    const revealVisibleTargets = () => {
      document.querySelectorAll<HTMLElement>(revealSelector).forEach((target) => {
        const rect = target.getBoundingClientRect();
        const isVisible = rect.width > 0 && rect.height > 0 && rect.top < window.innerHeight * 0.96 && rect.bottom > 0;
        if (!isVisible) return;
        target.classList.add("motion-reveal-visible");
        observer.unobserve(target);
      });
    };

    const observeTargets = () => {
      document.querySelectorAll<HTMLElement>(revealSelector).forEach((target) => {
        if (observed.has(target)) return;
        observed.add(target);
        target.style.setProperty("--motion-reveal-delay", `${Math.min(revealIndex * 38, 420)}ms`);
        revealIndex += 1;
        target.classList.add("motion-reveal-ready");
        observer.observe(target);
      });
      window.requestAnimationFrame(revealVisibleTargets);
    };

    observeTargets();
    const mutationObserver = new MutationObserver(observeTargets);
    mutationObserver.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("scroll", revealVisibleTargets, { passive: true });
    window.addEventListener("resize", revealVisibleTargets);

    return () => {
      window.removeEventListener("scroll", revealVisibleTargets);
      window.removeEventListener("resize", revealVisibleTargets);
      mutationObserver.disconnect();
      observer.disconnect();
    };
  }, []);

  return (
    <LazyMotion features={domAnimation}>
      <MotionConfig reducedMotion="user">
        <div className="motion-cursor-glow" aria-hidden="true" />
        <div className="motion-cursor-ring" aria-hidden="true" />
        <div className="motion-cursor-dot" aria-hidden="true" />
        {children}
      </MotionConfig>
    </LazyMotion>
  );
}
