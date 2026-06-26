import { DeepDiveModal, ModalBlock } from "./DeepDiveModal";
import { SkillGapSection } from "./SkillGapSection";
import type { GapReport } from "@/lib/api";
import type { RoleView } from "@/types";

export function RoleDetailModal({
  role,
  gapReport,
  gapError,
  open,
  onClose,
}: {
  role: RoleView;
  gapReport: GapReport | null;
  gapError: string | null;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <DeepDiveModal open={open} onClose={onClose} title={role.title} subtitle={role.trackLabel}>
      {(role.escoTitle || role.escoUri) && (
        <ModalBlock className="mb-6">
          <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
            ESCO reference
          </p>
          {role.escoUri ? (
            <a
              href={role.escoUri}
              target="_blank"
              rel="noreferrer"
              className="text-[13px] font-medium text-[color:var(--brand-deep)] underline-offset-4 hover:underline"
            >
              {role.escoTitle || role.escoUri}
            </a>
          ) : (
            <p className="text-[13px] leading-relaxed text-foreground/75">{role.escoTitle}</p>
          )}
        </ModalBlock>
      )}

      {gapError ? (
        <ModalBlock className="mb-6 border-l-2 border-red-300 pl-3">
          <p className="text-[13px] leading-relaxed text-red-700">{gapError}</p>
        </ModalBlock>
      ) : !gapReport ? (
        <ModalBlock className="mb-6">
          <p className="text-[13px] leading-relaxed text-foreground/60">Preparing gap report...</p>
        </ModalBlock>
      ) : (
        <SkillGapSection report={gapReport} />
      )}
    </DeepDiveModal>
  );
}
