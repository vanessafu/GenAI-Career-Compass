import { DeepDiveModal, ModalBlock } from "./DeepDiveModal";
import type { RoleView } from "@/types";

/**
 * Real role detail built entirely from backend RoleMatch data:
 * essential/optional skills + knowledge, plus the matching analysis text.
 */
export function RoleDetailModal({
  role,
  analysis,
  open,
  onClose,
}: {
  role: RoleView;
  analysis: string | null;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <DeepDiveModal open={open} onClose={onClose} title={role.title} subtitle={role.trackLabel}>
      {role.summary && (
        <ModalBlock className="mb-6">
          <p className="text-[13.5px] leading-relaxed text-foreground/75">{role.summary}</p>
        </ModalBlock>
      )}

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

      {analysis && (
        <ModalBlock className="mb-6">
          <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
            Why this fits you
          </p>
          <p className="text-[13px] leading-relaxed text-foreground/75">{analysis}</p>
        </ModalBlock>
      )}

      <SkillSection title="Matched skills" items={role.matchedSkills} highlight />
      <SkillSection title="Missing skills" items={role.missingSkills} />
      <SkillSection title="Matched domains" items={role.essentialKnowledge} highlight />
      <SkillSection title="Matched certifications" items={role.optionalKnowledge} />
    </DeepDiveModal>
  );
}

function SkillSection({
  title,
  items,
  highlight = false,
}: {
  title: string;
  items: string[];
  highlight?: boolean;
}) {
  if (items.length === 0) return null;
  return (
    <ModalBlock className="mb-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">{title}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span
            key={item}
            className={
              highlight
                ? "rounded-full bg-[color:var(--brand)]/10 px-2.5 py-1 text-[12px] text-[color:var(--brand-deep)]"
                : "rounded-full border border-foreground/10 bg-foreground/[0.03] px-2.5 py-1 text-[12px] text-foreground/70"
            }
          >
            {item}
          </span>
        ))}
      </div>
    </ModalBlock>
  );
}
