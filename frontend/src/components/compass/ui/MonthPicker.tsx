import { AnimatePresence, motion } from "framer-motion";
import { useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { MONTH_LABELS, formatMonthLabel, isMonthRangeInvalid } from "./monthPickerUtils";

/** A pair of month/year pickers with an inline "end before start" hint. */
export function MonthRange({
  start,
  end,
  onStart,
  onEnd,
  className,
}: {
  start: string;
  end: string;
  onStart: (v: string) => void;
  onEnd: (v: string) => void;
  className?: string;
}) {
  const invalid = isMonthRangeInvalid(start, end);
  return (
    <div className={cn("grid grid-cols-1 gap-2.5 sm:grid-cols-2", className)}>
      <MonthYearPicker value={start} onChange={onStart} placeholder="From" invalid={invalid} />
      <MonthYearPicker
        value={end}
        onChange={onEnd}
        placeholder="To"
        allowPresent
        invalid={invalid}
      />
      {invalid && (
        <p className="text-[11.5px] text-red-700 sm:col-span-2" role="alert">
          End date can’t be before the start date.
        </p>
      )}
    </div>
  );
}

/** Modern month/year picker: a styled trigger that opens a compact popover. */
export function MonthYearPicker({
  value,
  onChange,
  placeholder,
  allowPresent,
  invalid,
  compact,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  allowPresent?: boolean;
  invalid?: boolean;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [coords, setCoords] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const parsed = value.trim().match(/^(\d{4})-(\d{2})$/);
  const selectedYear = parsed ? Number(parsed[1]) : null;
  const selectedMonth = parsed ? Number(parsed[2]) : null;
  const [viewYear, setViewYear] = useState(selectedYear ?? new Date().getFullYear());

  // Position the portalled popover just under the trigger, clamped to the viewport.
  useLayoutEffect(() => {
    if (!open) return;
    const POPOVER_WIDTH = 224;
    const update = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const left = Math.max(8, Math.min(rect.left, window.innerWidth - POPOVER_WIDTH - 8));
      setCoords({ top: rect.bottom + 6, left });
    };
    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [open]);

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-invalid={invalid || undefined}
        onClick={() => {
          setViewYear(selectedYear ?? new Date().getFullYear());
          setOpen((v) => !v);
        }}
        className={cn(
          "manual-input flex items-center justify-between gap-2 text-left",
          compact && "manual-input--sm",
          invalid && "is-invalid",
        )}
      >
        <span className={cn(value.trim() ? "text-foreground" : "text-foreground/40")}>
          {value.trim() ? formatMonthLabel(value) : (placeholder ?? "Select")}
        </span>
        <Calendar size={14} className="shrink-0 text-foreground/40" />
      </button>

      {createPortal(
        <AnimatePresence>
          {open && (
            <>
              <div
                className="fixed inset-0 z-[60]"
                onClick={() => setOpen(false)}
                aria-hidden="true"
              />
              <motion.div
                initial={{ opacity: 0, y: -4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -4, scale: 0.98 }}
                transition={{ duration: 0.14 }}
                style={{ position: "fixed", top: coords.top, left: coords.left }}
                className="z-[61] w-56 rounded-2xl border border-foreground/10 bg-white/95 p-2.5 shadow-xl backdrop-blur"
              >
                <div className="mb-2 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => setViewYear((y) => y - 1)}
                    className="grid h-7 w-7 place-items-center rounded-lg text-foreground/60 transition hover:bg-foreground/5"
                    aria-label="Previous year"
                  >
                    <ChevronLeft size={15} />
                  </button>
                  <span className="text-[13.5px] font-semibold tabular-nums">{viewYear}</span>
                  <button
                    type="button"
                    onClick={() => setViewYear((y) => y + 1)}
                    className="grid h-7 w-7 place-items-center rounded-lg text-foreground/60 transition hover:bg-foreground/5"
                    aria-label="Next year"
                  >
                    <ChevronRight size={15} />
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-1">
                  {MONTH_LABELS.map((m, i) => {
                    const isSelected = selectedYear === viewYear && selectedMonth === i + 1;
                    return (
                      <button
                        key={m}
                        type="button"
                        onClick={() => {
                          onChange(`${viewYear}-${String(i + 1).padStart(2, "0")}`);
                          setOpen(false);
                        }}
                        className={cn(
                          "rounded-lg py-1.5 text-[12.5px] transition",
                          isSelected
                            ? "text-white"
                            : "text-foreground/75 hover:bg-[color:var(--brand)]/10",
                        )}
                        style={isSelected ? { background: "var(--gradient-warm)" } : undefined}
                      >
                        {m}
                      </button>
                    );
                  })}
                </div>
                <div className="mt-2 flex items-center justify-between border-t border-foreground/10 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      onChange("");
                      setOpen(false);
                    }}
                    className="rounded-md px-2 py-1 text-[12px] text-foreground/55 transition hover:bg-foreground/5"
                  >
                    {allowPresent ? "Present" : "Clear"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setOpen(false)}
                    className="rounded-md px-2 py-1 text-[12px] font-medium text-[color:var(--brand-deep)] transition hover:bg-[color:var(--brand)]/10"
                  >
                    Done
                  </button>
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </div>
  );
}
