import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useState } from "react";

export function DeepDiveModal({
  open,
  onClose,
  title,
  subtitle,
  headerAside,
  headerDescription,
  wide = false,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  subtitle?: string;
  headerAside?: React.ReactNode;
  headerDescription?: React.ReactNode;
  wide?: boolean;
  children: React.ReactNode;
}) {
  const [desktop, setDesktop] = useState(true);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    const update = () => setDesktop(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const initial = desktop ? { opacity: 0, x: 60 } : { opacity: 0, y: 80 };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-foreground/15 backdrop-blur-[3px]"
          />
          <motion.div
            initial={initial}
            animate={{ opacity: 1, x: 0, y: 0 }}
            exit={initial}
            transition={{ type: "spring", stiffness: 260, damping: 28 }}
            className={
              desktop
                ? wide
                  ? "fixed inset-x-4 top-20 bottom-6 z-50 mx-auto max-w-[1180px]"
                  : "fixed right-4 top-20 bottom-6 z-50 w-[clamp(420px,42vw,640px)]"
                : "fixed inset-x-3 bottom-3 z-50 max-h-[88dvh]"
            }
          >
            <div className="soft-card-elevated relative flex h-full max-h-[88dvh] flex-col overflow-y-auto rounded-3xl overscroll-y-contain md:max-h-none md:overflow-hidden">
              {!desktop && (
                <div className="mx-auto mt-3 h-1 w-10 shrink-0 rounded-full bg-foreground/15" />
              )}
              <div className="relative grid shrink-0 grid-cols-1 items-start gap-x-3 gap-y-2 p-6 pb-4 sm:p-8 sm:pb-5 md:grid-cols-[minmax(0,1fr)_auto]">
                <div className="min-w-0 pr-10 md:pr-0">
                  {subtitle && (
                    <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/45">
                      {subtitle}
                    </p>
                  )}
                  <h3 className="mt-1 text-balance font-display text-2xl leading-[1.12] tracking-tight sm:text-3xl">
                    {title}
                  </h3>
                </div>
                {headerAside && (
                  <div className="min-w-0 md:col-start-2 md:row-start-1 md:pr-12">
                    {headerAside}
                  </div>
                )}
                <button
                  onClick={onClose}
                  aria-label="Close"
                  className="absolute right-6 top-6 grid h-9 w-9 place-items-center rounded-full text-foreground/55 hover:bg-foreground/[0.06] hover:text-foreground sm:right-8 sm:top-8"
                >
                  <X size={16} />
                </button>
                {headerDescription && (
                  <div className="min-w-0 pt-2 md:col-start-1 md:row-start-2 md:pt-4">
                    {headerDescription}
                  </div>
                )}
              </div>
              <motion.div
                initial="hidden"
                animate="show"
                variants={{
                  show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
                }}
                className="flex-none overflow-y-visible px-6 pb-6 sm:px-7 sm:pb-7 md:min-h-0 md:flex-1 md:overflow-y-auto"
              >
                {children}
              </motion.div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

/** Reusable stagger child — wraps any block in a fade-up the modal will sequence. */
export function ModalBlock({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 10 },
        show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] } },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
