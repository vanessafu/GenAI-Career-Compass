/**
 * White canvas with a layered, multi-hue blue gradient field.
 * Uses sky / cyan / indigo / deep-navy drops so the background reads
 * as a real gradient and not a single flat blue tint.
 */
export function AmbientBackdrop() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-white" />
      <div
        className="absolute inset-0"
        style={{
          background:
            // top-left: light sky
            "radial-gradient(42% 36% at 8% 4%, oklch(0.86 0.09 230 / 0.55) 0%, transparent 70%)," +
            // top-right: cyan
            "radial-gradient(36% 30% at 96% 10%, oklch(0.82 0.10 210 / 0.45) 0%, transparent 72%)," +
            // mid-right: indigo
            "radial-gradient(34% 30% at 100% 58%, oklch(0.66 0.16 270 / 0.32) 0%, transparent 72%)," +
            // bottom-right: deep navy
            "radial-gradient(48% 40% at 92% 100%, oklch(0.45 0.16 258 / 0.32) 0%, transparent 72%)," +
            // bottom-left: periwinkle
            "radial-gradient(40% 34% at 0% 96%, oklch(0.78 0.10 255 / 0.42) 0%, transparent 72%)," +
            // mid-center wash, ties them together
            "radial-gradient(60% 50% at 50% 50%, oklch(0.94 0.04 240 / 0.55) 0%, transparent 75%)",
        }}
      />
    </div>
  );
}
