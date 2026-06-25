import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useState } from "react";

export function DeepDiveModal({
  open,
  onClose,
  title,
  subtitle,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
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
                ? "fixed right-4 top-20 bottom-6 z-50 w-[clamp(420px,42vw,640px)]"
                : "fixed inset-x-3 bottom-3 z-50 max-h-[88dvh]"
            }
          >
            <div className="soft-card-elevated relative flex h-full flex-col overflow-hidden rounded-3xl">
              {!desktop && (
                <div className="mx-auto mt-3 h-1 w-10 shrink-0 rounded-full bg-foreground/15" />
              )}
              <div className="flex shrink-0 items-start justify-between gap-3 p-6 pb-3 sm:p-7 sm:pb-4">
                <div className="min-w-0">
                  {subtitle && (
                    <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/45">
                      {subtitle}
                    </p>
                  )}
                  <h3 className="mt-1 truncate font-display text-2xl tracking-tight sm:text-3xl">
                    {title}
                  </h3>
                </div>
                <button
                  onClick={onClose}
                  aria-label="Close"
                  className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-foreground/55 hover:bg-foreground/[0.06] hover:text-foreground"
                >
                  <X size={16} />
                </button>
              </div>
              <motion.div
                initial="hidden"
                animate="show"
                variants={{
                  show: { transition: { staggerChildren: 0.06, delayChildren: 0.05 } },
                }}
                className="flex-1 overflow-y-auto px-6 pb-6 sm:px-7 sm:pb-7"
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
